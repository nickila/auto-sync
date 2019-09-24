import configparser
import os
import re
from collections import Mapping
from copy import deepcopy

import yaml

from auto_sync.util import compare_str, decode


class Config():

    def __init__(self, value_dict):
        self.values = value_dict

    def set_value(self, name, value):
        self.values[name] = value

    def get(self, name, default=None, required=False, as_type=None):
        val = self.values.get(name) or default
        if required and not val:
            raise AssertionError("Value for " + name + " required but not given")
        return (as_type)(val) if as_type else val

    def take(self, name, default=None, required=False, as_type=str):
        val = self.get(name, default, required)
        if name in self.values:
            self.values.pop(name)
        return (as_type)(val)

    def require(self, name):
        return self.get(name, required=True)

    def get_bool(self, name, default=False):
        val = self.get(name, default)
        return str(val).lower() == 'true'

    def get_int(self, name, default=None):
        return int(self.get(name, default))

    def get_list(self, name, default=None):
        return list(self.get(name, default))

    def get_dict(self, name, default=None):
        return dict(self.get(name, default))

    def require_bool(self, name):
        return bool(self.require(name))

    def require_int(self, name):
        return int(self.require(name))

    def require_list(self, name):
        return list(self.require(name))

    def require_dict(self, name):
        return dict(self.require(name))

    def get_path(self, name, default=None):
        raw = self.get(name, default)
        if not raw:
            return None
        raw = re.split('[/\\\\]+', raw)
        return os.sep.join(raw)

    # returns a new config from subset of keys
    def get_sub_dict(self, keys):
        return {k:self.values[k] for k  in keys}

    # returns a new config from subset of keys
    def get_sub_config(self, keys):
        return Config(self.get_sub_dict(keys))

    # merges a dictionary into config
    def merge_with(self, data):
        if data:
            for k, v in data.items():
                if not self.values.get(k):
                    self.set_value(k, v)
                elif isinstance(v, Mapping):
                    self.merge_dict(self.values[k], v)
                else:
                    self.set_value(k, v)
        return self

    # Combine dictionaries recursively
    def merge_dict(self, dct, merge_dct):
        if not merge_dct:
            return

        if isinstance(merge_dct, Mapping):
            for k in merge_dct:
                if (k in dct and isinstance(dct[k], dict)
                    and isinstance(merge_dct[k], Mapping)):
                    self.merge_dict(dct[k], merge_dct[k])
                else:
                    try:
                        dct[k] = merge_dct[k]
                    except Exception as e:
                        print()
        else:
            raise TypeError("Cannot merge dict with '"
                            + type(merge_dct).__name__ + "'")


class ConfigLoader():

    def __init__(self, props_file, sources_dir=None):
        self.sources_dir = sources_dir
        self.from_sources = self.from_properties(props_file)

    def find_env_var(self, key):
        for k, v in os.environ._data.items():
            if compare_str(k, key):
                return v

    @classmethod
    def load(cls, props_file, sources_dir=None):
        return cls(props_file, sources_dir)

    def get_config(self, name):
        cfg = self.from_sources.get(name)
        if not cfg:
            return None
        return Config(deepcopy(cfg))

    def from_properties(self, props_file):
        config = {}
        parser = configparser.RawConfigParser()
        parser.read(props_file)

        for s, v in parser._sections.items():
            for config_option in v:
                override = self.find_env_var("CFG." + s + "." + config_option)
                if override:
                    v[config_option] = decode(override)

            config[s] = v
            if self.sources_dir:
                if s == 'config_files':
                    config[s] = self.read_sources(v)
                elif s == 'binary_files':
                    config[s] = self.read_binaries(v)

        return config

    def read_sources(self, config_files):
        # Read in all the YAML

        cfg = {}
        for n, f in config_files.items():
            with open(self.get_resource_path(f)) as file:
                cfg[n] = yaml.safe_load(file) # Resource(f, yaml.safe_load(file)).as_dict()
        return cfg

    def read_binaries(self, binaries):
        # Read in any other files

        cfg = {}
        for n, f in binaries.items():
            cfg[n] = Resource(f, self.get_resource_path(f)).as_dict()
        return cfg

    def get_resource_path(self, filename):
        return os.path.join(self.sources_dir, filename)

    def get_resource_config(self, required_fields=None):
        options = {}
        required_fields = required_fields or []
        yaml_cfg = self.get_config('config_files')
        binary_cfg = self.get_config('binary_files')

        if not yaml_cfg or not binary_cfg:
            raise ValueError("Both config and binary sections are required")

        for f in yaml_cfg.values:
            if f in required_fields:
                options[f] = yaml_cfg.require(f)
                required_fields.remove(f)
            else:
                options[f] = yaml_cfg.get(f)

        options['binary'] = binary_cfg.values
        for b in binary_cfg.values:
            if b in required_fields:
                required_fields.remove(b)

        if required_fields:
            raise ValueError("Config missing required fields: " + str(required_fields))
        options['ust_executable'] = options['binary']['ust_executable']['filename']
        return Config(options)


class Resource():

    def __init__(self, filename, data):
        self.filename = filename
        self.data = data

    def as_dict(self):
        return deepcopy(vars(self))
