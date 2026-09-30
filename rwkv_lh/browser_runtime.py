"""Location of the installed browser runtime, without exposing a user's home."""
import os
from pathlib import Path

SANDBOX_BROWSER_ROOT = '/opt/rwkv-lh-browsers'


def installed_browser_root():
    configured = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '')
    if configured == '0':
        import importlib.util
        spec = importlib.util.find_spec('playwright')
        if spec is None or spec.origin is None:
            return None
        root = Path(spec.origin).parent / 'driver/package/.local-browsers'
    else:
        root = Path(configured) if configured else Path.home() / '.cache/ms-playwright'
    if not root.is_dir():
        return None
    root = root.resolve(strict=True)
    home = Path.home().resolve()
    if root in {home, *home.parents, *Path(__file__).resolve().parents} or (root / 'rwkv_lh').exists():
        raise ValueError('browser runtime must be a dedicated browser directory')
    return root
