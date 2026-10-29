"""Single source of truth for the agent transcript format.

Production execution, the generation grammar, prompt rendering and training
export all derive from this package. Two copies of a format is how the previous
round's training and serving silently diverged, so nothing here may be restated
by hand elsewhere.
"""
from .tools import (CANONICAL_NAMES, NATIVE_NAMES, PARAMETER_ALIASES, TOOL_PROTOCOL,
                    canonical_definitions, canonical_name, native_call, native_name)

__all__ = ['CANONICAL_NAMES', 'NATIVE_NAMES', 'PARAMETER_ALIASES', 'TOOL_PROTOCOL',
           'canonical_definitions', 'canonical_name', 'native_call', 'native_name']
