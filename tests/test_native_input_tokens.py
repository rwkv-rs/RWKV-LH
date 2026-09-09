"""Exercise the canonical Native service; no model capability labels."""
import asyncio
from dataclasses import replace

import pytest

from test_native_state_service import service_module
from test_native_state_service_recovery import service_fixture, prepared
from test_openai_compat_runtime import _cache_binding


@pytest.mark.parametrize("restart", [False, True])
def test_server_records_consumed_tokens_across_append_import_generate_and_restart(tmp_path, service_module, restart):
    async def scenario():
        exports, counters = {}, {}
        path = tmp_path / "journal.db"
        service = service_fixture(service_module, path, exports, counters)
        binding = _cache_binding()
        first = await service.dispatch("create", prepared("create", delta="ab", cache_binding=binding.to_dict()))
        binding = replace(binding, parent_state_digest=first["state_digest"], delta_digest="e" * 64)
        second = await service.dispatch("append", prepared("append", delta="cd",
            parent_state_ref=first["state_ref"], cache_binding=binding.to_dict()))
        if restart:
            service = service_fixture(service_module, path, exports, counters)
        alias = await service.dispatch("import", prepared("import", export_record=second["export_record"],
            cache_binding=binding.to_dict()))
        payload = prepared("generate", parent_state_ref=alias["state_ref"],
            parent_cache_binding_digest=binding.digest, request_id="GENERATE-proof", max_tokens=3,
            return_token_ids=True, sampling={}, stop=[])
        result = await service.dispatch("generate", payload)
        meta = result["candidate"]["metadata"]
        assert meta.get("prompt_token_ids") == list(b"abcd")
        assert meta.get("prompt_token_ids_scope") == "full_context"
        assert meta.get("input_bos_token_count") == 0
        assert meta["token_ids"] == [4, 5, 7]
        state = service._record(result["candidate"]["state_ref"])
        assert state.input_token_ids == list(b"abcd") + [4, 5, 7]
        # A receipt replay preserves the exact evidence and never samples twice.
        assert await service.dispatch("generate", payload) == result
        assert counters["sample"] == 1
    asyncio.run(scenario())
