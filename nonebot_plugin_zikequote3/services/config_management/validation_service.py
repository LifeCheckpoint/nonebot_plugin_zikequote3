from ...imports import *
from ast import literal_eval

def s_validate_parse_param(args: List[str]):
    schema_str = args[0].strip()
    new_value = literal_eval(args[1].strip())
    return schema_str, new_value
