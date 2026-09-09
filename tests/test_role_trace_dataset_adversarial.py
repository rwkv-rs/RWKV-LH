"""Adversarial review metadata tests; no role examples or external datasets."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from rwkv_lh.goal_state_protocols import role_trace_dataset_v1 as pipeline


def _review_pair():
    row = dict(
        request_id="TEST-RAW-REQUEST", role="executor_args",
        input_text="opaque complete input bytes", target_text="opaque raw output bytes",
        coverage=dict(failed_last_action=True),
    )
    reviews = [dict(
        request_id=row["request_id"], role=row["role"],
        input_sha256=pipeline._digest(row["input_text"]),
        target_sha256=pipeline._digest(row["target_text"]),
        decision="accept", purpose="failure_recovery_positive", reviewer_id=reviewer,
    ) for reviewer in ("human-one", "human-two")]
    return row, reviews


def test_two_reviews_bind_one_exact_failure_context_and_original_target():
    row, reviews = _review_pair()
    assert pipeline._review_authority(SimpleNamespace(reviews=reviews), row) == ["human-one", "human-two"]


@pytest.mark.parametrize("reviewers", [
    ("same-human", "same-human"), ("same-human", " same-human "), ("", "human-two"),
])
def test_two_review_records_cannot_impersonate_two_distinct_reviewers(reviewers):
    row, reviews = _review_pair()
    for review, identity in zip(reviews, reviewers, strict=True):
        review["reviewer_id"] = identity
    with pytest.raises(pipeline.DatasetIntegrityError, match="review"):
        pipeline._review_authority(SimpleNamespace(reviews=reviews), row)


@pytest.mark.parametrize("field", ["input_sha256", "target_sha256", "purpose", "decision"])
def test_review_must_not_label_different_bytes_or_purpose(field):
    row, reviews = _review_pair()
    reviews[1][field] = "different"
    with pytest.raises(pipeline.DatasetIntegrityError, match="bind"):
        pipeline._review_authority(SimpleNamespace(reviews=reviews), row)


def test_review_cannot_grant_positive_authority_without_failure_context():
    row, reviews = _review_pair()
    row["coverage"]["failed_last_action"] = False
    with pytest.raises(pipeline.DatasetIntegrityError, match="failure"):
        pipeline._review_authority(SimpleNamespace(reviews=reviews), row)


@pytest.mark.parametrize("count", [1, 3])
def test_review_pair_must_have_exactly_two_records(count):
    row, reviews = _review_pair()
    reviews = reviews[:1] if count == 1 else reviews + [deepcopy(reviews[0])]
    with pytest.raises(pipeline.DatasetIntegrityError, match="exactly two"):
        pipeline._review_authority(SimpleNamespace(reviews=reviews), row)
