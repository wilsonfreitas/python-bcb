from io import BytesIO
from typing import Any, Optional, Union
from lxml import etree
import json
import httpx
from urllib.parse import quote
from typing_extensions import Self

from bcb.exceptions import ODataError

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
        if self.obj.type == "Edm.Decimal":
            return f"{self.obj.name} {self.operator} {float(self.other)}"
        elif self.obj.type == "Edm.Int32":
            return f"{self.obj.name} {self.operator} {int(self.other)}"
        elif self.obj.type == "Edm.String":
            return f"{self.obj.name} {self.operator} '{str(self.other)}'"
        elif self.obj.type == "Edm.Date":
            return f"{self.obj.name} {self.operator} {self.other.strftime('%Y-%m-%d')}"
        else:
            return f"{self.obj.name} {self.operator} '{self.other}'"

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

    def __init__(self, url: str) -> None:
        self.url = url
        self._load_document()
        _xpath = "edmx:DataServices/edm:Schema"
        schema = self.doc.xpath(_xpath, namespaces=self.namespaces)[0]
        self.namespace: str = schema.attrib["Namespace"]
        self._used_elements: list[str] = []
        self._parse_entities(schema)
        self._parse_entity_sets(schema)
        self._parse_functions(schema)
        self._parse_function_imports(schema)

    def _load_document(self) -> None:
        res = httpx.get(self.url, timeout=60.0)
        self.doc = etree.parse(BytesIO(res.content))

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
    def __init__(self, url: str) -> None:
        self.url = url
        res = httpx.get(self.url, timeout=60.0)
        self.api_data: dict[str, Any] = json.loads(res.text)
        self.endpoints: list[ODataEndPoint] = [
            ODataEndPoint(**x) for x in self.api_data["value"]
        ]
        self._odata_context_url: str = self.api_data["@odata.context"]
        self.metadata = ODataMetadata(self._odata_context_url)

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
        return ODataQuery(entity_set, self.url)


class ODataQuery:
    def __init__(
        self, entity: Union[ODataEntitySet, ODataFunctionImport], url: str
    ) -> None:
        self.entity = entity
        self.base_url = url
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

    def collect(self) -> Any:
        return json.loads(self.text())

    def text(self) -> str:
        params = self._build_parameters()
        if self.is_function and len(self.function_parameters):
            for p in self.entity.function.parameters:  # type: ignore[union-attr]
                val = self.function_parameters[p.name or ""]
                if p.required and val is None:
                    raise ODataError("Parameter not set: " + (p.name or ""))
                params["@" + (p.name or "")] = p.format(val)
        qs = "&".join([f"{quote(k)}={quote(str(v))}" for k, v in params.items()])
        headers = {"OData-Version": "4.0", "OData-MaxVersion": "4.0"}
        res = httpx.get(self.odata_url() + "?" + qs, headers=headers, timeout=60.0)
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
