"""Convert bound coding tasks or export format-verified native evidence."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.collection_conversion import convert_task, preview_input, export_boundaries


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    prepare=commands.add_parser('prepare')
    prepare.add_argument('--source',type=Path,required=True)
    prepare.add_argument('--binding',type=Path,required=True)
    prepare.add_argument('--output',type=Path,required=True)
    export=commands.add_parser('export-boundaries')
    export.add_argument('--run-root',type=Path,required=True)
    export.add_argument('--model-sha256',required=True)
    export.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare':
        item=convert_task(args.source,json.loads(args.binding.read_text()),args.output)
        preview=preview_input(item)
        (args.output/'PREVIEW.json').write_text(json.dumps(preview,ensure_ascii=False))
        (args.output/'inventory.jsonl').write_text(json.dumps(item,ensure_ascii=False)+'\n')
        print(json.dumps({'source_id':item['source_id'],'preview_tokens':len(preview['input_token_ids']),
                          'model_calls':0,'training_rows':0},ensure_ascii=False))
    else:
        result=export_boundaries(args.run_root,args.model_sha256,args.output)
        print(json.dumps({'boundaries':result['boundaries'],'training_rows':0}))


if __name__=='__main__':
    main()
