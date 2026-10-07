"""Species context and evidence summaries for unique, retained PAS clusters."""

from collections import defaultdict

from sqlalchemy import func

from app.models.database import APASite, Sample, Species


MOTIF_MODELS = {
    "mammalian": "Mammalian",
    "land_plant": "Land plant",
    "budding_yeast": "Budding yeast",
    "fission_yeast": "Fission yeast",
    "not_assessed": "Not assessed",
}
PAS_LEVELS = ("PAS-L1", "PAS-L2", "PAS-L3")


def annotation_motif_model(values):
    """Retain the recorded model even when every site lacks a motif match."""
    models = {str(value).strip().lower() for value in values if value}
    if not models:
        return None
    if len(models) != 1 or not models.issubset(MOTIF_MODELS):
        raise ValueError(f"Inconsistent or unsupported species motif models: {sorted(models)}")
    return models.pop()


def _cluster_level_counts(db, species_id=None):
    query = db.query(
        APASite.species_id.label("species_id"),
        APASite.unified_id,
        func.min(APASite.pa_level).label("level"),
        func.count(func.distinct(APASite.pa_level)).label("level_count"),
    )
    if species_id is not None:
        query = query.filter(APASite.species_id == species_id)
    clusters = query.group_by(APASite.species_id, APASite.unified_id).subquery()
    rows = db.query(
        clusters.c.species_id, clusters.c.level, clusters.c.level_count, func.count()
    ).group_by(clusters.c.species_id, clusters.c.level, clusters.c.level_count).all()
    counts = defaultdict(lambda: defaultdict(int))
    for sid, level, level_count, count in rows:
        if level_count > 1:
            raise ValueError(f"Conflicting PAS levels within a unified cluster in species {sid}")
        counts[sid][level if level in PAS_LEVELS else "unassigned"] += count
    return counts


def _summary(species, sample_names, counts):
    sample_groups = {
        " ".join(name.replace("_", " ").casefold().split())
        for name in sample_names if name and name.strip()
    }
    model = species.motif_model
    assessed = model != "not_assessed" if model in MOTIF_MODELS else None
    reasons = []
    if len(sample_groups) < 2:
        reasons.append("insufficient_sample_groups")
    if assessed is False:
        reasons.append("motif_not_assessed")
    total = sum(counts.values())
    return {
        "species": species.name,
        "sample_group_count": len(sample_groups),
        "motif_model": model,
        "motif_model_label": MOTIF_MODELS.get(model, "Not recorded"),
        "motif_assessed": assessed,
        "l1_assignable": False if reasons else (True if assessed else None),
        "l1_unavailable_reasons": reasons,
        "total_clusters": total,
        "levels": [
            {
                "level": level,
                "count": counts.get(level, 0),
                "pct": round(100 * counts.get(level, 0) / total, 2) if total else 0,
            }
            for level in PAS_LEVELS
        ],
        "unassigned_count": counts.get("unassigned", 0),
    }


def build_pas_evidence_summary(db, species):
    samples = db.query(Sample.name).filter(Sample.species_id == species.id).all()
    counts = _cluster_level_counts(db, species.id)
    return _summary(species, [row.name for row in samples], counts[species.id])


def build_pas_evidence_cache(db):
    samples = defaultdict(list)
    for sid, name in db.query(Sample.species_id, Sample.name).all():
        samples[sid].append(name)
    counts = _cluster_level_counts(db)
    return {
        species.name: _summary(species, samples[species.id], counts[species.id])
        for species in db.query(Species).all()
    }
