from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,importlib.metadata,time
ROOT=Path('/home/chase/GitHub/RWKV-LH-direct-statetune-r1-20260913');SOURCE=ROOT/'source';sys.path.insert(0,str(SOURCE));sys.path.insert(1,'/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/engine')
os.environ['CUDA_HOME']='/home/chase/GitHub/RWKV-LH-r20-fp32io16/data/runtime/cuda-12.8';os.environ['CXX']='/usr/bin/x86_64-linux-gnu-g++-13';os.environ['TORCH_CUDA_ARCH_LIST']='12.0';os.environ['MAX_JOBS']='4';os.environ['OMP_NUM_THREADS']='4';os.environ['VLLM_RWKV7_WKV_MODE']='fp32io16'
from rwkv_lh.statetune_native_runtime import CFLAGS,CUDA_FLAGS,TRANSLATION_UNITS,NATIVE_BUILD_VERSION,native_source_records
from rwkv_lh.inference.uploaded_sources import verify_manifest,PROJECT_SCHEMA
import torch
from torch.utils.cpp_extension import load
D=ROOT/'native_build';D.mkdir(exist_ok=False);started=time.time()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n');return sha(p)
project=ROOT/'validation/PROJECT_SOURCE.json';verify_manifest(project,sha(project),expected_schema=PROJECT_SCHEMA,expected_root=SOURCE)
before=native_source_records(SOURCE);module=load(name='rwkv_lh_r26_decay_fp32',sources=[str(SOURCE/'rwkv_lh/statetune_native_csrc'/p) for p in TRANSLATION_UNITS],extra_cflags=CFLAGS,extra_cuda_cflags=CUDA_FLAGS,build_directory=str(D),verbose=True)
assert before==native_source_records(SOURCE)
compiler={}
for name,path,args in [('nvcc',Path(os.environ['CUDA_HOME'])/'bin/nvcc',['--version']),('cxx',Path(os.environ['CXX']),['--version']),('python',Path(sys.executable).resolve(),['--version'])]:
 compiler[name]={'path':str(path),'sha256':sha(path),'version':subprocess.check_output([str(path),*args],text=True).strip()}
toolchain_paths=[]
for folder in [Path(os.environ['CUDA_HOME'])/'bin',Path(os.environ['CUDA_HOME'])/'include',Path(os.environ['CUDA_HOME'])/'nvvm',Path(torch.__file__).parent/'include']:
 toolchain_paths.extend(p.resolve() for p in folder.rglob('*') if p.is_file())
toolchain=save(D/'TOOLCHAIN.json',{'compiler':compiler,'files':[{'path':str(p),'sha256':sha(p)} for p in sorted(set(toolchain_paths))]});compiler['toolchain_manifest']={'path':str(D/'TOOLCHAIN.json'),'sha256':toolchain}
build={'schema_version':NATIVE_BUILD_VERSION,'module_name':'rwkv_lh_r26_decay_fp32','source_files':before,'cflags':CFLAGS,'cuda_flags':CUDA_FLAGS,'extension':{'path':str(Path(module.__file__).resolve()),'sha256':sha(module.__file__)},'compiler':compiler,'build_ninja':{'path':str(D/'build.ninja'),'sha256':sha(D/'build.ninja')},'environment':{'torch_version':str(torch.__version__),'torch_cuda':torch.version.cuda,'torch_cxx11_abi':torch._C._GLIBCXX_USE_CXX11_ABI,'gpu_capability':list(torch.cuda.get_device_capability())},'elapsed_seconds':time.time()-started,'optimizer_steps':0}
bs=save(D/'BUILD_MANIFEST.json',build)
import flash_rwkv,vllm.rwkv7_ops
# Warm basic CUDA libraries, not model training, before sealing actual dependencies.
x=torch.ones((32,32),device='cuda',dtype=torch.float16);(x@x).sum().item();del x
deps=json.loads((ROOT/'validation/NATIVE_DEPENDENCIES.json').read_text());deps['python_executable']=str(Path(sys.executable).resolve());deps['python']=sys.version;deps['packages']={k:importlib.metadata.version(k) for k in deps['packages']};deps['torch_cuda']=torch.version.cuda;deps['torch_build']=torch.__config__.show();deps['flash_package_root']=str(Path(flash_rwkv.__file__).resolve().parent)
def records(paths):return [{'path':str(p),'size':p.stat().st_size,'sha256':sha(p)} for p in sorted(set(paths))]
deps['flash_files']=records([p.resolve() for p in Path(deps['flash_package_root']).rglob('*') if p.is_file() and '__pycache__' not in p.parts]);paths={Path(r['path']).resolve() for r in deps['loaded_libraries']}
for line in Path('/proc/self/maps').read_text().splitlines():
 fields=line.split(maxsplit=5)
 if len(fields)==6 and fields[5].startswith('/') and '.so' in fields[5]:
  assert not fields[5].endswith(' (deleted)');paths.add(Path(fields[5]).resolve())
deps['loaded_libraries']=records(paths);deps['provenance']={'source':'current package files and actually loaded libraries plus existing sealed runtime dependency coverage','native_extension_recompiled':True,'reason':'compiler Python binary identity drift rejected old build','optimizer_steps':0};ds=save(D/'DEPENDENCIES.json',deps)
print(json.dumps({'build_sha256':bs,'dependencies_sha256':ds,'elapsed_seconds':time.time()-started,'optimizer_steps':0}),flush=True)
