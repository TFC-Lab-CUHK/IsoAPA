import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.models import database as models
from app.models.database import APASite, Gene, Species, Transcript
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

    original_engine = models.engine
    original_session = models.SessionLocal
    models.engine = engine
    models.SessionLocal = testing_session

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
        models.SessionLocal = original_session
        models.engine = original_engine
        engine.dispose()
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def seed_species(session_factory, name, latin_name, gene_name, transcript_id):
    db = session_factory()
    try:
        species = Species(name=name, latin_name=latin_name)
        db.add(species)
        db.flush()
        gene = Gene(
            gene_id=f"{name}_gene",
            gene_key=f"{name}_gene",
            gene_name=gene_name,
            chromosome="1",
            strand="+",
            species_id=species.id,
        )
        db.add(gene)
        db.flush()
        transcript = Transcript(
            transcript_id=transcript_id,
            gene_id=gene.id,
            species_id=species.id,
        )
        db.add(transcript)
        db.flush()
        db.add(
            APASite(
                unified_id=f"{name}_site",
                transcript_id=transcript.id,
                species_id=species.id,
                mode_site_position=100,
                site_count=20,
                site_abundance=1.0,
            )
        )
        db.commit()
    finally:
        db.close()


def search_species(client, query):
    response = client.get("/api/v1/search", params={"species": query, "limit": 100})
    assert response.status_code == 200
    return {item["species"] for item in response.json()["items"]}


def test_species_search_accepts_database_scientific_and_common_names():
    with isolated_db() as session:
        seed_species(session, "Human", "Homo sapiens", "TP53", "NM_HUMAN.1")
        seed_species(session, "Zea_mays", "Zea mays", "Zm00001", "XM_MAIZE.1")
        client = TestClient(app, base_url="http://localhost")

        assert search_species(client, "human") == {"Human"}
        assert search_species(client, "Homo sapiens") == {"Human"}
        assert search_species(client, "maize") == {"Zea_mays"}
        assert search_species(client, "corn") == {"Zea_mays"}
        assert search_species(client, "Zea_mays") == {"Zea_mays"}


def test_species_metadata_and_autocomplete_expose_common_names():
    with isolated_db() as session:
        seed_species(session, "Human", "Homo sapiens", "TP53", "NM_HUMAN.1")
        seed_species(session, "Zea_mays", "Zea mays", "Zm00001", "XM_MAIZE.1")
        client = TestClient(app, base_url="http://localhost")

        species = {row["name"]: row for row in client.get("/api/v1/species").json()}
        assert "human" in species["Human"]["aliases"]
        assert "maize" in species["Zea_mays"]["aliases"]

        suggestions = client.get(
            "/api/v1/autocomplete",
            params={"field": "species", "q": "maize"},
        ).json()
        assert suggestions[0]["value"] == "Zea_mays"
        assert suggestions[0]["display_name"] == "Zea mays"
