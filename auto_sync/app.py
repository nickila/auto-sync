import logging.config
import os

import yaml

from config import ConfigLoader
from sync import Sync
from util import read_file
from worker import Worker

# Load all properties from INI and point to the folder where resources are stored
props_file = "app.ini"
cl = ConfigLoader.load(props_file, 'sync_resource')

# Just for process output
with open("logging.yml") as log_cfg:
    logging.config.dictConfig(yaml.safe_load(log_cfg))

sync_options = cl.get_config('sync')
resources_config = cl.get_resource_config()
log_folder = sync_options.get("log_folder")
os.makedirs(log_folder, exist_ok=True)

# The "base" config into which sync config gets merged
template_config = resources_config.merge_with(sync_options.values)
template_config.set_value("log_folder", os.path.abspath(log_folder))

# Read in the set of example syncs
example_sync_data = read_file("../example_sync/example.yml")

# Execute (single thread for now)
for config in example_sync_data:
    sync = Sync(config)
    w = Worker(sync, template_config)
    w.run()

# Some change