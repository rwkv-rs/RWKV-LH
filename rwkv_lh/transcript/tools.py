"""Canonical tool vocabulary over the project's own tool semantics.

The names are the common ones a base model has seen throughout pretraining;
the parameters stay this project's, because they are the stronger contract.
`Read` takes a byte offset with a resumable cursor, not a line number, and
`Grep` returns ordered match lines with a pagination cursor. Renaming must not
quietly downgrade either, so every description states the real semantics even
where a familiar name implies something else.

`finish_work` keeps its name: it is an explicit, trainable ending action with no
common equivalent, and the collected transcripts require it as the last call.
"""
from copy import deepcopy

TOOL_PROTOCOL = 'rwkv-lh.coder.tools.v2'

# Canonical name <- the native implementation name the harness executes.
CANONICAL_NAMES = {
    'read_file': 'Read',
    'write_file': 'Write',
    'replace_text': 'Edit',
    'run_shell': 'Bash',
    'list_directory': 'ListDir',
    'search_files': 'Grep',
    'read_job_output': 'BashOutput',
    'kill_job': 'KillShell',
    'finish_work': 'finish_work',
}

# A blocking-only shell cannot deliver a web project: starting a dev server
# consumes the call that was supposed to check it. The retired role data carried
# BashBackground/JobOutput/JobKill supervision, so losing these was a capability
# regression rather than a design choice. A job handle is observable state, not a
# promise: the harness may report a job already gone, and a log line saying
# "ready" never proves the server is still up on a later call.
BACKGROUND_TOOLS = ('BashOutput', 'KillShell')
JOB_HANDLE = {'type': 'string', 'minLength': 1,
              'description': 'Job handle returned by a Bash call that set run_in_background.'}
NATIVE_NAMES = {canonical: native for native, canonical in CANONICAL_NAMES.items()}

# Canonical parameter <- native parameter, per native tool. Only renames; no
# parameter is added, dropped or re-typed, so execution semantics are unchanged.
PARAMETER_ALIASES = {
    'read_file': {'path': 'file_path'},
    'write_file': {'path': 'file_path'},
    'replace_text': {'path': 'file_path', 'old': 'old_string', 'new': 'new_string', 'all': 'replace_all'},
}
_NATIVE_ALIASES = {native: {canonical: parameter for parameter, canonical in aliases.items()}
                   for native, aliases in PARAMETER_ALIASES.items()}

# A familiar name carries a wrong default expectation, so each description says
# what the parameter actually is.
DESCRIPTIONS = {
    'Read': 'Read original UTF-8 file text. offset is a UTF-8 byte offset on a character boundary, NOT a line '
            'number, and no ending position is supplied; continue from next_start_byte until complete. EOF '
            'returns empty text and a missing file fails.',
    'Write': 'Create or replace a UTF-8 file, including missing parent directories.',
    'Edit': 'Replace exact old_string with new_string in one file. Matching is exact; a missing or ambiguous '
            'match fails without writing.',
    'Bash': 'Execute a Bash command in the isolated workspace. There is no persistent terminal between '
            'calls. Set run_in_background to start a long-running process, such as a dev server, without '
            'blocking this call; it returns a job handle for BashOutput and KillShell. A background job is '
            'not guaranteed to survive until a later call.',
    'BashOutput': 'Read new output from a background job since the last read. Returns the incremental '
                  'stdout and stderr and whether the job is still running. Output showing a server is '
                  'ready does not prove it is still running now.',
    'KillShell': 'Terminate a background job and its process group. Returns the observed exit status; a '
                 'job that already exited is reported as such, not as a failure.',
    'ListDir': 'List paths, types and sizes without file contents, paginated. Use this to discover paths; Grep '
               'searches contents. Recursive listing skips .git, .venv, node_modules and __pycache__. Continue '
               'from next_cursor until complete.',
    'Grep': 'Search local UTF-8 file contents, not file names or the web. Default mode is Python regex; choose '
            'literal for exact text. Returns ordered match lines, source locations, skipped-file details and '
            'next_cursor.',
    'finish_work': 'End the run with your own declaration of finished or blocked and summarize the actual '
                   'results. This records a declaration and does not verify correctness.',
}


def canonical_name(native):
    if native not in CANONICAL_NAMES:
        raise ValueError('unknown native tool: ' + str(native))
    return CANONICAL_NAMES[native]


def native_name(canonical):
    if canonical not in NATIVE_NAMES:
        raise ValueError('unknown canonical tool: ' + str(canonical))
    return NATIVE_NAMES[canonical]


def _rename_schema(native, schema):
    aliases = PARAMETER_ALIASES.get(native, {})
    renamed = deepcopy(schema)
    renamed['properties'] = {aliases.get(key, key): value
                             for key, value in schema['properties'].items()}
    renamed['required'] = [aliases.get(key, key) for key in schema.get('required', [])]
    return renamed


def canonical_definitions(native_tools):
    """Rename names and parameters only; types, constraints and defaults stay native."""
    definitions = []
    for tool in native_tools:
        function = tool['function'] if 'function' in tool else tool
        name = canonical_name(function['name'])
        definitions.append({'type': 'function', 'function': {
            'name': name, 'description': DESCRIPTIONS[name],
            'parameters': _rename_schema(function['name'], function['parameters'])}})
    return definitions


def native_call(name, arguments):
    """Translate one canonical call back to the native tool the harness runs.

    A renamed parameter must arrive under its canonical spelling; the native
    spelling is rejected so the two vocabularies cannot blur into one.
    """
    native = native_name(name)
    aliases = _NATIVE_ALIASES.get(native, {})
    renamed = set(PARAMETER_ALIASES.get(native, {}))
    for key in arguments:
        if key in renamed and key not in aliases:
            raise ValueError('argument ' + key + ' must use its canonical name for ' + name)
    return native, {aliases.get(key, key): value for key, value in arguments.items()}
