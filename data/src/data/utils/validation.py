import re

def validate_regex_format(val: str, format_regex: str):
    return bool(re.match(format_regex, val))