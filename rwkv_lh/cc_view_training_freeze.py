"""CPU-only freeze, task-family split and sealed loading of CC-view episodes."""
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path

from . import cc_view_experiment as cc
from .cc_view_training_data import DATASET_SCHEMA,episode_row
from .statetune_core import require,sha256_file,verify_file
from .statetune_episodes import validate_row

_TOKENIZER=None


def _init_worker():
    global _TOKENIZER
    from .token_budget import tokenizer
    _TOKENIZER=tokenizer()


def _encode(item):
    require(_TOKENIZER is not None,'encoding worker not initialized')
    row=episode_row(item['converted'],episode_id=item['episode_id'],source=item['source'],tokenizer=_TOKENIZER)
    row.update(source_line=item['line'],source_sha256=item['source_sha256'],task_family=item['task_family'])
    return row


def embed_complete(texts,identity):
    """Use every source token, including requests longer than the encoder limit."""
    os.environ['CUDA_VISIBLE_DEVICES']=''
    import numpy as np
    import torch
    from sentence_transformers import SentenceTransformer
    for row in identity['files']:verify_file((Path(identity['local_path'])/row['path']).resolve(strict=True),row['sha256'])
    torch.set_num_threads(min(8,os.cpu_count() or 1))
    model=SentenceTransformer(identity['local_path'],device='cpu',trust_remote_code=False,local_files_only=True)
    size=model.max_seq_length-model.tokenizer.num_special_tokens_to_add(pair=False)
    cls=model.tokenizer.cls_token_id;sep=model.tokenizer.sep_token_id;pad=model.tokenizer.pad_token_id
    require(cls is not None and sep is not None and pad is not None,'embedding tokenizer must declare its special tokens')
    for probe in ('生成一个静态网页','Build a static website'):
        bare=model.tokenizer.encode(probe,add_special_tokens=False,truncation=False)
        require(model.tokenizer.encode(probe,add_special_tokens=True,truncation=False)==[cls,*bare,sep],
                'embedding tokenizer special-token layout differs')
    pieces=[];owners=[];weights=[];token_counts=[]
    for index,text in enumerate(texts):
        ids=model.tokenizer.encode(text,add_special_tokens=False,truncation=False)
        require(bool(ids),'empty requirement embedding input')
        token_counts.append(len(ids))
        for start in range(0,len(ids),size):
            chunk=ids[start:start+size]
            features={'input_ids':[cls,*chunk,sep]}
            require(len(features['input_ids'])<=model.max_seq_length,'embedding chunk exceeds encoder capacity')
            pieces.append(dict(features))
            owners.append(index);weights.append(len(chunk))
    require(sum(weights)==sum(token_counts),'embedding chunks dropped content tokens')
    model.eval();encoded=[]
    with torch.no_grad():
        for start in range(0,len(pieces),32):
            examples=pieces[start:start+32];length=max(len(item['input_ids']) for item in examples)
            ids=torch.full((len(examples),length),pad,dtype=torch.long);attention=torch.zeros_like(ids)
            for index,item in enumerate(examples):
                tokens=item['input_ids'];offset=length-len(tokens) if model.tokenizer.padding_side=='left' else 0
                ids[index,offset:offset+len(tokens)]=torch.tensor(tokens,dtype=torch.long)
                attention[index,offset:offset+len(tokens)]=1
            batch={'input_ids':ids,'attention_mask':attention}
            if 'token_type_ids' in model.tokenizer.model_input_names:batch['token_type_ids']=torch.zeros_like(ids)
            encoded.append(model(batch)['sentence_embedding'].detach().cpu().numpy())
            if start%640==0:print(json.dumps(dict(embedding_chunks=min(start+32,len(pieces)),total=len(pieces))),flush=True)
    vectors=np.concatenate(encoded)
    result=np.zeros((len(texts),vectors.shape[1]),dtype=np.float64)
    for vector,owner,weight in zip(vectors,owners,weights):result[owner]+=vector*weight
    result/=np.linalg.norm(result,axis=1,keepdims=True)
    require(not torch.cuda.is_initialized(),'embedding audit initialized CUDA')
    return result.astype(np.float32),dict(requests=len(texts),chunks=len(pieces),tokens=sum(token_counts),
        encoder_content_capacity=size,max_request_tokens=max(token_counts),truncated_requests=0,cuda_used=False)


def family_split(items,vectors,*,threshold,seed,fraction):
    """Connected semantic families stay whole; never force an exact row fraction."""
    import numpy as np
    parents=list(range(len(items)))
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    pairs=0
    for i,vector in enumerate(vectors):
        for j in np.flatnonzero(vectors[i+1:]@vector>threshold)+i+1:
            a,b=find(i),find(int(j))
            if a!=b:parents[b]=a
            pairs+=1
    groups=defaultdict(list)
    for index in range(len(items)):groups[find(index)].append(index)
    groups=list(groups.values());totals=Counter(item['source'] for item in items)
    counts=[Counter(items[i]['source'] for i in group) for group in groups]
    hashes=[hashlib.sha256((str(seed)+'/'+min(items[i]['episode_id'] for i in group)).encode()).hexdigest() for group in groups]
    chosen=set();validation=Counter()
    def objective(value):return sum((value[s]/total-fraction)**2 for s,total in totals.items())
    def possible(index):return all(validation[s]+n<totals[s] for s,n in counts[index].items())
    # Every source must have train and validation exposure, without splitting families.
    for source in sorted(totals):
        if validation[source]:continue
        options=[i for i in range(len(groups)) if i not in chosen and counts[i][source] and possible(i)]
        require(bool(options),'cannot cover every source in train and validation with whole families')
        best=min(options,key=lambda i:(objective(validation+counts[i]),hashes[i]))
        chosen.add(best);validation.update(counts[best])
    while True:
        options=[i for i in range(len(groups)) if i not in chosen and possible(i)
                 and objective(validation+counts[i])<objective(validation)-1e-15]
        if not options:break
        best=min(options,key=lambda i:(objective(validation+counts[i]),hashes[i]))
        chosen.add(best);validation.update(counts[best])
    valid_indices={index for group in chosen for index in groups[group]}
    for group_id,indices in enumerate(groups):
        family=hashes[group_id]
        for index in indices:items[index]['task_family']=family
    return valid_indices,dict(semantic_pairs=pairs,families=len(groups),target_fraction=fraction,
        actual_validation_counts=dict(validation),source_counts=dict(totals),
        actual_validation_fractions={str(s):validation[s]/totals[s] for s in totals},family_overlap=0)


def freeze(normalized_path,output,*,registration,embedding_identity,evaluation_requests,audit_directory,workers=4):
    output=Path(output)
    if output.exists():require(not any(output.iterdir()),'refuse to overwrite any existing dataset files')
    else:output.mkdir(parents=True,exist_ok=False)
    audit=Path(audit_directory);audit.mkdir(parents=True,exist_ok=False)
    items=[json.loads(line) for line in Path(normalized_path).open() if line.strip()]
    require({item['source'] for item in items}==set(range(1,7)),'all six authorized sources required')
    evaluation=[item['request'] for item in evaluation_requests]
    # Normalization removes a display heading only in the similarity view.
    requests=[item['converted']['request'].removeprefix('## original_request\n') for item in items]
    vectors,embedding_audit=embed_complete([*requests,*evaluation],embedding_identity)
    source_vectors,eval_vectors=vectors[:len(items)],vectors[len(items):]
    similarities=source_vectors@eval_vectors.T
    excluded=[];kept=[];kept_vectors=[]
    eval_hashes={hashlib.sha256(text.encode()).hexdigest() for text in evaluation}
    for i,item in enumerate(items):
        nearest=int(similarities[i].argmax());score=float(similarities[i,nearest])
        same_origin=(hashlib.sha256(requests[i].encode()).hexdigest() in eval_hashes
                     or item['episode_id'] in {row['task_id'] for row in evaluation_requests})
        if same_origin or score>registration['dataset']['embedding']['eval_exclusion_cosine']:
            excluded.append(dict(episode_id=item['episode_id'],source=item['source'],line=item['line'],
                source_sha256=item['source_sha256'],reason='same_origin' if same_origin else 'evaluation_embedding_near_duplicate',
                closest_evaluation_task=evaluation_requests[nearest]['task_id'],cosine=score))
        else:kept.append(item);kept_vectors.append(source_vectors[i])
    import numpy as np
    valid,split=family_split(kept,np.asarray(kept_vectors),threshold=registration['dataset']['embedding']['family_cosine'],
                           seed=registration['dataset']['embedding']['split_seed'],fraction=.05)
    (audit/'EVAL_EXCLUSIONS.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2)+'\n')
    (audit/'EMBEDDING_AUDIT.json').write_text(json.dumps(embedding_audit,ensure_ascii=False,indent=2)+'\n')
    source_counts=defaultdict(Counter);mask_reasons=Counter();action_tokens=Counter();files=[]
    handles={'train':(output/'TRAIN.jsonl').open('x'),'validation':(output/'VALIDATION.jsonl').open('x')}
    totals={'train':Counter(),'validation':Counter()};families={'train':set(),'validation':set()}
    try:
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'),initializer=_init_worker) as pool:
            for index,row in enumerate(pool.map(_encode,kept,chunksize=1)):
                key='validation' if index in valid else 'train';families[key].add(row['task_family'])
                source=row['source'];counts=source_counts[source];counts['episodes']+=1;counts[key+'_episodes']+=1
                token_count=len(row['token_ids']);supervised=sum(n for (_,n),mark in zip(row['target_spans'],row['supervised']) if mark)
                totals[key].update(episodes=1,tokens=token_count,supervised_target_tokens=supervised,chunks=len(row['chunk_starts']))
                counts.update(tokens=token_count,supervised_target_tokens=supervised)
                for (_,count),mark,action in zip(row['target_spans'],row['supervised'],row['actions']):
                    if mark:action_tokens[action]+=count
                    else:counts['masked_model_tokens']+=count
                for decision in row['mask_audit']:mask_reasons[decision['reason']]+=1
                for turn in kept[index]['converted']['turns']:
                    if not turn['supervised']:mask_reasons[turn.get('context_reason','original_self_supervision_mask')]+=1
                handles[key].write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
                if index%100==0:print(json.dumps(dict(encoded=index+1,total=len(kept),split=key)),flush=True)
    finally:
        for handle in handles.values():handle.close()
    require(not families['train']&families['validation'],'task family leakage')
    for key,name in [('train','TRAIN.jsonl'),('validation','VALIDATION.jsonl')]:
        files.append(dict(path=name,split=key,sha256=sha256_file(output/name),**dict(totals[key])))
    from .token_budget import VOCAB_PATH
    source_self_manifest=json.loads((Path(registration['source_paths'][5])/'MANIFEST.json').read_text())
    model_sha=source_self_manifest['model_sha256']
    manifest=dict(schema_version=DATASET_SCHEMA,input_protocol=cc.PROTOCOL,protocol_sha256=sha256_file(Path(cc.__file__)),
        tokenizer_sha256=sha256_file(VOCAB_PATH),model_sha256=model_sha,bos_token_id=0,vocab_size=65536,max_chunk_tokens=16384,
        generator_sha256=sha256_file(Path(__file__)),data_generator_sha256=sha256_file(Path(__file__).with_name('cc_view_training_data.py')),
        source_normalized_sha256=sha256_file(normalized_path),raw_source_read_only=True,
        source_counts={str(s):dict(c) for s,c in source_counts.items()},files=files,split=split,
        embedding=dict(model=embedding_identity['model_id'],revision=embedding_identity['revision'],
                       threshold=registration['dataset']['embedding']['eval_exclusion_cosine'],audit=embedding_audit),
        evaluation_exclusions=len(excluded),evaluation_audit_reference={'path':str(audit/'EVAL_EXCLUSIONS.json'),'sha256':sha256_file(audit/'EVAL_EXCLUSIONS.json')},
        mask_policy='Original self masks retained; unrepresentable source turns and over-cap source think are context-only; valid surrounding model segments remain supervised.',
        mask_reasons=dict(mask_reasons),supervised_tokens_by_action=dict(action_tokens),
        domain_record_counts=dict(frontend_including_fullstack=sum(c['episodes'] for s,c in source_counts.items() if s in (2,4,5,6)),
                                 backend_cli_including_fullstack=sum(c['episodes'] for s,c in source_counts.items() if s in (1,2,3)),
                                 fullstack_counted_in_both=source_counts[2]['episodes'],total=len(kept)),
        domain_note='Fullstack source 2 belongs to both requested domain coverages; the two percentages overlap and must not be summed.',
        source_authorizations='CCVIEW_TRAIN_12H_20261021 original prompt and continuation quality addendum',training_eligible=True)
    (output/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return manifest


def load_split(manifest_path,expected_sha,split,*,context_tokens):
    path=verify_file(manifest_path,expected_sha);manifest=json.loads(path.read_text())
    require(manifest['schema_version']==DATASET_SCHEMA and manifest['input_protocol']==cc.PROTOCOL,
            'requires the separate current CC-view training entrance')
    require(manifest['protocol_sha256']==sha256_file(Path(cc.__file__)),'CC-view renderer changed after dataset freeze')
    from .token_budget import VOCAB_PATH
    require(manifest['tokenizer_sha256']==sha256_file(VOCAB_PATH),'tokenizer differs from frozen CC-view data')
    row=next(item for item in manifest['files'] if item['split']==split)
    file=verify_file(path.parent/row['path'],row['sha256']);rows=[json.loads(line) for line in file.open() if line.strip()]
    require(len(rows)==row['episodes'],'CC-view split count differs')
    count=0
    for sample in rows:
        require(sample['input_protocol']==cc.PROTOCOL,'cross-view episode mixing refused')
        count+=validate_row(sample,context_tokens=context_tokens,vocab_size=manifest['vocab_size'],bos_token_id=manifest['bos_token_id'])
    require(count==row['supervised_target_tokens'],'CC-view target mask count differs')
    return rows,manifest
