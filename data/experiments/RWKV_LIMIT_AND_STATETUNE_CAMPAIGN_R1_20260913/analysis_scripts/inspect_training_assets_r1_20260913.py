import torch,json,pathlib
p=pathlib.Path('/mnt/nas-model/g1j/rwkv7-g1j-13.3b-20260831-ctx16384.pth');w=torch.load(p,map_location='cpu',weights_only=True,mmap=True)
keys=['emb.weight','head.weight','blocks.0.att.w1','blocks.0.att.w2','blocks.0.att.v0','blocks.0.att.v1','blocks.0.att.v2','blocks.0.ffn.key.weight']
print(json.dumps({'source':str(p),'bytes':p.stat().st_size,'tensors':len(w),'selected':{k:{'shape':list(w[k].shape),'dtype':str(w[k].dtype)} for k in keys if k in w},'manifest':json.loads(pathlib.Path('/home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-13.3b-vllm-v1/manifest.json').read_text()),'config':json.loads(pathlib.Path('/home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-13.3b-vllm-v1/config.json').read_text())},indent=2))
