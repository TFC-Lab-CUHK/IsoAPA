# IsoAPA

**Version:** v1.0.0

**IsoAPA** is a database of isoform-resolved alternative polyadenylation (APA) derived from long-read RNA sequencing. It identifies poly(A) sites (PASs) within annotated transcript contexts, enabling exploration of alternative 3′ ends used by transcripts with the same splicing pattern. The resource covers 99 species and provides sample-level read support and relative PAS usage.

**Access the database:** [isoapa.sls.cuhk.edu.hk](https://isoapa.sls.cuhk.edu.hk/)

## Main Features

| Feature | Description |
|---|---|
| **Search** | Find genes and transcripts, with filters for species and sample groups. |
| **Gene and Transcript Views** | Explore transcript structures, PAS locations, supporting reads and relative usage through interactive genome browsers and heatmaps. |
| **PAS Annotation** | Inspect cluster ranges, sequence context, motifs and PAS evidence levels. |
| **Cross-species Comparison** | Compare PAS profiles and usage across genes connected by curated ortholog relationships. |
| **Statistics** | Explore species coverage, PAS multiplicity, motif composition and evidence-level distributions. |

## Data Access

The [Download page](https://isoapa.sls.cuhk.edu.hk/download) provides PAS tables, genome-browser BED tracks and sample abundance matrices for a selected species. Leave the sample filter empty to include all samples in that species, or select samples to restrict the export. All dynamic exports require one exact species identifier from `/api/v1/species` (for example, `species=Human`); missing or invalid identifiers return HTTP 422. Files stream in batches. Programmatic access and versioned species archives are described in the [API reference](https://isoapa.sls.cuhk.edu.hk/api-reference).

Field definitions, usage guidance and genome annotation references are available on the [Help page](https://isoapa.sls.cuhk.edu.hk/help).

## API Resource Protection

The production NGINX configuration limits dynamic exports to two concurrent downloads per IP and four across the frontend instance; excess requests return HTTP 429. Statistics requests have a separate concurrency limit of eight. Existing request-rate limits also apply. Static release downloads share the per-IP download limit but do not occupy dynamic export slots.

Expensive statistics are cached per species for the backend process lifetime, with concurrent cache misses serialized. Species identifiers are validated before caching. Transcript multiplicity is aggregated in SQL, returning at most six bucket rows instead of loading every transcript into Python. Production requests never rebuild a missing `stats_cache.json`; generate that file offline with `python -m app.services.precompute_stats` from `backend/`. Restart the backend after replacing the database or statistics file.

The Swarm stack caps the backend at 2 CPUs and 2 GiB of memory by default. Override `ISOAPA_BACKEND_CPUS` and `ISOAPA_BACKEND_MEMORY` when deploying the stack if needed. See [incremental deployment instructions](docs/api-protection-deployment.md) to apply these changes without transferring the database or rebuilding a deployment package.

## Citation

Please cite:
Jizhou Zhang, Tsz Kwan Yau, Ting-Fung Chan, IsoAPA: a multi-species long-read RNA-seq atlas of isoform-resolved alternative polyadenylation, Nucleic Acids Research, 2026;, gkag1137, https://doi.org/10.1093/nar/gkag1137

## License

IsoAPA is distributed under the [MIT License](LICENSE).

## Contact

Ting-Fung Chan's laboratory, School of Life Sciences, The Chinese University of Hong Kong.

For questions or feedback: [tf.chan@cuhk.edu.hk](mailto:tf.chan@cuhk.edu.hk).
