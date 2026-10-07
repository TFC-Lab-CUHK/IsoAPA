"""Read-weighted PAS usage across all transcripts of each comparison gene."""

from collections import defaultdict

from sqlalchemy import func

from app.models.database import APASite, APASiteSample, Sample, Transcript


def pooled_gene_samples(db, gene_ids):
    rows = (
        db.query(
            Transcript.gene_id,
            APASite.unified_id,
            Sample.name,
            Sample.sample_type,
            func.sum(APASiteSample.site_count).label("read_count"),
        )
        .select_from(Transcript)
        .join(APASite, APASite.transcript_id == Transcript.id)
        .join(APASiteSample, APASiteSample.apa_site_id == APASite.id)
        .join(Sample, Sample.id == APASiteSample.sample_id)
        .filter(Transcript.gene_id.in_(gene_ids))
        .group_by(Transcript.gene_id, APASite.unified_id, Sample.id)
        .order_by(Transcript.gene_id, APASite.unified_id, Sample.id)
        .all()
    )
    observations = {}
    totals = defaultdict(int)
    for gene_id, site_id, sample_name, sample_type, read_count in rows:
        if not read_count or read_count < 0:
            continue
        name = " ".join(sample_name.replace("_", " ").split())
        key = name.casefold()
        entry = observations.setdefault((gene_id, site_id, key), {
            "name": name,
            "key": key,
            "sample_type": sample_type,
            "site_count": 0,
        })
        entry["site_count"] += int(read_count)
        totals[(gene_id, key)] += int(read_count)

    profiles = defaultdict(lambda: defaultdict(list))
    for (gene_id, site_id, key), entry in observations.items():
        total = totals[(gene_id, key)]
        profiles[gene_id][site_id].append({
            **entry,
            "total_site_count": total,
            "abundance": entry["site_count"] / total,
        })
    return profiles
