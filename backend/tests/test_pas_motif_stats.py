import os
from pathlib import Path
import sys
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes import _build_pas_motif_stats  # noqa: E402
from app.models.database import APASite, Base, Gene, Species, Transcript  # noqa: E402
from app.services import precompute_stats  # noqa: E402
from app.services.precompute_stats import (  # noqa: E402
    _build_pas_motif_cache,
    _summarize_pas_motif_rows,
)


class PASMotifStatsTests(unittest.TestCase):
    def test_primary_lineage_motifs_and_unassessed_sites_are_separated(self):
        summary = _summarize_pas_motif_rows(
            [
                ("AATAAA", "canonical", 10),
                ("AATAAA", "yeast_ee_pe", 3),
                ("AATGAA", "plant_nue", 5),
                ("TTTGTA", "plant_fue", 2),
                (None, "none", 4),
                (None, "not_assessed", 7),
            ]
        )

        self.assertEqual(summary["total"], 31)
        self.assertEqual(
            [(row["motif"], row["count"]) for row in summary["motifs"]],
            [
                ("AATAAA", 13),
                ("AATGAA", 5),
                ("TTTGTA", 2),
                ("No motif", 4),
                ("Not assessed", 7),
            ],
        )

    def test_top_ten_includes_all_assessed_types_and_keeps_special_groups(self):
        rows = [
            (f"MOTIF{count:02d}", "auxiliary", count)
            for count in range(11, 0, -1)
        ]
        rows.extend(
            [
                (None, "none", 4),
                ("IGNORED", "not_assessed", 7),
            ]
        )

        summary = _summarize_pas_motif_rows(rows)

        self.assertEqual(summary["total"], 77)
        self.assertEqual(
            [(row["motif"], row["count"]) for row in summary["motifs"]],
            [
                ("MOTIF11", 11),
                ("MOTIF10", 10),
                ("MOTIF09", 9),
                ("MOTIF08", 8),
                ("MOTIF07", 7),
                ("MOTIF06", 6),
                ("MOTIF05", 5),
                ("MOTIF04", 4),
                ("MOTIF03", 3),
                ("MOTIF02", 2),
                ("No motif", 4),
                ("Other motifs", 1),
                ("Not assessed", 7),
            ],
        )

    def test_top_ten_tie_breaking_is_independent_of_input_order(self):
        rows = [
            (f"MOTIF_{letter}", "auxiliary", 1)
            for letter in "ABCDEFGHIJK"
        ]
        expected = [(f"MOTIF_{letter}", 1) for letter in "ABCDEFGHIJ"]
        expected.append(("Other motifs", 1))

        forward = _summarize_pas_motif_rows(rows)
        reversed_order = _summarize_pas_motif_rows(list(reversed(rows)))

        self.assertEqual(
            [(row["motif"], row["count"]) for row in forward["motifs"]],
            expected,
        )
        self.assertEqual(
            [(row["motif"], row["count"]) for row in reversed_order["motifs"]],
            expected,
        )

    def test_global_stats_keep_matching_site_ids_separate_across_species(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        with Session() as db:
            first = Species(name="Species_one", latin_name="Species one")
            second = Species(name="Species_two", latin_name="Species two")
            db.add_all([first, second])
            db.flush()
            first_gene = Gene(
                gene_id="gene-1",
                gene_key="gene-1",
                gene_name="GENE1",
                chromosome="chr1",
                strand="+",
                species_id=first.id,
            )
            second_gene = Gene(
                gene_id="gene-2",
                gene_key="gene-2",
                gene_name="GENE2",
                chromosome="chr1",
                strand="+",
                species_id=second.id,
            )
            db.add_all([first_gene, second_gene])
            db.flush()
            first_tx = Transcript(
                transcript_id="tx-1", gene_id=first_gene.id, species_id=first.id
            )
            duplicate_tx = Transcript(
                transcript_id="tx-1-duplicate",
                gene_id=first_gene.id,
                species_id=first.id,
            )
            second_tx = Transcript(
                transcript_id="tx-2", gene_id=second_gene.id, species_id=second.id
            )
            db.add_all([first_tx, duplicate_tx, second_tx])
            db.flush()
            motif_sites = [
                APASite(
                    unified_id=f"motif-{letter}",
                    transcript_id=first_tx.id,
                    species_id=first.id,
                    mode_site_position=100 + offset,
                    site_count=10,
                    site_abundance=1.0,
                    pas_motif=f"MOTIF_{letter}",
                    pas_type="auxiliary",
                )
                for offset, letter in enumerate("ABCDEFGHIJK")
            ]
            db.add_all(
                motif_sites
                + [
                    # A second transcript row for the same unified site must not
                    # increase the motif count.
                    APASite(
                        unified_id="motif-A",
                        transcript_id=duplicate_tx.id,
                        species_id=first.id,
                        mode_site_position=100,
                        site_count=10,
                        site_abundance=1.0,
                        pas_motif="MOTIF_A",
                        pas_type="auxiliary",
                    ),
                    APASite(
                        unified_id="motif-A",
                        transcript_id=second_tx.id,
                        species_id=second.id,
                        mode_site_position=100,
                        site_count=10,
                        site_abundance=1.0,
                        pas_motif="ATTAAA",
                        pas_type="canonical",
                    ),
                    APASite(
                        unified_id="no-motif",
                        transcript_id=first_tx.id,
                        species_id=first.id,
                        mode_site_position=200,
                        site_count=10,
                        site_abundance=1.0,
                        pas_motif=None,
                        pas_type="none",
                    ),
                    APASite(
                        unified_id="not-assessed",
                        transcript_id=first_tx.id,
                        species_id=first.id,
                        mode_site_position=201,
                        site_count=10,
                        site_abundance=1.0,
                        pas_motif=None,
                        pas_type="not_assessed",
                    ),
                ]
            )
            db.commit()

            self.assertTrue(
                hasattr(precompute_stats, "_count_distinct_species_sites")
            )
            self.assertEqual(precompute_stats._count_distinct_species_sites(db), 14)

            expected_all = {
                "total": 14,
                "motifs": [
                    {"motif": "ATTAAA", "count": 1, "pct": 7.1},
                    *[
                        {"motif": f"MOTIF_{letter}", "count": 1, "pct": 7.1}
                        for letter in "ABCDEFGHI"
                    ],
                    {"motif": "No motif", "count": 1, "pct": 7.1},
                    {"motif": "Other motifs", "count": 2, "pct": 14.3},
                    {"motif": "Not assessed", "count": 1, "pct": 7.1},
                ],
            }
            motif_cache = _build_pas_motif_cache(db)
            live_all = _build_pas_motif_stats(db)
            live_first_species = _build_pas_motif_stats(db, "Species_one")

            self.assertEqual(live_all, expected_all)
            self.assertEqual(motif_cache["all"], live_all)
            self.assertEqual(
                motif_cache["by_species"]["Species_one"], live_first_species
            )


if __name__ == "__main__":
    unittest.main()
