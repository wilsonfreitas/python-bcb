from __future__ import annotations

import json
import logging
import math
import threading
from io import BytesIO
from typing import Any, Optional, Union
from urllib.parse import quote

import httpx
from lxml import etree
from typing_extensions import Self

from bcb.http import (
    RequestTimeout,
    get_async_client,
    get_client,
    raise_for_request_error,
    raise_for_status,
    timeout_kwargs,
)
from bcb.exceptions import ODataError

logger = logging.getLogger(__name__)

# Module-level metadata cache for OData services
# Maps service URL → ODataMetadata instance
_METADATA_CACHE: dict[str, "ODataMetadata"] = {}
_METADATA_CACHE_LOCK = threading.RLock()


def _load_json_object(text: str, *, context: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as ex:
        raise ODataError(f"{context} returned invalid JSON: {ex}") from ex
    if not isinstance(data, dict):
        raise ODataError(f"{context} returned invalid JSON payload: expected object")
    return data


def _required_field(data: dict[str, Any], field: str, *, context: str) -> Any:
    try:
        return data[field]
    except KeyError as ex:
        raise ODataError(f"{context} response missing required field {field!r}") from ex


def _load_xml_document(content: bytes, *, context: str) -> Any:
    try:
        return etree.parse(BytesIO(content))
    except etree.XMLSyntaxError as ex:
        raise ODataError(f"{context} returned invalid XML: {ex}") from ex


def _format_odata_string_literal(value: Any) -> str:
    if value is None:
        raise ODataError("Edm.String filter values cannot be None")
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _format_odata_literal(edm_type: Optional[str], value: Any) -> str:
    if value is None:
        raise ODataError(f"{edm_type or 'Unknown'} filter values cannot be None")

    if edm_type == "Edm.Decimal":
        try:
            decimal_value = float(value)
        except (TypeError, ValueError) as ex:
            raise ODataError(f"Invalid Edm.Decimal filter value: {value!r}") from ex
        if not math.isfinite(decimal_value):
            raise ODataError(f"Invalid Edm.Decimal filter value: {value!r}")
        return f"{decimal_value}"

    if edm_type in ("Edm.Int16", "Edm.Int32", "Edm.Int64"):
        try:
            return f"{int(value)}"
        except (TypeError, ValueError) as ex:
            raise ODataError(f"Invalid {edm_type} filter value: {value!r}") from ex

    if edm_type == "Edm.String":
        return _format_odata_string_literal(value)

    if edm_type == "Edm.Date":
        try:
            formatted = value.strftime("%Y-%m-%d")
        except AttributeError as ex:
            raise ODataError(f"Invalid Edm.Date filter value: {value!r}") from ex
        if not isinstance(formatted, str):
            raise ODataError(f"Invalid Edm.Date filter value: {value!r}")
        return formatted

    if edm_type == "Edm.Boolean":
        if not isinstance(value, bool):
            raise ODataError(f"Invalid Edm.Boolean filter value: {value!r}")
        return str(value).lower()

    raise ODataError(f"Unsupported OData filter literal type: {edm_type or 'Unknown'}")


# Edm.Boolean
# Edm.Byte
# Edm.Date
# Edm.DateTimeOffset
# Edm.Decimal
# Edm.Duration
# Edm.Guid
# Edm.Int16
# Edm.Int32
# Edm.Int64
# Edm.SByte
# Edm.String
# Edm.TimeOfDay


def str_types(type: str) -> str:
    if type == "Edm.Decimal":
        return "float"
    elif type in ("Edm.Int32", "Edm.Int64", "Edm.Int16"):
        return "int"
    elif type == "Edm.String":
        return "str"
    elif type == "Edm.Boolean":
        return "bool"
    elif type in ("Edm.Date", "Edm.TimeOfDay"):
        return "datetime"
    else:
        return type


class ODataEndPoint:
    def __init__(self, **kwargs: Any) -> None:
        self.data: dict[str, Any] = kwargs

    def __getitem__(self, item: str) -> Any:
        return self.data[item]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def __repr__(self) -> str:
        url = self.data["url"]
        return f"<EndPoint {url}>"


class ODataEntitySetMeta(type):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def __call__(self, *args: Any) -> Any:
        obj = super().__call__(*args)
        entity = args[2]
        for name, prop in entity.properties.items():
            setattr(obj, name, prop)
        return obj


class ODataEntitySet(metaclass=ODataEntitySetMeta):
    def __init__(self, name: str, entity_type: str, entity: "ODataEntity") -> None:
        self.name = name
        self.entity_type = entity_type
        self.entity = entity
        self.fullname: str = ""

    def describe(self) -> None:
        props = ", ".join(
            [f"{prop.name}<{prop.ftype}>" for prop in self.entity.properties.values()]
        )
        print(f"""
EntitySet (Endpoint): {self.name}
EntityType: {self.entity_type}
Properties: {props}""")

    def __repr__(self) -> str:
        return f"<EntitySet {self.name}>"


class ODataFunctionImport:
    def __init__(
        self, name: str, function: "ODataFunction", entity_set: ODataEntitySet
    ) -> None:
        self.name = name
        self.entity_set = entity_set
        self.function = function

    def describe(self) -> None:
        props = ", ".join(
            [
                f"{prop.name} <{prop.ftype}>"
                for prop in self.entity_set.entity.properties.values()
            ]
        )
        params = ", ".join(
            [f"{param.name} <{param.ftype}>" for param in self.function.parameters]
        )
        s = f"""
Function: {self.function.name}
Parameters: {params}
EntitySet: {self.entity_set.name}
EntityType: {self.entity_set.entity_type}
Properties: {props}"""
        print(s)

    def __repr__(self) -> str:
        return f"<FunctionImport {self.name}>"


class ODataParameter:
    def __init__(self, **kwargs: Any) -> None:
        self.data: dict[str, Any] = kwargs

    @property
    def name(self) -> Optional[str]:
        return self.data.get("Name")

    @property
    def type(self) -> Optional[str]:
        return self.data.get("Type")

    @property
    def ftype(self) -> str:
        return str_types(self.type or "")

    @property
    def required(self) -> bool:
        nullable = self.data.get("Nullable")
        if nullable:
            return bool(nullable == "false")
        else:
            return True

    def format(self, value: Any) -> str:
        if self.type == "Edm.Decimal":
            return f"{float(value)}"
        elif self.type == "Edm.Int32":
            return f"{int(value)}"
        elif self.type == "Edm.String":
            return f"'{str(value)}'"
        else:
            return f"'{str(value)}'"


class ODataPropertyOrderBy:
    def __init__(self, obj: "ODataProperty", order: str) -> None:
        self.obj = obj
        self.order = order

    def __str__(self) -> str:
        return f"{self.obj.name} {self.order}"

    def __repr__(self) -> str:
        return f"<{str(self)}>"


class ODataPropertyFilter:
    def __init__(self, obj: "ODataProperty", oth: Any, operator: str) -> None:
        self.obj = obj
        self.other = oth
        self.operator = operator

    def statement(self) -> str:
        literal = _format_odata_literal(self.obj.type, self.other)
        return f"{self.obj.name} {self.operator} {literal}"

    def __str__(self) -> str:
        return self.statement()

    def __repr__(self) -> str:
        return f"<filter: {str(self)}>"


class ODataProperty:
    def __init__(self, **kwargs: Any) -> None:
        self.data: dict[str, Any] = kwargs

    @property
    def name(self) -> Optional[str]:
        return self.data.get("Name")

    @property
    def type(self) -> Optional[str]:
        return self.data.get("Type")

    @property
    def ftype(self) -> str:
        return str_types(self.type or "")

    def asc(self) -> ODataPropertyOrderBy:
        return ODataPropertyOrderBy(self, "asc")

    def desc(self) -> ODataPropertyOrderBy:
        return ODataPropertyOrderBy(self, "desc")

    def __gt__(self, other: Any) -> ODataPropertyFilter:
        return ODataPropertyFilter(self, other, "gt")

    def __ge__(self, other: Any) -> ODataPropertyFilter:
        return ODataPropertyFilter(self, other, "ge")

    def __lt__(self, other: Any) -> ODataPropertyFilter:
        return ODataPropertyFilter(self, other, "lt")

    def __le__(self, other: Any) -> ODataPropertyFilter:
        return ODataPropertyFilter(self, other, "le")

    def __eq__(self, other: Any) -> ODataPropertyFilter:  # type: ignore[override]
        return ODataPropertyFilter(self, other, "eq")

    def __repr__(self) -> str:
        return f"<Property {self.name}<{self.ftype}>>"


class ODataFunction:
    def __init__(self, **kwargs: Any) -> None:
        self.name: str = kwargs["Name"]
        self.parameters: list[ODataParameter] = kwargs["parameters"]
        self.return_type: str = kwargs["return_type"]
        self.fullname: str = f"{kwargs['namespace']}.{self.name}"

    def __repr__(self) -> str:
        return f"<Function {self.name}>"


class ODataEntity:
    def __init__(
        self, name: str, properties: dict[str, ODataProperty], namespace: str
    ) -> None:
        self.name = name
        self.properties = properties
        self.fullname = f"{namespace}.{name}"

    def __repr__(self) -> str:
        return f"<Entity {self.name}>"


class ODataMetadata:
    namespaces = {
        "edm": "http://docs.oasis-open.org/odata/ns/edm",
        "edmx": "http://docs.oasis-open.org/odata/ns/edmx",
    }

    def __init__(self, url: str, *, timeout: RequestTimeout = None) -> None:
        self.url = url
        self._timeout = timeout
        self._load_document(timeout=timeout)
        try:
            _xpath = "edmx:DataServices/edm:Schema"
            schemas = self.doc.xpath(_xpath, namespaces=self.namespaces)
            if not schemas:
                raise ODataError(f"OData metadata {self.url} missing schema")
            schema = schemas[0]
            self.namespace = schema.attrib["Namespace"]
            self._used_elements: list[str] = []
            self._parse_entities(schema)
            self._parse_entity_sets(schema)
            self._parse_functions(schema)
            self._parse_function_imports(schema)
        except ODataError:
            raise
        except (KeyError, IndexError, TypeError) as ex:
            raise ODataError(
                f"OData metadata {self.url} has invalid structure: {ex}"
            ) from ex

    def _load_document(self, *, timeout: RequestTimeout = None) -> None:
        logger.debug(f"Fetching OData metadata from {self.url}")
        try:
            res = get_client().get(self.url, **timeout_kwargs(timeout))
        except httpx.HTTPError as ex:
            raise_for_request_error(
                ex, context=f"OData metadata {self.url}", error_cls=ODataError
            )
        logger.debug(
            f"OData metadata response: status={res.status_code}, length={len(res.content)}"
        )
        raise_for_status(
            res,
            context=f"OData metadata {self.url}",
            error_cls=ODataError,
            not_found_cls=ODataError,
            rate_limit_cls=ODataError,
            server_error_cls=ODataError,
        )
        self.doc = _load_xml_document(res.content, context=f"OData metadata {self.url}")

    def _parse_entity(self, entity_element: Any, namespace: str) -> ODataEntity:
        name = entity_element.attrib["Name"]
        props = {
            prop.attrib["Name"]: ODataProperty(**prop.attrib) for prop in entity_element
        }
        return ODataEntity(name, props, namespace)

    def _parse_entities(self, schema: Any) -> None:
        _xpath = "edm:EntityType"
        self.entities: list[ODataEntity] = [
            self._parse_entity(e, self.namespace)
            for e in schema.xpath(_xpath, namespaces=self.namespaces)
        ]

        self._entities_fullnames: dict[str, ODataEntity] = {
            e.fullname: e for e in self.entities
        }

    def _parse_entity_sets(self, schema: Any) -> None:
        _xpath = "edm:EntityContainer/edm:EntitySet"

        def _parse_entity_set(e: Any) -> ODataEntitySet:
            entity = self._entities_fullnames[e.attrib["EntityType"]]
            return ODataEntitySet(e.attrib["Name"], e.attrib["EntityType"], entity)

        self.entity_sets: dict[str, ODataEntitySet] = {
            e.attrib["Name"]: _parse_entity_set(e)
            for e in schema.xpath(_xpath, namespaces=self.namespaces)
        }

        for n, es in self.entity_sets.items():
            es.fullname = f"{self.namespace}.{n}"

        self._entity_sets_fullnames: dict[str, ODataEntitySet] = {
            es.fullname: es for es in self.entity_sets.values()
        }

    def _parse_functions(self, schema: Any) -> None:
        _xpath = "edm:Function"

        def _parse_function(e: Any) -> ODataFunction:
            parameters = []
            return_type = None
            for element in e:
                if element.tag.endswith("Parameter"):
                    parameters.append(ODataParameter(**element.attrib))
                elif element.tag.endswith("ReturnType"):
                    return_type = element.attrib["Type"]
            kwargs: dict[str, Any] = dict(**e.attrib)
            kwargs["parameters"] = parameters
            kwargs["return_type"] = return_type
            kwargs["namespace"] = self.namespace
            return ODataFunction(**kwargs)

        self.functions: dict[str, ODataFunction] = {
            e.attrib["Name"]: _parse_function(e)
            for e in schema.xpath(_xpath, namespaces=self.namespaces)
        }

        self._functions_fullnames: dict[str, ODataFunction] = {
            f.fullname: f for f in self.functions.values()
        }

    def _parse_function_imports(self, schema: Any) -> None:
        _xpath = "edm:EntityContainer/edm:FunctionImport"

        def _parse_function_import(e: Any) -> ODataFunctionImport:
            function = self._functions_fullnames[e.attrib["Function"]]
            entity_set = self._entity_sets_fullnames[e.attrib["EntitySet"]]
            self._used_elements.append(e.attrib["EntitySet"])
            return ODataFunctionImport(e.attrib["Name"], function, entity_set)

        self.function_imports: dict[str, ODataFunctionImport] = {
            e.attrib["Name"]: _parse_function_import(e)
            for e in schema.xpath(_xpath, namespaces=self.namespaces)
        }


class ODataService:
    """OData service client.

    Parameters
    ----------
    url : str
        OData service root URL
    """

    def __init__(self, url: str, *, timeout: RequestTimeout = None) -> None:
        self.url = url
        self._timeout = timeout
        try:
            res = get_client().get(self.url, **timeout_kwargs(timeout))
        except httpx.HTTPError as ex:
            raise_for_request_error(
                ex, context=f"OData service {self.url}", error_cls=ODataError
            )
        raise_for_status(
            res,
            context=f"OData service {self.url}",
            error_cls=ODataError,
            not_found_cls=ODataError,
            rate_limit_cls=ODataError,
            server_error_cls=ODataError,
        )
        context = f"OData service {self.url}"
        self.api_data = _load_json_object(res.text, context=context)
        value = _required_field(self.api_data, "value", context=context)
        if not isinstance(value, list):
            raise ODataError("OData service response field 'value' must be a list")
        endpoints = []
        for endpoint in value:
            if not isinstance(endpoint, dict):
                raise ODataError(
                    "OData service response field 'value' must contain objects"
                )
            endpoints.append(ODataEndPoint(**endpoint))
        self.endpoints = endpoints
        odata_context = _required_field(
            self.api_data, "@odata.context", context=context
        )
        if not isinstance(odata_context, str):
            raise ODataError(
                "OData service response field '@odata.context' must be a string"
            )
        self._odata_context_url = odata_context

        # Use cached metadata if available, otherwise create and cache new one
        with _METADATA_CACHE_LOCK:
            if self._odata_context_url in _METADATA_CACHE:
                self.metadata = _METADATA_CACHE[self._odata_context_url]
            else:
                self.metadata = ODataMetadata(self._odata_context_url, timeout=timeout)
                _METADATA_CACHE[self._odata_context_url] = self.metadata

    def __getitem__(self, item: str) -> Union[ODataEntitySet, ODataFunctionImport]:
        es = self.entity_sets.get(item)
        if es is None:
            fi = self.function_imports.get(item)
            if fi is not None:
                return fi
            else:
                raise ODataError("Invalid name: " + item)
        else:
            return es

    @property
    def entities(self) -> list[ODataEntity]:
        return self.metadata.entities

    @property
    def function_imports(self) -> dict[str, ODataFunctionImport]:
        return self.metadata.function_imports

    @property
    def entity_sets(self) -> dict[str, ODataEntitySet]:
        return self.metadata.entity_sets

    def describe(self) -> None:
        es_names = []
        for es in self.entity_sets.keys():
            k = f"{self.metadata.namespace}.{es}"
            if k not in self.metadata._used_elements:
                es_names.append(es)
        if len(es_names):
            print("EntitySets:")
            for es in es_names:
                print(" ", es)
        if len(self.function_imports):
            print("FunctionImports:")
            for es in self.function_imports.keys():
                print(" ", es)

    def query(
        self, entity_set: Union[ODataEntitySet, ODataFunctionImport]
    ) -> "ODataQuery":
        return ODataQuery(entity_set, self.url, timeout=self._timeout)


class ODataQuery:
    def __init__(
        self,
        entity: Union[ODataEntitySet, ODataFunctionImport],
        url: str,
        *,
        timeout: RequestTimeout = None,
    ) -> None:
        self.entity = entity
        self.base_url = url
        self._timeout = timeout
        self._params: dict[str, Any] = {}
        self.function_parameters: dict[str, Any] = {}
        self._filter: list[ODataPropertyFilter] = []
        self._select: list[ODataProperty] = []
        self._orderby: list[ODataPropertyOrderBy] = []
        self._raw = False
        self.is_function = isinstance(entity, ODataFunctionImport)
        if self.is_function:
            self.function_parameters = {
                (p.name or ""): None
                for p in self.entity.function.parameters  # type: ignore[union-attr]
            }

    def odata_url(self) -> str:
        self._url = (
            f"{self.base_url}{self.entity.name}"
            if self.base_url.endswith("/")
            else f"{self.base_url}/{self.entity.name}"
        )
        if self.is_function:
            args = [f"{p.name}=@{p.name}" for p in self.entity.function.parameters]  # type: ignore[union-attr]
            args_str = ",".join(args)
            return f"{self._url}({args_str})"
        else:
            return self._url

    def parameters(self, **kwargs: Any) -> Self:
        for arg in kwargs:
            if arg in self.function_parameters:
                self.function_parameters[arg] = kwargs[arg]
            else:
                raise ODataError(f"Unknown parameter: {arg}")
        return self

    def filter(self, *args: ODataPropertyFilter) -> Self:
        if len(args):
            self._filter.extend(args)
        return self

    def limit(self, limit: int) -> Self:
        self._params["$top"] = limit
        return self

    def skip(self, skip: int) -> Self:
        self._params["$skip"] = skip
        return self

    def format(self, fmt: str) -> Self:
        self._params["$format"] = fmt
        return self

    def orderby(self, *args: ODataPropertyOrderBy) -> Self:
        if len(args):
            self._orderby.extend(args)
        return self

    def select(self, *args: ODataProperty) -> Self:
        if len(args):
            self._select.extend(args)
        return self

    def raw(self) -> Self:
        self._raw = True
        return self

    def _build_parameters(self) -> dict[str, Any]:
        params: dict[str, Any] = {"$format": self._params.get("$format", "json")}
        if len(self._filter):
            _filter = " and ".join(str(f) for f in self._filter)
            params["$filter"] = _filter
        if len(self._orderby):
            _orderby = ",".join(str(f) for f in self._orderby)
            params["$orderby"] = _orderby
        if len(self._select):
            _select = ",".join(str(f.name) for f in self._select)
            params["$select"] = _select
        params.update(self._params)
        return params

    def reset(self) -> None:
        self._filter = []
        self._orderby = []
        self._params = {}

    def _resolve_timeout(self, timeout: RequestTimeout) -> RequestTimeout:
        if timeout is None:
            return self._timeout
        return timeout

    def collect(self, *, timeout: RequestTimeout = None) -> Any:
        url = self.odata_url()
        data = _load_json_object(
            self.text(timeout=timeout), context=f"OData query {url}"
        )
        _required_field(data, "value", context=f"OData query {url}")
        return data

    async def async_text(self, *, timeout: RequestTimeout = None) -> str:
        """Async version of text(). Fetches OData response using shared client."""
        params = self._build_parameters()
        if self.is_function and len(self.function_parameters):
            for p in self.entity.function.parameters:  # type: ignore[union-attr]
                val = self.function_parameters[p.name or ""]
                if p.required and val is None:
                    raise ODataError("Parameter not set: " + (p.name or ""))
                params["@" + (p.name or "")] = p.format(val)
        qs = "&".join([f"{quote(k)}={quote(str(v))}" for k, v in params.items()])
        headers = {"OData-Version": "4.0", "OData-MaxVersion": "4.0"}
        url = self.odata_url()
        try:
            res = await get_async_client().get(
                url + "?" + qs,
                headers=headers,
                **timeout_kwargs(self._resolve_timeout(timeout)),
            )
        except httpx.HTTPError as ex:
            raise_for_request_error(
                ex, context=f"OData query {url}", error_cls=ODataError
            )
        raise_for_status(
            res,
            context=f"OData query {url}",
            error_cls=ODataError,
            not_found_cls=ODataError,
            rate_limit_cls=ODataError,
            server_error_cls=ODataError,
        )
        return res.text

    async def async_collect(self, *, timeout: RequestTimeout = None) -> Any:
        """Async version of collect(). Awaits async_text() and parses JSON."""
        url = self.odata_url()
        data = _load_json_object(
            await self.async_text(timeout=timeout), context=f"OData query {url}"
        )
        _required_field(data, "value", context=f"OData query {url}")
        return data

    def text(self, *, timeout: RequestTimeout = None) -> str:
        params = self._build_parameters()
        if self.is_function and len(self.function_parameters):
            for p in self.entity.function.parameters:  # type: ignore[union-attr]
                val = self.function_parameters[p.name or ""]
                if p.required and val is None:
                    raise ODataError("Parameter not set: " + (p.name or ""))
                params["@" + (p.name or "")] = p.format(val)
        qs = "&".join([f"{quote(k)}={quote(str(v))}" for k, v in params.items()])
        headers = {"OData-Version": "4.0", "OData-MaxVersion": "4.0"}
        url = self.odata_url()
        logger.debug(f"Fetching OData query from {url}")
        try:
            res = get_client().get(
                url + "?" + qs,
                headers=headers,
                **timeout_kwargs(self._resolve_timeout(timeout)),
            )
        except httpx.HTTPError as ex:
            raise_for_request_error(
                ex, context=f"OData query {url}", error_cls=ODataError
            )
        logger.debug(
            f"OData query response: status={res.status_code}, length={len(res.text)}"
        )
        raise_for_status(
            res,
            context=f"OData query {url}",
            error_cls=ODataError,
            not_found_cls=ODataError,
            rate_limit_cls=ODataError,
            server_error_cls=ODataError,
        )
        return res.text

    def show(self) -> None:
        print("URL:")
        print(f"  {self.odata_url()}")
        if self.is_function and len(self.function_parameters):
            print("Function Parameters:")
            for p in self.entity.function.parameters:  # type: ignore[union-attr]
                v = self.function_parameters[p.name or ""]
                req = " (required) " if p.required else " "
                print(f"  {p.name}<{p.ftype}>{req}= {v}")
        params = self._build_parameters()
        if len(params):
            print("Query Parameters:")
            for k, v in params.items():
                print(" ", k, "=", v)
        if self.is_function:
            names = [
                f"{p.name}<{p.ftype}>"
                for p in self.entity.entity_set.entity.properties.values()  # type: ignore[union-attr]
            ]
            names_str = ", ".join(names)
            print("Return:", names_str)
        else:
            names = [
                f"{p.name}<{p.ftype}>"
                for p in self.entity.entity.properties.values()  # type: ignore[union-attr]
            ]
            names_str = ", ".join(names)
            print("Return:", names_str)
