from collections import OrderedDict
from copy import deepcopy
import uuid

class Sync():

    def __init__(self, sync_config=None):
        self.id = sync_config.get("sync_name") or uuid.uuid4()
        self.sync_config = sync_config or {}
        try:
            self.org_id = sync_config['umapi']['enterprise']['org_id']
        except:
            self.org_id = None

    def serialize(self, filter=True):
        return OrderedDict({
            'org_id': self.org_id,
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
