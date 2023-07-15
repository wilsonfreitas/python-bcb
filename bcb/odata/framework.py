from io import BytesIO
import logging
from lxml import etree
import json
import httpx
from urllib.parse import quote


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


def str_types(type):
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
    def __init__(self, **kwargs):
        self.data = kwargs

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __repr__(self):
        url = self.data["url"]
        return f"<EndPoint {url}>"


class ODataEntitySetMeta(type):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, *args):
        obj = super().__call__(*args)
        entity = args[2]
        for name, prop in entity.properties.items():
            setattr(obj, name, prop)
        return obj


class ODataEntitySet(metaclass=ODataEntitySetMeta):
    def __init__(self, name, entity_type, entity):
        self.name = name
        self.entity_type = entity_type
        self.entity = entity

    def describe(self):
        props = ", ".join(
            [f"{prop.name}<{prop.ftype}>" for prop in self.entity.properties.values()]
        )
        print(
            f"""
EntitySet (Endpoint): {self.name}
EntityType: {self.entity_type}
Properties: {props}"""
        )

    def __repr__(self):
        return f"<EntitySet {self.name}>"


class ODataFunctionImport:
    def __init__(self, name, function, entity_set):
        self.name = name
        self.entity_set = entity_set
        self.function = function

    def describe(self):
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

    def __repr__(self):
        return f"<FunctionImport {self.name}>"


class ODataParameter:
    def __init__(self, **kwargs):
        self.data = kwargs

    @property
    def name(self):
        return self.data.get("Name")

    @property
    def type(self):
        return self.data.get("Type")

    @property
    def ftype(self):
        return str_types(self.type)

    @property
    def required(self):
        nullable = self.data.get("Nullable")
        if nullable:
            return nullable == "false"
        else:
            return True

    def format(self, value):
        if self.type == "Edm.Decimal":
            return f"{float(value)}"
        elif self.type == "Edm.Int32":
            return f"{int(value)}"
        elif self.type == "Edm.String":
            return f"'{str(value)}'"
        else:
            return f"'{str(value)}'"


class ODataPropertyOrderBy:
    def __init__(self, obj, order):
        self.obj = obj
        self.order = order

    def __str__(self):
        return f"{self.obj.name} {self.order}"

    def __repr__(self):
        return f"<{str(self)}>"


class ODataPropertyFilter:
    def __init__(self, obj, oth, operator):
        self.obj = obj
        self.other = oth
        self.operator = operator

    def statement(self):
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

    def __str__(self):
        return self.statement()

    def __repr__(self):
        return f"<filter: {str(self)}>"


class ODataProperty:
    def __init__(self, **kwargs):
        self.data = kwargs

    @property
    def name(self):
        return self.data.get("Name")

    @property
    def type(self):
        return self.data.get("Type")

    @property
    def ftype(self):
        return str_types(self.type)

    def asc(self):
        return ODataPropertyOrderBy(self, "asc")

    def desc(self):
        return ODataPropertyOrderBy(self, "desc")

    def __gt__(self, other):
        return ODataPropertyFilter(self, other, "gt")

    def __ge__(self, other):
        return ODataPropertyFilter(self, other, "ge")

    def __lt__(self, other):
        return ODataPropertyFilter(self, other, "lt")

    def __le__(self, other):
        return ODataPropertyFilter(self, other, "le")

    def __eq__(self, other):
        return ODataPropertyFilter(self, other, "eq")

    def __repr__(self):
        return f"<Property {self.name}<{self.ftype}>>"


class ODataFunction:
    def __init__(self, **kwargs):
        self.name = kwargs["Name"]
        self.parameters = kwargs["parameters"]
        self.return_type = kwargs["return_type"]
        self.fullname = f'{kwargs["namespace"]}.{self.name}'

    def __repr__(self):
        return f"<Function {self.name}>"


class ODataEntity:
    def __init__(self, name, properties, namespace):
        self.name = name
        self.properties = properties
        self.fullname = f"{namespace}.{name}"

    def __repr__(self):
        return f"<Entity {self.name}>"


class ODataMetadata:
    namespaces = {
        "edm": "http://docs.oasis-open.org/odata/ns/edm",
        "edmx": "http://docs.oasis-open.org/odata/ns/edmx",
    }

    def __init__(self, url):
        self.url = url
        self._load_document()
        _xpath = "edmx:DataServices/edm:Schema"
        schema = self.doc.xpath(_xpath, namespaces=self.namespaces)[0]
        self.namespace = schema.attrib["Namespace"]
        self._used_elements = []
        self._parse_entities(schema)
        self._parse_entity_sets(schema)
        self._parse_functions(schema)
        self._parse_function_imports(schema)

    def _load_document(self):
        res = httpx.get(self.url, timeout=60.0)
        self.doc = etree.parse(BytesIO(res.content))

    def _parse_entity(self, entity_element, namespace):
        name = entity_element.attrib["Name"]
        props = {
            prop.attrib["Name"]: ODataProperty(**prop.attrib) for prop in entity_element
        }
        return ODataEntity(name, props, namespace)

    def _parse_entities(self, schema):
        _xpath = "edm:EntityType"
        self.entities = [
            self._parse_entity(e, self.namespace)
            for e in schema.xpath(_xpath, namespaces=self.namespaces)
        ]

        self._entities_fullnames = {e.fullname: e for e in self.entities}

    def _parse_entity_sets(self, schema):
        _xpath = "edm:EntityContainer/edm:EntitySet"

        def _parse_entity_set(e):
            entity = self._entities_fullnames[e.attrib["EntityType"]]
            return ODataEntitySet(e.attrib["Name"], e.attrib["EntityType"], entity)

        self.entity_sets = {
            e.attrib["Name"]: _parse_entity_set(e)
            for e in schema.xpath(_xpath, namespaces=self.namespaces)
        }

        for n, es in self.entity_sets.items():
            es.fullname = f"{self.namespace}.{n}"

        self._entity_sets_fullnames = {
            es.fullname: es for es in self.entity_sets.values()
        }

    def _parse_functions(self, schema):
        _xpath = "edm:Function"

        def _parse_function(e):
            parameters = []
            return_type = None
            for element in e:
                if element.tag.endswith("Parameter"):
                    parameters.append(ODataParameter(**element.attrib))
                elif element.tag.endswith("ReturnType"):
                    return_type = element.attrib["Type"]
            kwargs = dict(**e.attrib)
            kwargs["parameters"] = parameters
            kwargs["return_type"] = return_type
            kwargs["namespace"] = self.namespace
            return ODataFunction(**kwargs)

        self.functions = {
            e.attrib["Name"]: _parse_function(e)
            for e in schema.xpath(_xpath, namespaces=self.namespaces)
        }

        self._functions_fullnames = {f.fullname: f for f in self.functions.values()}

    def _parse_function_imports(self, schema):
        _xpath = "edm:EntityContainer/edm:FunctionImport"

        def _parse_function_import(e):
            function = self._functions_fullnames[e.attrib["Function"]]
            entity_set = self._entity_sets_fullnames[e.attrib["EntitySet"]]
            self._used_elements.append(e.attrib["EntitySet"])
            return ODataFunctionImport(e.attrib["Name"], function, entity_set)

        self.function_imports = {
            e.attrib["Name"]: _parse_function_import(e)
            for e in schema.xpath(_xpath, namespaces=self.namespaces)
        }


class ODataService:
    def __init__(self, url):
        self.url = url
        res = httpx.get(self.url, timeout=60.0)
        self.api_data = json.loads(res.text)
        self.endpoints = [ODataEndPoint(**x) for x in self.api_data["value"]]
        self._odata_context_url = self.api_data["@odata.context"]
        self.metadata = ODataMetadata(self._odata_context_url)

    def __getitem__(self, item):
        es = self.entity_sets.get(item)
        if es is None:
            fi = self.function_imports.get(item)
            if fi is not None:
                return fi
            else:
                raise ValueError("Invalid name: " + item)
        else:
            return es

    @property
    def entities(self):
        return self.metadata.entities

    @property
    def function_imports(self):
        return self.metadata.function_imports

    @property
    def entity_sets(self):
        return self.metadata.entity_sets

    def describe(self):
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

    def query(self, entity_set):
        return ODataQuery(entity_set, self.url)


class ODataQuery:
    def __init__(self, entity, url):
        self.entity = entity
        self.base_url = url
        self._params = {}
        self.function_parameters = {}
        self._filter = []
        self._select = []
        self._orderby = []
        self._raw = False
        self.is_function = isinstance(entity, ODataFunctionImport)
        if self.is_function:
            self.function_parameters = {
                p.name: None for p in self.entity.function.parameters
            }

    def odata_url(self):
        self._url = (
            f"{self.base_url}{self.entity.name}"
            if self.base_url.endswith("/")
            else f"{self.base_url}/{self.entity.name}"
        )
        if self.is_function:
            args = [f"{p.name}=@{p.name}" for p in self.entity.function.parameters]
            args = ",".join(args)
            return f"{self._url}({args})"
        else:
            return self._url

    def parameters(self, **kwargs):
        for arg in kwargs:
            if arg in self.function_parameters:
                self.function_parameters[arg] = kwargs[arg]
            else:
                raise ValueError(f"Unknown parameter: {arg}")
        return self

    def filter(self, *args):
        if len(args):
            self._filter.extend(args)
        return self

    def limit(self, limit):
        self._params["$top"] = limit
        return self

    def skip(self, skip):
        self._params["$skip"] = skip
        return self

    def format(self, fmt):
        self._params["$format"] = fmt
        return self

    def orderby(self, *args):
        if len(args):
            self._orderby.extend(args)
        return self

    def select(self, *args):
        if len(args):
            self._select.extend(args)
        return self

    def raw(self):
        self._raw = True
        return self

    def _build_parameters(self):
        params = {"$format": self._params.get("$format", "json")}
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

    def reset(self):
        self._filter = []
        self._orderby = []
        self._params = {}

    def collect(self):
        return json.loads(self.text())

    def text(self):
        params = self._build_parameters()
        if self.is_function and len(self.function_parameters):
            for p in self.entity.function.parameters:
                val = self.function_parameters[p.name]
                if p.required and val is None:
                    raise ValueError("Parameter not set: " + p.name)
                params["@" + p.name] = p.format(val)
        qs = "&".join([f"{quote(k)}={quote(str(v))}" for k, v in params.items()])
        headers = {"OData-Version": "4.0", "OData-MaxVersion": "4.0"}
        res = httpx.get(self.odata_url() + "?" + qs, headers=headers, timeout=60.0)
        return res.text

    def show(self):
        print(f"URL:")
        print(f"  {self.odata_url()}")
        if self.is_function and len(self.function_parameters):
            print("Function Parameters:")
            for p in self.entity.function.parameters:
                v = self.function_parameters[p.name]
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
                for p in self.entity.entity_set.entity.properties.values()
            ]
            names = ", ".join(names)
            print("Return:", names)
        else:
            names = [
                f"{p.name}<{p.ftype}>" for p in self.entity.entity.properties.values()
            ]
            names = ", ".join(names)
            print("Return:", names)
