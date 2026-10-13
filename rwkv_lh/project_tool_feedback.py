"""One model-facing tool view shared by RWKV and teacher data collection.

Raw receipts retain host evidence. Literal source and command output are never
searched/replaced; only fields in host-produced metadata are omitted.
"""
from copy import deepcopy
import json


def _host_view(value):
    if isinstance(value, dict):
        return {key: _host_view(item) for key, item in value.items()
                if key != 'sha256' and not key.endswith('_sha256')
                and key not in {'source_snapshots', 'snapshot_transition_verified',
                                'content_digest', 'contract_digest'}}
    if isinstance(value, list):
        return [_host_view(item) for item in value]
    return value


def model_tool_result(result):
    """Keep operational facts and literal contents, omitting host hash bookkeeping."""
    view = deepcopy(result)
    if 'artifacts' in view:
        view['artifacts'] = _host_view(view['artifacts'])
    if 'metadata' in view:
        view['metadata'] = _host_view(view['metadata'])
    # search_files.output is a host-generated envelope, unlike file/command text.
    # Preserve each actual match and the opaque pagination cursor verbatim.
    if view.get('action_type') == 'search_files' and view.get('success'):
        try:
            payload = json.loads(view['output'])
        except (KeyError, TypeError, ValueError):
            pass
        else:
            if isinstance(payload, dict) and payload.get('schema_version') == 'rwkv-lh.search-files-result.v1':
                view['output'] = json.dumps(_host_view(payload), ensure_ascii=False, sort_keys=True)
    return view
