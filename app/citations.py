import re

_REF_RE = re.compile(r"\[S(\d+)\]")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_TOKEN_RE = re.compile(r"[\wÀ-ÿ]{3,}", re.UNICODE)


def _tokens(text):
    return set(_TOKEN_RE.findall((text or "").lower()))


def verify_citations(answer, sources, min_overlap=0.08):
    source_map = {i: src for i, src in enumerate(sources, 1)}
    referenced = {int(x) for x in _REF_RE.findall(answer or "")}
    invalid = sorted(x for x in referenced if x not in source_map)
    valid_referenced = referenced - set(invalid)

    claims = []
    for raw in _SENTENCE_RE.split(answer or ""):
        sentence = raw.strip()
        if len(sentence) < 25 or sentence.endswith(":"):
            continue
        refs = [int(x) for x in _REF_RE.findall(sentence)]
        clean = _REF_RE.sub("", sentence).strip()
        claim_tokens = _tokens(clean)
        if len(claim_tokens) < 3:
            continue
        best_overlap = 0.0
        valid_refs = [r for r in refs if r in source_map]
        for ref in valid_refs:
            evidence_tokens = _tokens(source_map[ref].get("text", ""))
            if evidence_tokens:
                best_overlap = max(best_overlap, len(claim_tokens & evidence_tokens) / len(claim_tokens))
        supported = bool(valid_refs) and best_overlap >= min_overlap
        claims.append({
            "text": clean[:240],
            "references": valid_refs,
            "overlap": round(best_overlap, 3),
            "supported": supported,
        })

    supported_count = sum(1 for c in claims if c["supported"])
    checked = len(claims)
    ratio = supported_count / checked if checked else (1.0 if valid_referenced else 0.0)
    coverage = len(valid_referenced) / len(source_map) if source_map else 0.0
    if invalid or ratio < 0.55:
        confidence = "low"
    elif ratio < 0.85:
        confidence = "medium"
    else:
        confidence = "high"
    return {
        "confidence": confidence,
        "claims_checked": checked,
        "supported_claims": supported_count,
        "unsupported_claims": max(0, checked - supported_count),
        "invalid_references": invalid,
        "sources_referenced": len(valid_referenced),
        "source_coverage": round(coverage, 3),
        "details": claims[:20],
        "method": "reference+lexical-evidence heuristic",
    }
