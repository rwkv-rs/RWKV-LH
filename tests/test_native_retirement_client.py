from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.runtime.native_state import NATIVE_STATE_LIFECYCLE_VERSION


def test_release_uses_recoverable_native_request_and_keeps_identity(monkeypatch):
    client = OpenAICompatibleRWKVClient(RuntimeSettings(base_url='http://unused',api_key='',model='test'))
    calls=[]
    identity={'state_ref':'WKV-'+'a'*32,'state_digest':'b'*64,'cache_binding_digest':'c'*64}
    def request(op,payload):
        calls.append((op,payload))
        return {'released_state_refs':[identity['state_ref']]}
    monkeypatch.setattr(client,'_native_request',request)
    result=client.state_release(states=[identity],release_import_aliases=True)
    assert calls[0][0]=='release'
    assert calls[0][1]['states']==[identity]
    assert calls[0][1]['release_import_aliases'] is True
    assert calls[0][1]['lifecycle_protocol']==NATIVE_STATE_LIFECYCLE_VERSION
    assert result['released_state_refs']==[identity['state_ref']]
