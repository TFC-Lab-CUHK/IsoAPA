"""Download contracts: required scope, preserved data, and bounded streaming."""

import asyncio
import csv
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, insert, select

from test_sample_observations import isolated_db, seed
from app.api.routes import download_apa_sites, download_abundance_matrix, download_bed
from app.models.database import APASite, APASiteSample, Gene, Sample, Species, Transcript
from app.services.downloads import OUTPUT_CHUNK_SIZE, stream_delimited
from main import app


ENDPOINTS = ["apa-sites", "genes", "transcripts", "bed", "abundance-matrix"]


@pytest.fixture
def download_db():
    with isolated_db() as (factory, _):
        seed(factory)
        with factory() as db:
            mouse = db.query(Species).filter_by(name="Mouse").one()
            gene = db.query(Gene).one()
            gene.gene_name = 'Brca1,"alpha"'
            original = db.query(APASite).one()
            duplicate_sample = Sample(name="Brain sample", sample_type="tissue", species_id=mouse.id)
            db.add(duplicate_sample)
            db.flush()
            db.add(APASiteSample(
                apa_site_id=original.id, sample_id=duplicate_sample.id, sample_order=2,
                original_site_position=104, site_count=2, site_abundance=0.2,
            ))
            db.add(APASite(
                unified_id="empty_site", transcript_id=original.transcript_id,
                species_id=mouse.id, mode_site_position=200,
            ))
            tx = Transcript(transcript_id="SECOND.1", gene_id=gene.id, species_id=mouse.id)
            db.add(tx)
            db.flush()
            shared = APASite(
                unified_id="cluster_1", transcript_id=tx.id, species_id=mouse.id, mode_site_position=102,
            )
            db.add(shared)
            db.flush()
            brain = db.query(Sample).filter_by(name="Brain_sample", species_id=mouse.id).one()
            db.add(APASiteSample(
                apa_site_id=shared.id, sample_id=brain.id, sample_order=0,
                original_site_position=102, site_count=5, site_abundance=0.5,
            ))
            for name in ["Human", "Mouse_extra"]:
                species = Species(name=name, latin_name=name)
                db.add(species)
                db.flush()
                sample = Sample(name=f"{name}_only", species_id=species.id)
                gene = Gene(
                    gene_id=f"{name}_gene", gene_key=f"{name}_gene", gene_name="OTHER",
                    chromosome="chrOther", strand="-", species_id=species.id,
                )
                db.add_all([sample, gene])
                db.flush()
                transcript = Transcript(transcript_id=f"{name}_tx", gene_id=gene.id, species_id=species.id)
                db.add(transcript)
                db.flush()
                site = APASite(
                    unified_id=f"{name}_site", transcript_id=transcript.id,
                    species_id=species.id, mode_site_position=300,
                )
                db.add(site)
                db.flush()
                db.add(APASiteSample(
                    apa_site_id=site.id, sample_id=sample.id, original_site_position=300,
                    site_count=99, site_abundance=1,
                ))
            db.commit()
        yield factory


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("identifier", [None, "", " ", "Unknown", "%", "_", "Mous", "Mus musculus"])
def test_download_requires_an_exact_species(download_db, endpoint, identifier):
    params = {} if identifier is None else {"species": identifier}
    response = TestClient(app, base_url="http://localhost").get(f"/api/v1/download/{endpoint}", params=params)
    assert response.status_code == 422
    assert "attachment" not in response.headers.get("content-disposition", "")


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_download_contains_only_the_selected_species(download_db, endpoint):
    response = TestClient(app, base_url="http://localhost").get(
        f"/api/v1/download/{endpoint}", params={"species": "Mouse"},
    )
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["x-accel-buffering"] == "no"
    assert "OTHER" not in response.text
    assert "chrOther" not in response.text
    assert "Human" not in response.text
    assert "Mouse_extra" not in response.text
    if endpoint != "bed":
        assert "Mus musculus" in response.text


@pytest.mark.parametrize("format,delimiter", [("csv", ","), ("tsv", "\t"), ("txt", "\t")])
def test_pa_observation_export_keeps_quoting_and_exact_filters(download_db, format, delimiter):
    client = TestClient(app, base_url="http://localhost")
    response = client.get("/api/v1/download/apa-sites", params={
        "species": "Mouse", "sample": "ES_cell", "gene_name": "Brca1", "format": format,
    })
    rows = list(csv.DictReader(io.StringIO(response.text), delimiter=delimiter))
    assert len(rows) == 1
    assert rows[0] == {
        "gene_name": 'Brca1,"alpha"', "gene_id": "12231", "transcript_id": "NM_TEST.1",
        "site_id": "cluster_1", "cluster_range": "100:110", "representative_position": "102",
        "sample_site_position": "103", "site_abundance": "0.3", "species": "Mus musculus", "sample": "ES cell",
    }
    empty = client.get("/api/v1/download/apa-sites", params={"species": "Mouse", "sample": "Brain"})
    assert len(empty.text.splitlines()) == 1


@pytest.mark.parametrize("format,delimiter", [("csv", ","), ("tsv", "\t")])
def test_matrix_preserves_associations_zeros_and_normalized_samples(download_db, format, delimiter):
    response = TestClient(app, base_url="http://localhost").get(
        "/api/v1/download/abundance-matrix", params={"species": "Mouse", "format": format},
    )
    rows = list(csv.DictReader(io.StringIO(response.text), delimiter=delimiter))
    assert len(rows) == 3
    assert sum(row["site_id"] == "cluster_1" for row in rows) == 2
    original = next(row for row in rows if row["transcript_id"] == "NM_TEST.1" and row["site_id"] == "cluster_1")
    assert original["gene_name"] == 'Brca1,"alpha"'
    assert original["Brain sample_count"] == "9"
    assert original["Brain sample_relative_abundance"] == "0.2"
    assert original["ES cell_count"] == "3"
    assert original["ES cell_relative_abundance"] == "0.3"
    empty = next(row for row in rows if row["site_id"] == "empty_site")
    assert empty["Brain sample_count"] == empty["Brain sample_relative_abundance"] == "0"


def test_matrix_sample_selection_is_exact_and_repeatable(download_db):
    client = TestClient(app, base_url="http://localhost")
    response = client.get("/api/v1/download/abundance-matrix", params=[
        ("species", "Mouse"), ("sample", "Brain_sample"), ("sample", "ES_cell"),
    ])
    rows = list(csv.DictReader(io.StringIO(response.text), delimiter="\t"))
    assert len(rows) == 2
    # The unselected spelling variant must not add its counts to this export.
    assert rows[0]["Brain sample_count"] == "7"
    assert rows[1]["ES cell_count"] == "0"
    for sample in ["Brain", "Unknown", "Human_only"]:
        response = client.get("/api/v1/download/abundance-matrix", params={"species": "Mouse", "sample": sample})
        assert response.text.strip() == "site_id\ttranscript_id\tgene_name\tchromosome\tstrand\tspecies"


def test_bed_preserves_zero_based_coordinates(download_db):
    response = TestClient(app, base_url="http://localhost").get("/api/v1/download/bed?species=Mouse")
    assert response.text.startswith('track name="IsoAPA_PA_Sites"')
    assert "1\t101\t102\tcluster_1\t.\t+\n" in response.text
    assert "1\t199\t200\tempty_site\t.\t+\n" in response.text


def test_serializer_yields_before_materializing_the_input_and_closes_it():
    consumed = 0
    closed = False

    def rows():
        nonlocal consumed, closed
        try:
            for _ in range(10000):
                consumed += 1
                yield ["x" * 100]
        finally:
            closed = True

    content = stream_delimited(["value"], rows(), "\t")
    assert next(content) == "value\r\n"
    assert consumed == 0
    chunk = next(content)
    assert OUTPUT_CHUNK_SIZE <= len(chunk) < OUTPUT_CHUNK_SIZE + 102
    assert 0 < consumed < 1000
    content.close()
    assert closed


@pytest.mark.parametrize("endpoint", ["apa-sites", "bed", "abundance-matrix"])
@pytest.mark.parametrize("finish", [False, True, "disconnect"])
def test_stream_survives_request_session_close_and_releases_connection(download_db, endpoint, finish):
    with download_db() as db:
        species_id = db.scalar(select(Species.id).where(Species.name == "Mouse"))
        transcript_id = db.scalar(select(Transcript.id).where(Transcript.transcript_id == "NM_TEST.1"))
        sample_id = db.scalar(select(Sample.id).where(Sample.name == "ES_cell"))
        db.execute(insert(APASite), [
            {"unified_id": f"bulk_{index:05d}_" + "x" * 100, "transcript_id": transcript_id,
             "species_id": species_id, "mode_site_position": index + 1000}
            for index in range(2500)
        ])
        site_ids = db.scalars(select(APASite.id).where(APASite.mode_site_position >= 1000))
        db.execute(insert(APASiteSample), [
            {"apa_site_id": site_id, "sample_id": sample_id, "original_site_position": 1000,
             "site_count": 1, "site_abundance": 0.5}
            for site_id in site_ids
        ])
        db.commit()
        engine = db.get_bind()

    checked_out = set()

    def checkout(connection, record, proxy):
        checked_out.add(id(record))

    def checkin(connection, record):
        checked_out.remove(id(record))

    event.listen(engine, "checkout", checkout)
    event.listen(engine, "checkin", checkin)
    try:
        with download_db() as request_db:
            if endpoint == "apa-sites":
                response = download_apa_sites(species="Mouse", sample=None, gene_name=None, format="tsv", db=request_db)
            elif endpoint == "bed":
                response = download_bed(species="Mouse", db=request_db)
            else:
                response = download_abundance_matrix(species="Mouse", sample=None, format="tsv", db=request_db)
        assert not checked_out

        async def consume():
            if finish == "disconnect":
                sent_data = False

                async def receive():
                    await asyncio.Event().wait()

                async def send(message):
                    nonlocal sent_data
                    if len(message.get("body", b"")) >= OUTPUT_CHUNK_SIZE:
                        sent_data = True
                        raise OSError("Simulated disconnected download")

                with pytest.raises(Exception):
                    await response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send)
                assert sent_data
                assert not checked_out
                return
            header = await anext(response.body_iterator)
            assert "bulk_" not in header
            first_chunk = await anext(response.body_iterator)
            assert "bulk_" in first_chunk
            assert len(first_chunk) < OUTPUT_CHUNK_SIZE + 512
            assert checked_out
            if finish:
                remaining = [chunk async for chunk in response.body_iterator]
                assert remaining
                assert not checked_out
            else:
                await response.body_iterator.aclose()
            await response.close()
            assert not checked_out

        asyncio.run(consume())
    finally:
        event.remove(engine, "checkout", checkout)
        event.remove(engine, "checkin", checkin)
