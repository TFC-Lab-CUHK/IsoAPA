import gzip
import os
import sys
import tempfile
import pytest
from contextlib import contextmanager
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.models import database as models
from app.models.database import (
    APASite,
    APASiteSample,
    Gene,
    OrthologRelation,
    Sample,
    Species,
    Transcript,
    TranscriptSearchIndex,
    TranscriptSearchSample,
)
from app.services.orthologs import rebuild_ortholog_relations
from app.services.search_index import rebuild_search_index
from main import app


@contextmanager
def isolated_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = models.create_engine(
        f"sqlite:///{path}", connect_args={"check_same_thread": False}
    )
    testing_session = models.sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    models.Base.metadata.create_all(bind=engine)

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[models.get_db] = override_db
    try:
        yield testing_session
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        os.remove(path)


def seed_ortholog_pair(session_factory):
    db = session_factory()
    try:
        human = Species(
            name="Human", latin_name="Homo sapiens", tax_id=9606, assembly="GRCh38"
        )
        mouse = Species(
            name="Mouse", latin_name="Mus musculus", tax_id=10090, assembly="GRCm39"
        )
        db.add_all([human, mouse])
        db.flush()
        human_gene = Gene(
            gene_id="7157",
            gene_key="7157",
            gene_name="TP53",
            chromosome="17",
            strand="-",
            species_id=human.id,
        )
        mouse_gene = Gene(
            gene_id="22059",
            gene_key="22059",
            gene_name="Trp53",
            chromosome="11",
            strand="+",
            species_id=mouse.id,
        )
        db.add_all([human_gene, mouse_gene])
        db.flush()
        human_tx = Transcript(
            transcript_id="NM_HUMAN.1", gene_id=human_gene.id, species_id=human.id
        )
        mouse_tx = Transcript(
            transcript_id="NM_MOUSE.1", gene_id=mouse_gene.id, species_id=mouse.id
        )
        db.add_all([human_tx, mouse_tx])
        db.flush()
        human_site = APASite(
            unified_id="human-site",
            transcript_id=human_tx.id,
            species_id=human.id,
            mode_site_position=100,
            cluster_start=95,
            cluster_end=105,
            pas_motif="AATAAA",
            pa_level="PAS-L1",
            site_count=20,
            site_abundance=0.7,
        )
        mouse_site = APASite(
            unified_id="mouse-site",
            transcript_id=mouse_tx.id,
            species_id=mouse.id,
            mode_site_position=200,
            cluster_start=195,
            cluster_end=205,
            pas_motif="ATTAAA",
            pa_level="PAS-L1",
            site_count=18,
            site_abundance=0.6,
        )
        db.add_all([human_site, mouse_site])
        db.flush()
        human_sample = Sample(name="Brain", sample_type="tissue", species_id=human.id)
        mouse_sample = Sample(name="brain", sample_type="tissue", species_id=mouse.id)
        db.add_all([human_sample, mouse_sample])
        db.flush()
        db.add_all(
            [
                APASiteSample(
                    apa_site_id=human_site.id,
                    sample_id=human_sample.id,
                    original_site_position=100,
                    site_count=14,
                    site_abundance=0.7,
                ),
                APASiteSample(
                    apa_site_id=mouse_site.id,
                    sample_id=mouse_sample.id,
                    original_site_position=200,
                    site_count=11,
                    site_abundance=0.6,
                ),
            ]
        )
        db.add(
            OrthologRelation(
                gene_a_id=min(human_gene.id, mouse_gene.id),
                gene_b_id=max(human_gene.id, mouse_gene.id),
            )
        )
        db.commit()
        return human_gene.id, mouse_gene.id
    finally:
        db.close()


def test_ortholog_search_listing_and_comparison_endpoints():
    with isolated_db() as session:
        human_gene_id, mouse_gene_id = seed_ortholog_pair(session)
        client = TestClient(app, base_url="http://localhost")

        search = client.get(
            "/api/v1/orthologs/search",
            params={"species": "human", "q": "TP5"},
        )
        assert search.status_code == 200
        assert search.json()[0]["gene_db_id"] == human_gene_id
        assert search.json()[0]["ortholog_species_count"] == 1

        listing = client.get(f"/api/v1/orthologs/{human_gene_id}")
        assert listing.status_code == 200
        assert listing.json()["source_gene"]["gene_name"] == "TP53"
        assert listing.json()["orthologs"][0]["gene_name"] == "Trp53"

        comparison = client.get(
            "/api/v1/orthologs/compare",
            params={"gene_ids": f"{human_gene_id},{mouse_gene_id}"},
        )
        assert comparison.status_code == 200
        payload = comparison.json()
        assert [gene["gene_name"] for gene in payload["genes"]] == ["TP53", "Trp53"]
        assert payload["sample_options"] == [
            {"value": "brain", "title": "Brain", "species_count": 2}
        ]
        assert payload["genes"][0]["transcripts"][0]["sites"][0][
            "mean_abundance"
        ] == 0.7

        unrelated = client.get(
            "/api/v1/orthologs/compare",
            params={"gene_ids": f"{human_gene_id},999999"},
        )
        assert unrelated.status_code == 400
        assert unrelated.json()["detail"] == (
            "All comparison genes must be direct orthologs of the first gene"
        )


def test_rebuild_ortholog_relations_filters_by_taxonomy_and_gene_id(tmp_path):
    with isolated_db() as session:
        human_gene_id, mouse_gene_id = seed_ortholog_pair(session)
        source = tmp_path / "gene_orthologs.gz"
        with gzip.open(source, "wt") as handle:
            handle.write(
                "#tax_id\tGeneID\trelationship\tOther_tax_id\tOther_GeneID\n"
            )
            handle.write("9606\t7157\tOrtholog\t10090\t22059\n")
            handle.write("9606\t7157\tOrtholog\t10116\t24842\n")

        db = session()
        try:
            stats = rebuild_ortholog_relations(db, source_path=source)
            relations = db.query(OrthologRelation).all()
            assert stats["relation_count"] == 1
            assert len(relations) == 1
            assert {relations[0].gene_a_id, relations[0].gene_b_id} == {
                human_gene_id,
                mouse_gene_id,
            }
        finally:
            db.close()


def test_gene_usage_pools_reads_from_all_transcripts_even_when_display_is_capped():
    with isolated_db() as session:
        human_id, mouse_id = seed_ortholog_pair(session)
        with session() as db:
            tx1 = db.query(Transcript).filter_by(gene_id=human_id).one()
            first_site = db.query(APASite).filter_by(transcript_id=tx1.id).one()
            first_obs = db.query(APASiteSample).filter_by(apa_site_id=first_site.id).one()
            first_obs.site_count, first_obs.site_abundance = 40, 0.4
            brain_id = first_obs.sample_id
            liver = Sample(name="Liver", sample_type="tissue", species_id=tx1.species_id)
            skin = Sample(name="Skin", sample_type="tissue", species_id=tx1.species_id)
            db.add_all([liver, skin])
            tx2 = Transcript(transcript_id="NM_HUMAN.2", gene_id=human_id, species_id=tx1.species_id)
            db.add(tx2)
            db.flush()
            records = []
            for tx, key, position in [(tx1, "B", 200), (tx2, "human-site", 100), (tx2, "C", 300)]:
                record = APASite(unified_id=key, transcript_id=tx.id, species_id=tx.species_id,
                                 mode_site_position=position, pa_level="PAS-L2")
                db.add(record)
                records.append(record)
            db.flush()
            site_b, shared_site, site_c = records
            for record, sample_id, count, abundance in [
                (site_b, brain_id, 60, 0.6),
                (shared_site, brain_id, 300, 0.75),
                (site_c, brain_id, 100, 0.25),
                (first_site, liver.id, 2, 0.2),
                (site_b, liver.id, 8, 0.8),
                (shared_site, liver.id, 900, 1.0),
                (site_c, skin.id, 20, 1.0),
            ]:
                db.add(APASiteSample(apa_site_id=record.id, sample_id=sample_id,
                                    original_site_position=record.mode_site_position,
                                    site_count=count, site_abundance=abundance))
            # Identical public site IDs and sample names in another species
            # must never contribute to this gene's numerator or denominator.
            mouse_tx = db.query(Transcript).filter_by(gene_id=mouse_id).one()
            db.query(APASite).filter_by(transcript_id=mouse_tx.id).one().unified_id = "human-site"
            db.commit()

        client = TestClient(app, base_url="http://localhost")
        params = {"gene_ids": f"{human_id},{mouse_id}", "max_transcripts": 1}
        response = client.get("/api/v1/orthologs/compare", params=params)
        assert response.status_code == 200
        human, mouse = response.json()["genes"]
        assert len(human["transcripts"]) == 1
        assert human["transcripts"][0]["transcript_id"] == "NM_HUMAN.1"
        assert [s["site_id"] for s in human["sites"]] == ["C", "B", "human-site"]
        by_site = {s["site_id"]: s for s in human["sites"]}
        shared = by_site["human-site"]
        samples = {s["key"]: s for s in shared["samples"]}
        assert samples["brain"]["site_count"] == 340
        assert samples["brain"]["total_site_count"] == 500
        assert samples["brain"]["abundance"] == pytest.approx(0.68)
        assert samples["liver"]["abundance"] == pytest.approx(902 / 910)
        assert shared["mean_abundance"] == pytest.approx((0.68 + 902 / 910) / 2)
        assert by_site["C"]["mean_abundance"] == pytest.approx(0.6)
        assert not any(s["key"] == "liver" for s in by_site["C"]["samples"])
        assert "skin" in {s["value"] for s in response.json()["sample_options"]}
        for key in ("brain", "liver", "skin"):
            assert sum(s["abundance"] for site in human["sites"] for s in site["samples"]
                       if s["key"] == key) == pytest.approx(1)
        tx_shared = next(s for s in human["transcripts"][0]["sites"] if s["site_id"] == "human-site")
        assert next(s["abundance"] for s in tx_shared["samples"] if s["key"] == "brain") == 0.4
        assert tx_shared["site_order"] == shared["site_order"] == 3
        assert mouse["sites"][0]["samples"][0]["abundance"] == 1
        assert mouse["sites"][0]["samples"][0]["site_count"] == 11

        full = client.get("/api/v1/orthologs/compare", params={**params, "max_transcripts": 30})
        assert full.json()["genes"][0]["sites"] == human["sites"]


def test_partial_search_refresh_updates_only_selected_species():
    with isolated_db() as session:
        human_id, mouse_id = seed_ortholog_pair(session)
        with session() as db:
            rebuild_search_index(db)
            human_tx = db.query(Transcript).filter_by(gene_id=human_id).one()
            mouse_tx = db.query(Transcript).filter_by(gene_id=mouse_id).one()
            other = db.query(TranscriptSearchIndex).filter_by(species_id=mouse_tx.species_id).one()
            other.gene_name = "Existing cached name"
            db.commit()
            before = tuple(getattr(other, c.name) for c in TranscriptSearchIndex.__table__.columns)
            sample_before = db.query(TranscriptSearchSample).filter_by(species_id=mouse_tx.species_id).one()
            before_sample = tuple(getattr(sample_before, c.name) for c in TranscriptSearchSample.__table__.columns)
            new_site = APASite(unified_id="another-site", transcript_id=human_tx.id,
                               species_id=human_tx.species_id, mode_site_position=500)
            db.add(new_site)
            db.flush()
            sample = db.query(Sample).filter_by(species_id=human_tx.species_id).one()
            db.add(APASiteSample(apa_site_id=new_site.id, sample_id=sample.id,
                                original_site_position=500, site_count=20, site_abundance=0.5))
            db.commit()
            rebuild_search_index(db, species_ids=[human_tx.species_id])
            db.expire_all()
            other = db.query(TranscriptSearchIndex).filter_by(species_id=mouse_tx.species_id).one()
            assert tuple(getattr(other, c.name) for c in TranscriptSearchIndex.__table__.columns) == before
            sample_after = db.query(TranscriptSearchSample).filter_by(species_id=mouse_tx.species_id).one()
            assert tuple(getattr(sample_after, c.name) for c in TranscriptSearchSample.__table__.columns) == before_sample
            assert db.query(TranscriptSearchIndex).filter_by(species_id=human_tx.species_id).one().apa_site_count == 2
            assert db.query(TranscriptSearchSample).filter_by(species_id=human_tx.species_id).one().apa_site_count == 2
            rebuild_search_index(db, species_ids=[])
            assert db.query(TranscriptSearchIndex).count() == 2


def test_partial_ortholog_refresh_preserves_unrelated_relations(tmp_path):
    with isolated_db() as session:
        human_id, mouse_id = seed_ortholog_pair(session)
        source = tmp_path / "orthologs.gz"
        with gzip.open(source, "wt") as handle:
            handle.write("#tax_id\tGeneID\trelationship\tOther_tax_id\tOther_GeneID\n")
            handle.write("9606\t7157\tOrtholog\t10116\t24842\n")
        with session() as db:
            human = db.query(Gene).filter_by(id=human_id).one()
            rat = Species(name="Rat", latin_name="Rattus norvegicus", tax_id=10116)
            db.add(rat)
            db.flush()
            rat_gene = Gene(gene_id="24842", gene_key="24842", gene_name="Tp53",
                            chromosome="10", strand="+", species_id=rat.id)
            db.add(rat_gene)
            db.flush()
            unrelated = OrthologRelation(gene_a_id=min(mouse_id, rat_gene.id), gene_b_id=max(mouse_id, rat_gene.id))
            db.add(unrelated)
            db.commit()
            saved_id = unrelated.id
            rebuild_ortholog_relations(db, source_path=source, species_ids=[human.species_id])
            pairs = {(row.gene_a_id, row.gene_b_id): row.id for row in db.query(OrthologRelation).all()}
            assert pairs[tuple(sorted((mouse_id, rat_gene.id)))] == saved_id
            assert tuple(sorted((human_id, rat_gene.id))) in pairs
            assert tuple(sorted((human_id, mouse_id))) not in pairs
