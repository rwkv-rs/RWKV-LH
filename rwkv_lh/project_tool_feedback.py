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


READ_ONLY_TOOLS = frozenset({'read_file', 'list_directory', 'search_files'})


def _without_empty(value):
    """Drop absent host facts; False and 0 remain observable values."""
    if isinstance(value, dict):
        kept = {key: _without_empty(item) for key, item in value.items()}
        return {key: item for key, item in kept.items() if item not in (None, '', [], {})}
    if isinstance(value, list):
        return [_without_empty(item) for item in value]
    return value


def _host_metadata(metadata, action_type):
    """Omit bookkeeping restated elsewhere in the same receipt or the action."""
    view = _host_view(metadata)
    # The read cursor repeats start/end/next_start_byte and the source line range.
    view.pop('chunk', None)
    # Stream byte offsets summarize the literal output, which is shown in full.
    view.pop('command_streams', None)
    if view.get('executable_resolution') == 'unchanged':
        # The shell wrapper argv restates `command`; only a resolved change is a fact.
        for key in ('executable_resolution', 'argv', 'resolved_argv'):
            view.pop(key, None)
    if isinstance(view.get('command_stdin'), dict) and view['command_stdin'].get('bytes') == 0:
        view.pop('command_stdin')
    if action_type in READ_ONLY_TOOLS and view.get('workspace_committed') is False:
        view.pop('workspace_committed')
    return _without_empty(view)


def model_tool_result(result):
    """Keep operational facts and literal contents, omitting host bookkeeping."""
    view = deepcopy(result)
    if 'artifacts' in view:
        view['artifacts'] = _without_empty(_host_view(view['artifacts']))
    if 'metadata' in view:
        view['metadata'] = _host_metadata(view['metadata'], view.get('action_type'))
    for key in ('artifacts', 'evidence', 'metadata', 'exit_code', 'error'):
        if key in view and (view[key] is None or view[key] == [] or view[key] == {}):
            del view[key]
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
