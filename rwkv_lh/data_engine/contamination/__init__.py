"""Offline benchmark exclusion. A match is exclusion, never a training grant.

Only registered benchmark data is indexed. This module never opens a protected
holdout or downloads a source. Exact shingle sets avoid probabilistic false
negatives from MinHash; an inverted index limits the exact Jaccard comparisons.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone, time
import re
import unicodedata

from rwkv_lh.data_engine.tasks import checksum

SCHEMA = 'rwkv-lh.contamination-registry.v1'
CHECKER = 'exact-shingles.v1'
REQUIRED_SOURCES = ('swe-bench-test', 'swe-bench-lite', 'swe-bench-verified',
                    'swe-rebench-leaderboard', 'terminal-bench-2', 'agent-eval-rwkv',
                    'local-agent-15', 'core-loop-heldout')


def repository(value):
    value = str(value or '').strip().lower().removesuffix('/').removesuffix('.git')
    return re.sub(r'^(?:https?://github\.com/|git@github\.com:)', '', value)


def tokens(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    return re.findall(r'[\u3400-\u9fff]|[^\W_]+|_+|[^\w\s]', text)


def shingles(words, size):
    return {tuple(words[i:i + size]) for i in range(len(words) - size + 1)}


def timestamp(value, *, end_of_day=False):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('creation date is required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if len(value) == 10 and end_of_day:
        parsed = datetime.combine(parsed.date(), time.max)
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def make_registry(entries, *, cutoff, coverage, required_sources=REQUIRED_SOURCES):
    timestamp(cutoff)
    return {'schema_version': SCHEMA, 'checker_version': CHECKER, 'cutoff': cutoff,
            'required_sources': list(required_sources), 'coverage': deepcopy(coverage),
            'entries': deepcopy(entries)}


class Registry:
    def __init__(self, document):
        self.document = deepcopy(document)
        if document.get('schema_version') != SCHEMA or document.get('checker_version') != CHECKER:
            raise ValueError('unknown contamination registry or checker')
        self.sha256 = checksum(document)
        self.cutoff = timestamp(document['cutoff'], end_of_day=True)
        self.entries = document['entries']
        self.missing = []
        for name in document['required_sources']:
            item = document['coverage'].get(name, {})
            if item.get('status') == 'not_created' and name == 'core-loop-heldout':
                continue
            if not item.get('complete') or not item.get('revision'):
                self.missing.append(name)
            elif not any(e['benchmark'] == name for e in self.entries):
                raise ValueError('complete coverage requires actual benchmark entries: ' + name)
        self.instances, self.commits, self.hashes, self.repos = (defaultdict(set) for _ in range(4))
        self.grams13, self.grams5, self.exact = (defaultdict(set) for _ in range(3))
        self.sets5 = {}
        for i, entry in enumerate(self.entries):
            if entry.get('instance_id'):
                self.instances[entry['instance_id']].add(i)
            repo = repository(entry.get('repository'))
            if repo and entry.get('base_commit'):
                self.commits[(repo, entry['base_commit'].lower())].add(i)
            if repo and entry.get('repository_level'):
                self.repos[repo].add(i)
            for sha in [entry.get('gold_patch_sha256'), *entry.get('test_file_sha256', [])]:
                if sha:
                    self.hashes[sha].add(i)
            words = tokens(entry.get('text', ''))
            if words:
                self.exact[tuple(words)].add(i)
            for gram in shingles(words, 13):
                self.grams13[gram].add(i)
            self.sets5[i] = shingles(words, 5)
            for gram in self.sets5[i]:
                self.grams5[gram].add(i)

    def check(self, candidate):
        result = {key: 'pass' for key in ('registry', 'source', 'instance', 'text', 'repository', 'time')}
        result.update(registry_sha256=self.sha256, checker_version=CHECKER,
                      cutoff=self.document['cutoff'], hits=[])

        def hit(level, rule, indices=()):
            result[level] = 'exclude'
            result['hits'].append({'level': level, 'rule': rule, 'entries': sorted(indices)})

        if self.missing:
            hit('registry', 'incomplete:' + ','.join(self.missing))
        source = re.sub(r'[^a-z0-9]', '', str(candidate.get('source_dataset', '')).lower())
        if any(name in source for name in ('realagentholdout', 'acceptancetests', 'dataacceptance')):
            hit('source', 'protected_source')
        repo = repository(candidate.get('repository'))
        for rule, indices in (
            ('instance_id', self.instances.get(candidate.get('instance_id'), set())),
            ('repository_commit', self.commits.get((repo, str(candidate.get('base_commit', '')).lower()), set())),
        ):
            if indices:
                hit('instance', rule, indices)
        for sha in [candidate.get('gold_patch_sha256'), *candidate.get('test_file_sha256', [])]:
            if sha and sha in self.hashes:
                hit('instance', 'hidden_material_hash', self.hashes[sha])
        if repo in self.repos:
            hit('repository', 'benchmark_repository', self.repos[repo])
        words = tokens(candidate.get('text', ''))
        if not words:
            hit('text', 'missing_request')
        exact13 = set().union(*(self.grams13.get(g, set()) for g in shingles(words, 13)))
        if exact13:
            hit('text', 'thirteen_gram', exact13)
        grams5 = shingles(words, 5)
        possible = set().union(*(self.grams5.get(g, set()) for g in grams5))
        for i in sorted(possible):
            other = self.sets5[i]
            if len(grams5 & other) / len(grams5 | other) >= .8:
                hit('text', 'five_gram_jaccard', [i])
        if not grams5 and tuple(words) in self.exact:
            hit('text', 'short_exact_text', self.exact[tuple(words)])
        try:
            if timestamp(candidate.get('created_at')) > self.cutoff:
                hit('time', 'after_cutoff')
        except (TypeError, ValueError):
            hit('time', 'missing_or_invalid_date')
        result['passed'] = all(result[k] == 'pass' for k in ('registry', 'source', 'instance', 'text', 'repository', 'time'))
        return result
