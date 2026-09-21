"""Run the calendar project's frozen black-box checks outside the Agent workspace."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.benchmark_verifier import run_isolated_verifier


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('output must be new; do not overwrite original evaluation')
    program=(Path(__file__).resolve().parents[1]/'benchmarks/calendar_project_v1/verify.py').read_text()
    digest=hashlib.sha256(program.encode()).hexdigest()
    args.output.mkdir(parents=True)
    result=run_isolated_verifier({'checks':[{'kind':'project_behavior','program':program,
        'program_sha256':digest,'browser':True,'timeout':120}]},args.workspace,[],{},
        private_root=args.output/'private',timeout_seconds=150)
    raw=result.checks[0].observation.get('output','')
    details=None
    for line in raw.splitlines():
        try:
            value=json.loads(line)
            if isinstance(value,dict) and 'checks' in value:details=value
        except ValueError:pass
    report={'passed':result.passed,'program_sha256':digest,'checks':[r.to_dict() for r in result.checks],
            'details':details,'metadata':result.metadata,'source_purpose':'development_evaluation_not_training'}
    (args.output/'RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if result.passed else 1


if __name__=='__main__':
    raise SystemExit(main())
