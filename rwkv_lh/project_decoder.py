"""Derive the entire role output grammar from its existing tool definitions."""
from .runtime.structured_output import build_decoder_contract

INPUT_FRAMING = 'project-decoder-json-fence.v1'


def build_role_decoder(definitions):
    if not definitions or len({item['name'] for item in definitions}) != len(definitions):
        raise ValueError('decoder requires unique role tools')
    return build_decoder_contract({'anyOf': [
        {'type': 'object', 'properties': {
            'function': {'const': item['name']}, 'params': item['parameters']},
         'required': ['function', 'params'], 'additionalProperties': False}
        for item in definitions]})
