import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from test_sample_observations import isolated_db, seed
from app.api import routes
from app.models.database import APASite, Gene, Species, Transcript
from main import app


@pytest.fixture(autouse=True)
def empty_stats_cache(monkeypatch):
    monkeypatch.setattr(routes, "_STATS_QUERY_CACHE", {})
    monkeypatch.setattr(routes, "_STATS_CACHE", None)


@pytest.mark.parametrize(
    "endpoint,builder,result",
    [
        ("multiplicity", "_build_multiplicity_stats", {"total": 1}),
        ("top-genes", "_build_top_gene_stats", [{"gene_name": "Brca1"}]),
        ("pas-motifs", "_build_pas_motif_stats", {"total": 1, "motifs": []}),
        ("pas-evidence", "build_pas_evidence_summary", {"total": 1}),
    ],
)
def test_repeated_requests_reuse_stats_and_reject_unknown_species(monkeypatch, endpoint, builder, result):
    monkeypatch.setattr(routes, "_load_stats_cache", lambda: {"detailed": {}})
    build = Mock(return_value=result)
    monkeypatch.setattr(routes, builder, build)
    with isolated_db() as (Session, _):
        seed(Session)
        with TestClient(app, base_url="http://localhost") as client:
            for _ in range(3):
                response = client.get(f"/api/v1/stats/{endpoint}", params={"species": "Mouse"})
                assert response.status_code == 200
                assert response.json() == result
            for species in ("missing-1", "missing-2", "Mou", " "):
                assert client.get(f"/api/v1/stats/{endpoint}", params={"species": species}).status_code == 404
            for species in ("", "x" * 101):
                assert client.get(f"/api/v1/stats/{endpoint}", params={"species": species}).status_code == 422
    assert build.call_count == 1
    assert len(routes._STATS_QUERY_CACHE) == 1


def test_concurrent_cache_misses_compute_once_and_cached_hits_do_not_wait():
    started = Event()
    release = Event()
    routes._cached_statistic("multiplicity", "Mouse", lambda: {"total": 1})

    def build():
        started.set()
        assert release.wait(timeout=5)
        return {"total": 2}

    build_once = Mock(side_effect=build)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(routes._cached_statistic, "multiplicity", "Human", build_once) for _ in range(6)]
        try:
            assert started.wait(timeout=5)
            # A slow new species must not hold up an already cached result.
            assert routes._cached_statistic("multiplicity", "Mouse", Mock(side_effect=AssertionError)) == {"total": 1}
        finally:
            release.set()
        assert [future.result(timeout=5) for future in futures] == [{"total": 2}] * 6
    assert build_once.call_count == 1


def test_failed_computation_can_be_retried():
    build = Mock(side_effect=[RuntimeError("temporary failure"), {"total": 1}])
    with pytest.raises(RuntimeError):
        routes._cached_statistic("multiplicity", "Mouse", build)
    assert routes._cached_statistic("multiplicity", "Mouse", build) == {"total": 1}
    assert build.call_count == 2


def test_global_and_species_stats_have_separate_cache_entries():
    with isolated_db() as (Session, _):
        seed(Session)
        with Session() as db:
            second = Species(name="Other", latin_name="Other")
            db.add(second)
            db.flush()
            gene = Gene(gene_id="other", gene_key="other", gene_name="Other", chromosome="1", strand="+", species_id=second.id)
            db.add(gene)
            db.flush()
            db.add(Transcript(transcript_id="OTHER", gene_id=gene.id, species_id=second.id))
            db.commit()
        with TestClient(app, base_url="http://localhost") as client:
            global_stats = client.get("/api/v1/stats/multiplicity").json()
            mouse_stats = client.get("/api/v1/stats/multiplicity?species=Mouse").json()
            other_stats = client.get("/api/v1/stats/multiplicity?species=Other").json()
            assert client.get("/api/v1/stats/multiplicity").json() == global_stats
    assert global_stats["total"] == 2
    assert global_stats["buckets"]["0"] == 1
    assert mouse_stats["total"] == 1
    assert mouse_stats["buckets"]["1"] == 1
    assert other_stats["total"] == 1
    assert other_stats["buckets"]["0"] == 1


def test_multiplicity_aggregation_preserves_zero_single_multi_and_distinct_sites():
    with isolated_db() as (Session, _):
        seed(Session)
        with Session() as db:
            original = db.query(Transcript).one()
            for site_count in (0, 2, 6):
                tx = Transcript(transcript_id=f"TX_{site_count}", gene_id=original.gene_id, species_id=original.species_id)
                db.add(tx)
                db.flush()
                for site_index in range(site_count):
                    # Cluster IDs are shared across transcripts of this gene.
                    db.add(APASite(unified_id=f"site_{site_index}", transcript_id=tx.id, species_id=tx.species_id, mode_site_position=200 + site_index))
            db.commit()
            result = routes._build_multiplicity_stats(db, "Mouse")
            assert routes._build_top_gene_stats(db, "Mouse")[0]["apa_count"] == 7
    assert result == {
        "buckets": {"0": 1, "1": 1, "2": 1, "3": 0, "4": 0, "5+": 1},
        "total": 4, "single_count": 1, "multi_count": 2,
        "pct_single_site": 25.0, "pct_multi_site": 50.0,
    }


def test_missing_production_cache_never_rebuilds_database_on_request(monkeypatch, tmp_path):
    monkeypatch.setattr(routes.settings, "APP_ENV", "production")
    monkeypatch.setattr(routes, "STATS_CACHE_FILE", str(tmp_path / "missing.json"))
    build = Mock(side_effect=AssertionError("Public requests must not rebuild the atlas"))
    monkeypatch.setattr(routes, "build_stats_cache", build)
    with pytest.raises(HTTPException) as error:
        routes._load_stats_cache()
    assert error.value.status_code == 503
    build.assert_not_called()


def test_precomputed_cache_is_loaded_once(monkeypatch, tmp_path):
    path = tmp_path / "stats.json"
    payload = {"basic": {"total_species": 1}, "detailed": {"total_species": 1}}
    path.write_text(json.dumps(payload))
    monkeypatch.setattr(routes, "STATS_CACHE_FILE", str(path))
    assert routes._load_stats_cache() == payload
    path.unlink()
    assert routes._load_stats_cache() == payload
