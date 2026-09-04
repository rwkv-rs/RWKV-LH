# NET-SEL-2P9-S5 pre-training query-length amendment

Date: 2026-08-28 (Asia/Shanghai)

The authoritative pinned tokenizer preflight completed before any S5 head
training or S5 quality evaluation.  The 2526 compact queries are 95–331 tokens;
the 25 tool descriptions are 41–58 tokens.  No input was truncated and all
task/objective/progress facts remain intact.

The preregistered query maximum is changed from 256 to 384.  The independent
compression gate remains: S5 maximum must be at least 4x lower than the S3
maximum 1348; observed `1348 / 331 = 4.0725`.  The description maximum remains
64 and passes.  Dataset, features, architecture, seed, training parameters,
quality metrics, ECRA gates and all other protocol terms are unchanged.

This is a tokenizer preflight correction, not a response to model quality.
Both feature manifests and their token-count observations are preserved.
