from pathlib import Path
import sys,json,hashlib,importlib.util,os
R=Path('/home/chase/GitHub/RWKV-LH-direct-statetune-r1-20260913');sys.path.insert(0,str(R/'source_r2'));S=R/'artifact_patch/prepare_rwkv_vllm_artifact.py';expected=sys.argv[1];assert hashlib.sha256(S.read_bytes()).hexdigest()==expected
spec=importlib.util.spec_from_file_location('converter_patch',S);converter=importlib.util.module_from_spec(spec);spec.loader.exec_module(converter)
from safetensors import safe_open
old=R/'model';D=R/'model_serving_r2';D.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p in old.iterdir():
 if p.is_file() and p.name not in ['manifest.json','model.safetensors.index.json']:os.link(p,D/p.name)
with safe_open(D/'model.safetensors',framework='pt',device='cpu') as weights:names=list(weights.keys())
converter.write_weight_index(D,names);m=json.loads((old/'manifest.json').read_text());m['output']['weights_index_sha256']=sha(D/'model.safetensors.index.json');m['serving_index_derivation']={'original_artifact_manifest_sha256':sha(old/'manifest.json'),'producer_script_sha256':expected,'purpose':'Explicit standard inference shard index excludes preserved audit sidecar; all original tensor/config/vocab bytes hard-linked, original artifact unchanged','runtime_tensor_count':len(names)};converter.write_json(D/'manifest.json',m)
profile=json.loads((R/'training_runs/direct-read-r1-20260913/STATE_PROFILES.json').read_text());profile['model_artifact']=str(D);converter.write_json(R/'evaluation_service/STATE_PROFILES_R2.json',profile)
# Exercise the actual engine file selector, not an imitation of its glob policy.
sys.path.insert(1,'/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/engine')
from vllm.config.load import LoadConfig
from vllm.model_executor.model_loader.default_loader import DefaultModelLoader
loader=DefaultModelLoader(LoadConfig());folder,files,uses_safe=loader._prepare_weights(str(D),revision=None,fall_back_to_pt=True);assert files==[str(D/'model.safetensors')] and uses_safe
converter.write_json(R/'artifact_patch/RESULT.json',{'runtime_weight_files':files,'unused_preserved':(D/'native_unused_layer0_value_mix.safetensors').exists(),'index_sha256':m['output']['weights_index_sha256'],'manifest_sha256':sha(D/'manifest.json'),'profile_sha256':sha(R/'evaluation_service/STATE_PROFILES_R2.json'),'original_artifact_unchanged':sha(old/'manifest.json')==m['serving_index_derivation']['original_artifact_manifest_sha256'],'optimizer_steps':0});print('loader selected only model.safetensors',flush=True)
