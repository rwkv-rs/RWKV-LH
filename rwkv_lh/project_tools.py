"""One frontend tool catalog shared by production, replay and offline data."""
from .harness import ActionHarness

FRONTEND_TOOLS = ('list_directory', 'search_files', 'read_file', 'write_file',
                  'replace_text', 'run_shell')


def configure_project_tools(harness):
    """Install the frontend primitives while retaining explicitly registered extensions.

    Browser verification belongs to the external evaluator. Its registration is
    excluded even if a caller supplies an external-check Harness. Other explicit
    extensions keep their declared capabilities. Schemas and execution use the
    same restricted registry; the shared research Harness is unchanged.
    """
    builtins = set(ActionHarness.builtin_action_names())
    extensions = [tool['name'] for tool in harness.g1i_tool_definitions()
                  if tool['name'] not in builtins and tool['name'] not in FRONTEND_TOOLS
                  and tool['name'] != 'check_project'
                  and harness.definition(tool['name']).capability_class != 'local.project_check']
    harness.retain_actions((*FRONTEND_TOOLS, *extensions))
    harness.configure_process_network('run_shell', 'public_web')
    return harness
