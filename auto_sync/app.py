import logging.config
import os

import yaml
import sys
from auto_sync.config import ConfigLoader
from auto_sync.sync import Sync
from auto_sync.util import read_file
from auto_sync.worker import Worker

print(os.getcwd())
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))



# Load all properties from INI and point to the folder where resources are stored
props_file = os.path.join(bundle_dir, "app.ini")
cl = ConfigLoader.load(props_file, 'sync_resource')

# Just for process output
with open(os.path.join(bundle_dir, "logging.yml")) as log_cfg:
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

