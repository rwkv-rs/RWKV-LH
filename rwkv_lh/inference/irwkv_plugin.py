"""irwkv extension registration; model equations and scheduling remain upstream."""


def register_worker():
    from irwkv.model_executor.models.rwkv import RwkvForCausalLM
    from .irwkv_native_worker import RWKV7ModelState
    RwkvForCausalLM.get_model_state_cls = staticmethod(lambda: RWKV7ModelState)


def endpoint():
    from .native_state_service import RWKVNativeStateEndpointPlugin
    return RWKVNativeStateEndpointPlugin()


class NativeStateWorkerExtension:
    def rwkv_native_state_action(self, action, payload):
        state = self.model_runner.model_state
        from .irwkv_native_worker import RWKV7ModelState
        if not isinstance(state, RWKV7ModelState):
            raise RuntimeError('irwkv persistent State worker plugin was not loaded')
        methods = {
            'capabilities': state.native_state_capabilities, 'seed': state.seed_native_state,
            'clone': state.clone_native_state, 'get': state.get_native_state,
            'drop': state.drop_native_state, 'rebind': state.rebind_native_state,
            'export': state.export_native_state, 'import': state.import_native_state,
            'delete_export': state.delete_native_state_export,
        }
        args = dict(payload)
        if action == 'capture':
            target = args.pop('state_ref')
            try:
                result = state.capture_native_request(**args, state_ref=target)
            except KeyError:
                result = state.finalize_staged_native_state(target, args['sampled_token_id'])
        else:
            if action not in methods:
                raise ValueError('unknown Native State action: ' + action)
            if action in ('export', 'import', 'delete_export'):
                if 'worker_rank' in args and args['worker_rank'] != self.rank:
                    raise ValueError('Native State export rank differs')
                args['worker_rank'] = self.rank
            result = methods[action](**args)
        return dict(result, worker_rank=self.rank)
