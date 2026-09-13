"""Document RRF followed by BM25 inside selected documents; no semantic rules."""
import asyncio


async def document_groups(index, queries, *, candidate_k, knowledge_base_id, document_limit):
    initial = await asyncio.gather(*(asyncio.to_thread(index.search_chunks, query,
        candidate_k=candidate_k, knowledge_base_id=knowledge_base_id, collapse_documents=True)
        for query in queries))
    scores, votes = {}, []
    for query_index, group in enumerate(initial):
        seen = set()
        for rank, hit in enumerate(group, 1):
            if hit.document_id in seen:
                continue
            seen.add(hit.document_id)
            weight = 1 / (60 + rank)
            scores[hit.document_id] = scores.get(hit.document_id, 0) + weight
            votes.append({"query_index": query_index, "document_id": hit.document_id,
                          "best_chunk_id": hit.node_id, "rank": rank, "rrf_contribution": weight})
    selected = sorted(scores, key=lambda document: -scores[document])[:document_limit]
    expanded = (await asyncio.gather(*(asyncio.to_thread(index.search_chunks, query,
        candidate_k=candidate_k, knowledge_base_id=knowledge_base_id, document_ids=selected)
        for query in queries))) if selected else [[] for _ in queries]
    if any(hit.document_id not in selected for group in expanded for hit in group):
        raise ValueError("document-scoped search returned an unselected document")
    return expanded, {"scope": "documents", "selected_document_ids": selected,
        "document_limit": document_limit, "rrf_scores": scores, "rrf_votes": votes,
        "document_candidates": [[h.document_id for h in group] for group in initial],
        "expanded_chunk_ids": [[h.node_id for h in group] for group in expanded],
        "passage_query_policy": "each original model query, restricted to the selected documents"}
