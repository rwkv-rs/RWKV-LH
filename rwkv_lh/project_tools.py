"""One frontend tool catalog shared by production, replay and offline data."""
from .harness import ActionHarness

# A blocking-only shell cannot deliver a web project: the call that starts a dev
# server is the call that was supposed to check it. Background control is part of
# the product menu for that reason; the shared research Harness keeps it out of
# the role prompts by default (harness.BACKGROUND_JOB_ACTIONS).
FRONTEND_TOOLS = ('list_directory', 'search_files', 'read_file', 'write_file',
                  'replace_text', 'run_shell', 'read_job_output', 'kill_job')


def register_background_jobs(harness):
    """Add background job control to this Harness instance only.

    These are not class-level builtins: the legacy role chain enumerates a
    frozen 23-tool menu and cc-view keeps a hand-written name map, so a default
    registration would appear in views that predate the capability. Registering
    per instance keeps the current product's menu honest without widening
    artifacts that are being deleted.
    """
    from .harness import BACKGROUND_JOB_DEFINITIONS
    for name, definition in BACKGROUND_JOB_DEFINITIONS.items():
        if name not in harness._definitions:
            harness.register_action(definition, getattr(harness, '_' + name))
    return harness


def configure_project_tools(harness):
    """Install the frontend primitives while retaining explicitly registered extensions.

    Browser verification belongs to the external evaluator. Its registration is
    excluded even if a caller supplies an external-check Harness. Other explicit
    extensions keep their declared capabilities. Schemas and execution use the
    same restricted registry; the shared research Harness is unchanged.
    """
    register_background_jobs(harness)
    builtins = set(ActionHarness.builtin_action_names())
    extensions = [tool['name'] for tool in harness.g1i_tool_definitions()
                  if tool['name'] not in builtins and tool['name'] not in FRONTEND_TOOLS
                  and tool['name'] != 'check_project'
                  and harness.definition(tool['name']).capability_class != 'local.project_check']
    harness.retain_actions((*FRONTEND_TOOLS, *extensions))
    harness.configure_frontend_file_tools()
    harness.configure_process_network('run_shell', 'public_web')
    return harness
