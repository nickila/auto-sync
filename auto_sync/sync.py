from collections import OrderedDict
from copy import deepcopy
import uuid

class Sync():

    def __init__(self, run_config=None):
        self.id = run_config.get("id") or uuid.uuid4()
        self.sync_args = run_config.get("sync_args") or ""
        self.sync_config = run_config.get("sync_config") or {}
        self.sync_type = run_config.get('sync_type') or "ldap"

        try:
            self.org_id = run_config['umapi']['enterprise']['org_id']
        except:
            self.org_id = None

    def serialize(self, filter=True):
        return OrderedDict({
            'org_id': self.org_id,
            'sync_args': self.sync_args,
            'sync_type': self.sync_type,
            'sync_config': self.public_scope() if filter else self.sync_config
        })

    def public_scope(self):
        san_cfg = deepcopy(self.sync_config)

        try:
            san_cfg['umapi']['enterprise'] = self.org_id
        except:
            pass  # we don't care if the keys don't exist for this

        try:
            for s in san_cfg['connector']['mapping']['scoped_sources']:
                s['access_token'] = "removed"
        except:
            pass  # we don't care if the keys don't exist for this
        return san_cfg
