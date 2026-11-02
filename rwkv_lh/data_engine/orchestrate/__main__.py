import argparse,asyncio,fcntl,json
from pathlib import Path
from . import campaign

def main():
    parser=argparse.ArgumentParser(description='Offline execution-verified round-0 data collection')
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--teacher-config',type=Path,required=True)
    parser.add_argument('--tasks-manifest',type=Path,required=True)
    parser.add_argument('--count',type=int)
    parser.add_argument('--workers',type=int,default=32)
    parser.add_argument('--max-attempts',type=int,default=3)
    args=parser.parse_args()
    if min(args.count or 1,args.workers,args.max_attempts)<1:parser.error('positive counts required')
    args.root.mkdir(parents=True,exist_ok=True)
    with (args.root/'campaign.lock').open('a') as claim:
        fcntl.flock(claim,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=asyncio.run(campaign(args.root,json.loads(args.teacher_config.read_text())['providers'],count=args.count,tasks_manifest=args.tasks_manifest,
            workers=args.workers,max_attempts=args.max_attempts))
    print(json.dumps(result,indent=2))
    return 0 if set(result['jobs'])=={'done'} else 1

if __name__=='__main__':raise SystemExit(main())
