import os
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api import routes
from app.models.database import APASite, Base, Gene, Sample, Species, Transcript
from app.services.pas_evidence_stats import (
    annotation_motif_model,
    build_pas_evidence_cache,
    build_pas_evidence_summary,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()


def add_species(db, name, model, samples, levels):
    species = Species(name=name, latin_name=name, motif_model=model)
    db.add(species)
    db.flush()
    db.add_all(Sample(name=name, species_id=species.id) for name in samples)
    gene = Gene(gene_id=name, gene_key=name, gene_name=name, species_id=species.id,
                chromosome="1", strand="+")
    db.add(gene)
    db.flush()
    # A site shared by two transcripts must still contribute just one cluster.
    for number in (1, 2):
        transcript = Transcript(transcript_id=f"{name}-{number}", species_id=species.id, gene_id=gene.id)
        db.add(transcript)
        db.flush()
        db.add_all(
            APASite(species_id=species.id, transcript_id=transcript.id,
                    unified_id=f"cluster-{i}", mode_site_position=100 + i,
                    pa_level=level, pas_type="none")
            for i, level in enumerate(levels)
        )
    db.commit()
    return species


def test_counts_deduplicate_clusters_and_sample_labels_and_keep_species_separate(db):
    human = add_species(db, "Human", "mammalian", ["Brain", "brain", "Liver"],
                        ["PAS-L1", "PAS-L2", "PAS-L3", "PAS-L3"])
    mouse = add_species(db, "Mouse", "mammalian", ["Brain", "Liver"], ["PAS-L2"])
    result = build_pas_evidence_summary(db, human)
    assert result["total_clusters"] == 4
    assert result["sample_group_count"] == 2
    assert [(row["count"], row["pct"]) for row in result["levels"]] == [(1, 25), (1, 25), (2, 50)]
    assert result["l1_assignable"] is True
    assert result["l1_unavailable_reasons"] == []
    cache = build_pas_evidence_cache(db)
    assert cache["Human"] == result
    assert cache["Mouse"] == build_pas_evidence_summary(db, mouse)
    assert cache["Mouse"]["total_clusters"] == 1


@pytest.mark.parametrize("model,samples,reasons", [
    ("mammalian", ["Brain"], ["insufficient_sample_groups"]),
    ("not_assessed", ["Brain", "Liver"], ["motif_not_assessed"]),
    ("not_assessed", ["Brain"], ["insufficient_sample_groups", "motif_not_assessed"]),
])
def test_l1_restrictions_report_each_missing_requirement(db, model, samples, reasons):
    species = add_species(db, "Test", model, samples, ["PAS-L3"])
    result = build_pas_evidence_summary(db, species)
    assert result["l1_assignable"] is False
    assert result["l1_unavailable_reasons"] == reasons


def test_no_motif_match_does_not_mean_model_was_unassessed(db):
    species = add_species(db, "Plant", "land_plant", ["leaf", "root"], ["PAS-L2"])
    result = build_pas_evidence_summary(db, species)
    assert result["motif_assessed"] is True
    assert result["motif_model_label"] == "Land plant"
    assert result["l1_assignable"] is True
    assert result["levels"][0]["count"] == 0


def test_missing_metadata_and_levels_are_not_invented(db):
    species = add_species(db, "Unknown", None, ["A", "B"], [None])
    result = build_pas_evidence_summary(db, species)
    assert result["motif_assessed"] is None
    assert result["l1_assignable"] is None
    assert result["total_clusters"] == 1
    assert result["unassigned_count"] == 1
    assert sum(level["count"] for level in result["levels"]) == 0


def test_conflicting_cluster_labels_fail_instead_of_double_counting(db):
    species = add_species(db, "Conflicting", "mammalian", ["A", "B"], ["PAS-L1"])
    db.query(APASite).first().pa_level = "PAS-L2"
    db.flush()
    with pytest.raises(ValueError, match="Conflicting PAS levels"):
        build_pas_evidence_summary(db, species)


def test_endpoint_uses_same_summary_for_cached_and_live_results(db, monkeypatch):
    species = add_species(db, "Human", "mammalian", ["Brain", "Liver"], ["PAS-L1"])
    monkeypatch.setattr(routes, "_load_stats_cache", lambda: {"detailed": {}})
    live = routes.get_pas_evidence_stats("Human", db)
    expected = build_pas_evidence_summary(db, species)
    assert live == expected
    monkeypatch.setattr(routes, "_load_stats_cache", lambda: {
        "detailed": {"pas_evidence_by_species": {"Human": expected}}
    })
    monkeypatch.setattr(routes, "build_pas_evidence_summary", lambda *args: pytest.fail("Should use cache"))
    assert routes.get_pas_evidence_stats("Human", db) == expected
    with pytest.raises(routes.HTTPException) as exc:
        routes.get_pas_evidence_stats("Missing", db)
    assert exc.value.status_code == 404


def test_annotation_model_validation():
    assert annotation_motif_model(["land_plant", "LAND_PLANT"]) == "land_plant"
    assert annotation_motif_model([None]) is None
    with pytest.raises(ValueError):
        annotation_motif_model(["mammalian", "land_plant"])
    with pytest.raises(ValueError):
        annotation_motif_model(["invented_model"])
