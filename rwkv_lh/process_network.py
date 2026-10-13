"""Public command routing without inheriting host credentials or configuration."""
import os
from urllib.parse import urlsplit


def public_proxy_environment():
    """Carry public proxy endpoints and keep local project connections direct."""
    result = {}
    for name in ('http_proxy', 'https_proxy'):
        values = {os.environ[key].strip() for key in (name, name.upper())
                  if os.environ.get(key, '').strip()}
        if len(values) > 1:
            raise ValueError(f'{name}: conflicting public proxy URLs')
        if not values:
            continue
        value = values.pop()
        try:
            parsed = urlsplit(value)
            valid = (parsed.scheme in ('http', 'https') and bool(parsed.hostname)
                     and parsed.username is None and parsed.password is None
                     and parsed.path in ('', '/') and not parsed.query and not parsed.fragment
                     and all(ord(char) > 32 for char in value))
            parsed.port
        except ValueError:
            valid = False
        if not valid:
            raise ValueError(f'{name}: public proxy URL required; no credentials, path, query or fragment')
        result[name] = result[name.upper()] = value
    if result:
        result['no_proxy'] = result['NO_PROXY'] = '127.0.0.1,localhost,::1'
    return result


def command_network_environment():
    """Dependency cache lives in the command's temporary filesystem.

    Explicit tool environment additions may override these defaults. User npm
    configuration and tokens are not read from the host home directory.
    """
    return {'npm_config_cache': '/tmp/npm-cache', 'npm_config_userconfig': '/dev/null',
            'npm_config_update_notifier': 'false', **public_proxy_environment()}
