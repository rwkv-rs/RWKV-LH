import shutil
import asyncio
from types import SimpleNamespace
import pytest
from test_native_state_service import service_module as service_module
from test_native_state_lifecycle import disk_service, initial_state, release_request


def test_remote_disk_reserve_refuses_new_state_but_allows_cleanup(tmp_path,service_module,monkeypatch):
    async def run():
        service,_,_,root=disk_service(service_module,tmp_path)
        original,request=await initial_state(service)
        monkeypatch.setattr(shutil,'disk_usage',lambda path:SimpleNamespace(free=0,total=100))
        assert service.capabilities()['state_storage']['free_bytes']==0
        assert (await initial_state(service))[0]==original  # durable retry must still work
        from test_native_state_service_recovery import prepared
        from test_openai_compat_runtime import _cache_binding
        binding=_cache_binding()
        with pytest.raises(service_module.HTTPException) as failure:
            await service.dispatch('create',prepared('create',lane_id=binding.lane_id,delta='new allocation',cache_binding=binding.to_dict()))
        assert failure.value.status_code==507
        await service.dispatch('release',release_request(original))
        assert not list(root.glob('*.pt'))
    asyncio.run(run())
