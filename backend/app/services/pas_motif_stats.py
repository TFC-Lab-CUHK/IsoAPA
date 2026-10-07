"""Shared PAS-motif categories for live and precomputed statistics."""

# Used by database queries to choose a stable annotation when a unified site is
# represented by multiple transcript rows. It does not filter summarized motifs.
PRIMARY_PAS_TYPES = frozenset(
    {
        "canonical",
        "variant",
        "plant_nue",
        "yeast_ee_pe",
        "pombe_a_rich",
    }
)


def summarize_pas_motif_rows(rows, top_n: int = 10) -> dict:
    ranked_counts: dict[str, int] = {}
    no_motif_count = 0
    other_count = 0
    not_assessed_count = 0

    for motif, pas_type, count in rows:
        count = int(count or 0)
        label = (motif or "").strip()
        motif_type = (pas_type or "").strip().lower()

        if motif_type == "not_assessed":
            not_assessed_count += count
        elif not label:
            no_motif_count += count
        else:
            ranked_counts[label] = ranked_counts.get(label, 0) + count

    total = (
        sum(ranked_counts.values())
        + no_motif_count
        + other_count
        + not_assessed_count
    )
    ranked = sorted(ranked_counts.items(), key=lambda item: (-item[1], item[0]))
    top = ranked[:top_n]
    other_count += sum(count for _, count in ranked[top_n:])
    if no_motif_count:
        top.append(("No motif", no_motif_count))
    if other_count:
        top.append(("Other motifs", other_count))
    if not_assessed_count:
        top.append(("Not assessed", not_assessed_count))

    return {
        "total": total,
        "motifs": [
            {
                "motif": motif,
                "count": count,
                "pct": round((count / total) * 100, 1) if total else 0,
            }
            for motif, count in top
        ],
    }
