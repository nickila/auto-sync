import logging
import os
import shutil
import sys
import tempfile
import uuid
from os.path import join
from subprocess import Popen, PIPE, STDOUT
from copy import deepcopy
import yaml

from auto_sync.util import decode, timestamp


class Worker():

    def __init__(self, sync, template):
        self.sync = sync
        self.template_config = deepcopy(template)
        self.sync_command = template.get("default_command", "python {pex} -c {cfg} {args}")
        self.default_sync_args = template.get("default_args", "")
        self.logger = logging.getLogger(sync.org_id)

    def run(self):
        try:
            tmpdir = tempfile.TemporaryDirectory()
            self.process(self.sync, tmpdir.name)
        finally:
            tmpdir.cleanup()

    def process(self, sync, tmpdir):

        # prepare
        self.logger.info("Processing " + sync.id)
        command, run_log = self.prepare(sync, tmpdir)

        # Run the sync
        shellex = self.template_config.get_bool('use_os.system', False)

        try:
            self.run_sync(command, shellex)
        finally:
            # Finally to always copy in unexpected failure
            # Copy the run log somewhere to save
            output_log = "{0}-{1}.log".format(sync.id, timestamp())
            output_log = os.path.join(self.template_config.get("log_folder"), output_log)
            shutil.copy(run_log, output_log)

    def prepare(self, sync, dir):

        # Temporary log for logging in tmp directory
        run_log = join(dir, str(uuid.uuid4()))

        # Determines the type of sync (ldap, oneroster, etc)
        # Required to set the keys in config correctly
        connector_type = sync.sync_type

        # Set the keys in UST config correctly for the type and files
        full_config = self.get_template(connector_type).merge_with(sync.sync_config).values
        full_config['config']['logging']['file_log_name_format'] = run_log
        full_config['config']['invocation_defaults']['connector'] = connector_type
        full_config['config']['adobe_users']['connectors'] = {
            'umapi': 'umapi.yml'
        }

        full_config['config']['directory_users']['extension'] = 'extension.yml'
        full_config['config']['directory_users']['connectors'] = {
            connector_type: "connector.yml"
        }

        # Copy files over
        for name, resource in full_config.items():
            if name == 'binary':
                for f, d in resource.items():
                    shutil.copy(d['data'], join(dir, d['filename']))
            elif isinstance(resource, dict):
                with open(join(dir, name + ".yml"), 'w') as file:
                    yaml.dump(resource, file, default_flow_style=False)

        # Prepend the log with the sync info
        with open(run_log, 'w') as log:
            yaml.dump(sync.public_scope(), log)
            log.write("\n\n")

        # Format the command for absolute paths (do NOT use os.chdir)
        # NOTE: it must be similar like: python(3) {pex} -c {cfg} {args}
        command = self.sync_command.format(
            pex=join(dir, full_config['ust_executable']),
            cfg=join(dir, 'config.yml'),
            args=sync.sync_args or self.default_sync_args)

        return command, run_log

    def run_sync(self, command, system_shell=False):

        # Cannot use subprocess with PEX file and also debug
        if system_shell:
            os.system(command)

        # Normal execution
        else:
            p = Popen(command.split(" "), stdout=PIPE, stdin=PIPE, stderr=STDOUT)
            for line in iter(p.stdout.readline, b''):
                line = decode(line)
                print(line)  # For console but not log visibility
                sys.stdout.flush()

    def get_template(self, connector_type):

        # Take what we need from the template list
        keys = ['umapi', 'extension', connector_type, 'config', 'binary', 'ust_executable']
        cfg = self.template_config.get_sub_config(keys)

        # Pop the key to a new name - connector, to match sync config
        cfg.values['connector'] = cfg.values.pop(connector_type)
        return cfg
