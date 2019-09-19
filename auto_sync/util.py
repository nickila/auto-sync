import json
import os
import re
from io import StringIO
from datetime import datetime
import yaml

date_format = "%Y-%m-%d_%H.%M.%S"

def decode(text, force=False):
    if not text:
        return
    try:
        text = text.decode()
    except:
        pass
    if not force and not isinstance(text, str):
        raise TypeError("Cannot decode str: " + str(text))
    return text.strip()


def compare_str(val1, val2):
    return decode(val1).lower() == decode(val2).lower()


def as_list(text):
    if not text:
        return []
    if isinstance(text, list):
        return text
    elif isinstance(text, set):
        return list(text)
    text = decode(text)
    if isinstance(text, str):
        return [text]
    raise TypeError(
        "Object not representable as list: " + type(text).__name__)


def correct_path(path):
    path = re.split('[/\\\\]+', path)
    return os.sep.join(path)

def read_file(filename):
    with open(filename) as file:
        data = file.read()
    type = filename.split(".")[-1]
    return parse_yaml_json(data, data_type=type)

def parse_yaml_json(data, data_type="json"):
    if not data:
        return {}
    if data_type == 'json':
        return json.loads(data)
    elif data_type in ['yml', 'yaml']:
        return yaml.safe_load(StringIO(data))

def timestamp(date=None):
    if date and not isinstance(date, datetime):
        return date
    return (date or datetime.now()).strftime(date_format)