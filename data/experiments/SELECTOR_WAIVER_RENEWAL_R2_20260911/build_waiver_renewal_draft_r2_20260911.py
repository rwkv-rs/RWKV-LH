"""Build the DRAFT waiver renewal covering statetune_data.py's new SHA.

Carries forward the 10 accepted entries from SCOPED_EQUIVALENCE_WAIVER_ACCEPTED
(f53186ec…) unchanged — their pinned current SHAs are verified to still match
the working tree — and adds one entry for rwkv_lh/statetune_data.py (changed by
STATETUNE_FREEZE_WIRING_R1_20260911, commit 162e60ee). decision stays "draft"
until the two authorized reviewers re-sign. Frozen SHA source: the same frozen
source_tree_manifest the old 14 sources pinned; the fresh COMMAND_PATH sources
share the same frozen statetune_data.py SHA (file unchanged between e7c455b6
and 21c0cf45), so one entry covers both source groups.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path('/home/chase/GitHub/RWKV-LH')
ACCEPTED = ROOT / 'data/experiments/SELECTOR_WAIVER_RENEWAL_R1_20260910/SCOPED_EQUIVALENCE_WAIVER_ACCEPTED.json'
TARGET = 'rwkv_lh/statetune_data.py'

accepted = json.loads(ACCEPTED.read_text())
assert accepted['decision'] == 'accept' and len(accepted['entries']) == 10
for entry in accepted['entries']:
    current = hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest()
    assert current == entry['current_sha256'], f"carried entry stale: {entry['path']}"
    assert entry['path'] != TARGET

manifests = [
    ROOT / 'data/experiments/REALPROJECT_OFFICIAL_COLLECTION_R3_20260910/all_zero/source_tree_manifest.json',
    ROOT / 'data/experiments/ULTRADATA_OFFICIAL_COLLECTION_R6_20260910/all_zero/source_tree_manifest.json',
]
frozen_shas = set()
for manifest_path in manifests:
    manifest = json.loads(manifest_path.read_text())
    frozen_shas.update(item['sha256'] for item in manifest if item['path'] == TARGET)
assert len(frozen_shas) == 1, f'frozen SHA disagrees: {sorted(frozen_shas)}'
frozen = next(iter(frozen_shas))
current = hashlib.sha256((ROOT / TARGET).read_bytes()).hexdigest()
assert frozen != current, 'statetune_data.py appears unchanged; renewal unnecessary'

value = {
    'schema_version': accepted['schema_version'],
    'decision': 'draft',
    'reviewers': ['REVIEWER-ONE-TBD', 'REVIEWER-TWO-TBD'],
    'entries': [*accepted['entries'], {
        'path': TARGET, 'frozen_sha256': frozen, 'current_sha256': current,
        'rationale': (
            'STATETUNE_FREEZE_WIRING_R1_20260911 (162e60ee): freeze_dataset now replays '
            'the pinned admission waiver bidirectionally and an optional sealed row '
            'selection (membership filter only; rows never constructed or edited). '
            'No role protocol, prompt builder contract, State semantics, or admission '
            'default behavior changed; checkpoint byte rebuild and token replay '
            'defenses remain unconditional.'),
        'evidence_refs': [
            'data/experiments/STATETUNE_FREEZE_WIRING_R1_20260911/REPORT.zh-CN.md',
            'data/experiments/STATETUNE_FREEZE_WIRING_R1_20260911/EVIDENCE_SHA256.json',
        ],
    }],
}
out_dir = ROOT / 'data/experiments/SELECTOR_WAIVER_RENEWAL_R2_20260911'
out_dir.mkdir(exist_ok=True)
out = out_dir / 'EQUIVALENCE_WAIVER_RENEWAL_DRAFT.json'
out.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'entries': len(value['entries']), 'added': TARGET,
                  'frozen': frozen[:16], 'current': current[:16],
                  'draft_sha256': hashlib.sha256(out.read_bytes()).hexdigest()}, indent=2))
