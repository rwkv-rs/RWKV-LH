from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH-direct-statetune-r1-20260913');sys.path[:0]=[str(R/'source_r2'),'/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/engine']
from vllm.config.load import LoadConfig
from vllm.model_executor.model_loader.default_loader import DefaultModelLoader
D=R/'model_serving_r2';loader=DefaultModelLoader(LoadConfig());kwargs={'revision':None,'subfolder':None,'fall_back_to_pt':True,'allow_patterns_overrides':None};_,oldfiles,_=loader._prepare_weights(str(R/'model'),**kwargs);_,files,uses=loader._prepare_weights(str(D),**kwargs);assert len(oldfiles)==2 and files==[str(D/'model.safetensors')] and uses
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((D/'manifest.json').read_text());result={'runtime_weight_files':files,'original_unindexed_weight_files':oldfiles,'unused_preserved':(D/'native_unused_layer0_value_mix.safetensors').exists(),'index_sha256':sha(D/'model.safetensors.index.json'),'manifest_sha256':sha(D/'manifest.json'),'profile_sha256':sha(R/'evaluation_service/STATE_PROFILES_R2.json'),'original_artifact_unchanged':sha(R/'model/manifest.json')==m['serving_index_derivation']['original_artifact_manifest_sha256'],'optimizer_steps':0};(R/'artifact_patch/RESULT_R2.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
