"""Mandatory Native plugin preflight before irwkv's standard serve command."""
from importlib.metadata import entry_points
import os


def require_plugins():
    required = {
        ('irwkv.general_plugins','rwkv_lh_state_worker'): 'rwkv_lh.inference.irwkv_plugin:register_worker',
        ('irwkv.endpoint_plugins','rwkv_lh_native'): 'rwkv_lh.inference.irwkv_plugin:endpoint',
    }
    selected = set(os.environ.get('IRWKV_PLUGINS','').split(','))
    for (group,name), target in required.items():
        installed = list(entry_points(group=group,name=name))
        if name not in selected or len(installed)!=1 or installed[0].value!=target:
            raise RuntimeError('required Native plugin missing or replaced: '+name)
        # irwkv logs and swallows factory/registration errors. This preflight
        # calls those exact installed entry points without swallowing failure.
        installed[0].load()()


def main():
    require_plugins()
    from irwkv.entrypoints.cli.main import main as irwkv_main
    return irwkv_main()


if __name__ == '__main__':main()
