import os
from pathlib import Path
import sys
import tempfile
import unittest


os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.database import APASite  # noqa: E402
from app.schemas.schemas import APASiteBase  # noqa: E402
from app.services.etl import _load_anno_index  # noqa: E402


class PALevelContractTests(unittest.TestCase):
    def test_database_and_api_schema_use_pa_level_only(self):
        self.assertTrue(hasattr(APASite, "pa_level"))
        self.assertFalse(hasattr(APASite, "apa_level"))
        self.assertIn("pa_level", APASiteBase.model_fields)
        self.assertNotIn("apa_level", APASiteBase.model_fields)

    def test_annotation_index_reads_pa_level_without_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            annotation = Path(directory) / "Test_species_unified_apa.anno.txt"
            annotation.write_text(
                "cluster_key\tsequence\tpas_motif\tpas_position\tpas_type\t"
                "search_level\tpa_level\tcluster_start\tcluster_end\tmotif_model\n"
                "cluster-1\tAATAAA\tAATAAA\t-20\tcanonical\thexamer\t"
                "PAS-L1\t100\t105\tmammalian\n",
                encoding="utf-8",
            )

            index = _load_anno_index(directory, "Test_species")

        self.assertEqual(index["cluster-1"]["pa_level"], "PAS-L1")
        self.assertEqual(index["cluster-1"]["motif_model"], "mammalian")
        self.assertNotIn("apa_level", index["cluster-1"])

    def test_annotation_index_accepts_motif_only_annotation(self):
        with tempfile.TemporaryDirectory() as directory:
            annotation = Path(directory) / "Test_species_unified_apa.anno.txt"
            annotation.write_text(
                "cluster_key\tsequence\tpas_motif\tpas_position\tpas_type\t"
                "search_level\tcluster_start\tcluster_end\n"
                "cluster-1\tAATAAA\tAATAAA\t-20\tcanonical\thexamer\t"
                "100\t105\n",
                encoding="utf-8",
            )

            index = _load_anno_index(directory, "Test_species")

        self.assertIsNone(index["cluster-1"]["pa_level"])
        self.assertEqual(index["cluster-1"]["pas_motif"], "AATAAA")


if __name__ == "__main__":
    unittest.main()
