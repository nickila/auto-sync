import logging
import os
import shutil
import sys
import tempfile
import uuid
from copy import deepcopy
from os.path import join
from subprocess import Popen, PIPE, STDOUT

import yaml

from util import decode, timestamp


class Worker():

    def __init__(self, sync, template):
        self.sync = sync
        self.template_config = template
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

        run_log = join(dir, str(uuid.uuid4())) + ".log"
        full_config = self.merge_template(sync)
        full_config['config']['data']['logging'] \
            ['file_log_name_format'] = run_log

        # Copy files over
        for name, resource in full_config.items():
            if name == 'binary':
                for f, d in resource.items():
                    shutil.copy(d['data'], join(dir, d['filename']))
            elif isinstance(resource, dict):
                with open(join(dir, resource['filename']), 'w') as file:
                    yaml.dump(resource['data'], file)

        # Prepend the log with the sync info
        with open(run_log, 'w') as log:
            yaml.dump(sync.public_scope(), log)
            log.write("\n\n")

        # Format the command for absolute paths (relatives will cause concurrency issues)
        ust_config = full_config['config']['filename']
        pex = full_config['ust_executable']
        command = full_config.get('cmd') or full_config['default_cmd']
        command = command.format(pex=join(dir, pex), cfg=join(dir, ust_config))
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

    def merge_template(self, sync):
        data = deepcopy(sync.sync_config)
        for d in data:
            if d in self.template_config.values:
                data[d] = {
                    'data': data.get(d)}
        return self.template_config.merge_with(data).values
