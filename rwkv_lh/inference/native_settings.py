"""Project-owned State settings, independent of irwkv's environment registry."""
import os

_DEFAULTS = {
    'IRWKV_RWKV7_NATIVE_STATE_CACHE_CAPACITY': 128,
    'IRWKV_RWKV7_NATIVE_STATE_STORE_CAPACITY': 0,
    'IRWKV_RWKV7_NATIVE_STATE_DIR': None,
    'IRWKV_RWKV7_STATE_PROFILE_MANIFEST': None,
    'IRWKV_RWKV7_STATE_PROFILE_MANIFEST_SHA256': None,
}


def __getattr__(name):
    if name not in _DEFAULTS:
        raise AttributeError(name)
    default = _DEFAULTS[name]
    value = os.environ.get(name, default)
    return int(value) if type(default) is int else value
