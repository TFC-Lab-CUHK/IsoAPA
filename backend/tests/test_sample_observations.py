import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.models import database as models
from app.models.database import APASite, APASiteSample, Gene, Sample, Species, Transcript
from main import app


@contextmanager
def isolated_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = models.create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    TestingSession = models.sessionmaker(autocommit=False, autoflush=False, bind=engine)
    models.Base.metadata.create_all(bind=engine)

    original_engine = models.engine
    original_session = models.SessionLocal
    models.engine = engine
    models.SessionLocal = TestingSession

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[models.get_db] = override_db
    try:
        yield TestingSession, path
    finally:
        app.dependency_overrides.clear()
        models.SessionLocal = original_session
        models.engine = original_engine
        engine.dispose()
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def seed(session_factory, stale_sample_data=False):
    db = session_factory()
    try:
        sp = Species(name="Mouse", latin_name="Mus musculus", assembly="GRCm39")
        db.add(sp)
        db.flush()
        sample_a = Sample(name="Brain_sample", sample_type="tissue", species_id=sp.id)
        sample_b = Sample(name="ES_cell", sample_type="cell_culture", species_id=sp.id)
        db.add_all([sample_a, sample_b])
        db.flush()
        gene = Gene(
            gene_id="12231",
            gene_key="12231",
            gene_name="Brca1",
            chromosome="1",
            strand="+",
            species_id=sp.id,
        )
        db.add(gene)
        db.flush()
        tx = Transcript(transcript_id="NM_TEST.1", gene_id=gene.id, species_id=sp.id)
        db.add(tx)
        db.flush()
        import json
        legacy_details = [
            {
                "sample_name": "Fake_sample",
                "sample_type": "tissue",
                "original_site_position": 999,
                "site_count": 99,
                "site_abundance": 0.99,
            }
        ]
        site = APASite(
            unified_id="cluster_1",
            transcript_id=tx.id,
            species_id=sp.id,
            mode_site_position=102,
            transcript_biotype="mRNA",
            site_count=10,
            site_abundance=0.5,
            sample_data=json.dumps(legacy_details) if stale_sample_data else None,
            cluster_start=100,
            cluster_end=110,
            sequence="A" * 101,
            pas_motif="AATAAA",
            pas_position=-20,
            pas_type="canonical",
        )
        db.add(site)
        db.flush()
        db.add_all(
            [
                APASiteSample(
                    apa_site_id=site.id,
                    sample_id=sample_a.id,
                    sample_order=0,
                    original_site_position=101,
                    site_count=7,
                    site_abundance=0.7,
                ),
                APASiteSample(
                    apa_site_id=site.id,
                    sample_id=sample_b.id,
                    sample_order=1,
                    original_site_position=103,
                    site_count=3,
                    site_abundance=0.3,
                ),
            ]
        )
        db.commit()
        return gene.id
    finally:
        db.close()


def response_text(response):
    body = response.content
    return body.decode("utf-8") if isinstance(body, bytes) else str(body)


def test_normalized_sample_observations_drive_api_contract():
    with isolated_db() as (Session, _):
        gene_id = seed(Session)
        client = TestClient(app, base_url="http://localhost")

        gene = client.get(f"/api/v1/gene/{gene_id}?species=Mouse").json()
        locus = client.get("/api/v1/transcript/NM_TEST.1?species=Mouse").json()
        apa = response_text(client.get("/api/v1/download/apa-sites?species=Mouse&format=tsv"))
        matrix = response_text(client.get("/api/v1/download/abundance-matrix?species=Mouse"))

    assert set(gene["transcripts"][0]["samples"]) == {"Brain_sample", "ES_cell"}
    assert {sample["name"] for sample in locus["samples"]} == {"Brain_sample", "ES_cell"}
    assert "Brain sample" in apa
    assert "ES cell" in apa
    assert "Brain sample_count" in matrix
    assert "ES cell_relative_abundance" in matrix


def test_stale_sample_data_is_ignored_when_filtering_by_sample():
    with isolated_db() as (Session, _):
        seed(Session, stale_sample_data=True)
        client = TestClient(app, base_url="http://localhost")

        search = client.get("/api/v1/search?species=Mouse&sample=Fake_sample").json()
        matrix = response_text(client.get("/api/v1/download/abundance-matrix?species=Mouse&sample=Fake_sample"))

    assert search["total"] == 0
    assert matrix.strip() == "site_id\ttranscript_id\tgene_name\tchromosome\tstrand\tspecies"
