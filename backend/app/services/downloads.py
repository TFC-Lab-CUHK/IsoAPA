"""Bounded-memory exports with database sessions owned by the response stream."""

import csv
import io
from itertools import groupby

import anyio
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.models.database import APASite, APASiteSample, Gene, Sample, Transcript


QUERY_BATCH_SIZE = 500
OUTPUT_CHUNK_SIZE = 64 * 1024


class DownloadResponse(StreamingResponse):
    def __init__(self, content, **kwargs):
        self.content_iterator = content
        super().__init__(content, **kwargs)

    async def close(self):
        # Also run on transport errors and request cancellation, where a
        # response background task may never execute.
        with anyio.CancelScope(shield=True):
            await run_in_threadpool(self.content_iterator.close)

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            await self.close()


def stream_query_rows(bind, statement, row_values):
    # The request's dependency session may close before the response is consumed.
    # A separate session also gives the stream an explicit cleanup boundary.
    with Session(bind=bind) as session:
        with session.execute(
            statement.execution_options(yield_per=QUERY_BATCH_SIZE)
        ) as result:
            for row in result:
                yield row_values(row)


def stream_delimited(headers, rows, delimiter):
    """Send the header immediately, then serialize at most one chunk at a time."""
    try:
        with io.StringIO(newline="") as output:
            writer = csv.writer(output, delimiter=delimiter)
            writer.writerow(headers)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

            for row in rows:
                writer.writerow(row)
                if output.tell() >= OUTPUT_CHUNK_SIZE:
                    yield output.getvalue()
                    output.seek(0)
                    output.truncate(0)
            if output.tell():
                yield output.getvalue()
    finally:
        rows.close()


def stream_bed(bind, statement):
    rows = stream_query_rows(bind, statement, lambda row: row)
    try:
        yield 'track name="IsoAPA_PA_Sites" description="IsoAPA Polyadenylation Sites" useScore=0\n'
        with io.StringIO() as output:
            for row in rows:
                position = int(row.mode_site_position or 0)
                output.write(
                    f"{row.chromosome or 'chrUnknown'}\t{max(0, position - 1)}\t"
                    f"{position}\t{row.unified_id or '.'}\t.\t{row.strand or '.'}\n"
                )
                if output.tell() >= OUTPUT_CHUNK_SIZE:
                    yield output.getvalue()
                    output.seek(0)
                    output.truncate(0)
            if output.tell():
                yield output.getvalue()
    finally:
        rows.close()


def stream_abundance_matrix(bind, species_id, species_label, selected_samples, delimiter, format_sample_name):
    with Session(bind=bind) as session:
        sample_statement = select(Sample.name).where(Sample.species_id == species_id)
        if selected_samples:
            sample_statement = sample_statement.where(Sample.name.in_(selected_samples))
        # Only the small sample catalogue is materialized to determine columns.
        names = sorted(
            set(session.scalars(sample_statement)),
            key=lambda name: (format_sample_name(name).lower(), name),
        )
        sample_columns = {}
        headers = ["site_id", "transcript_id", "gene_name", "chromosome", "strand", "species"]
        for name in names:
            display_name = format_sample_name(name)
            key = display_name.lower()
            if key and key not in sample_columns:
                sample_columns[key] = len(sample_columns) * 2
                headers.extend([f"{display_name}_count", f"{display_name}_relative_abundance"])

        statement = (
            select(
                APASite.id.label("apa_site_id"), APASite.unified_id,
                Transcript.transcript_id, Gene.gene_name, Gene.chromosome, Gene.strand,
                Sample.name.label("sample_name"), APASiteSample.site_count,
                APASiteSample.site_abundance,
            )
            .select_from(APASite)
            .join(Transcript, APASite.transcript_id == Transcript.id)
            .join(Gene, Transcript.gene_id == Gene.id)
            .outerjoin(APASiteSample, APASiteSample.apa_site_id == APASite.id)
            .outerjoin(Sample, APASiteSample.sample_id == Sample.id)
            .where(APASite.species_id == species_id)
            .order_by(APASite.id, APASiteSample.sample_order, APASiteSample.id)
        )
        if selected_samples:
            statement = statement.where(
                Sample.species_id == species_id, Sample.name.in_(selected_samples)
            )

        def matrix_rows():
            with session.execute(
                statement.execution_options(yield_per=QUERY_BATCH_SIZE)
            ) as result:
                # One site's observations are reduced at a time, including sites
                # without observations. Never retain the complete matrix.
                for _, observations in groupby(result, key=lambda row: row.apa_site_id):
                    values = [0] * (len(sample_columns) * 2)
                    for row in observations:
                        column = sample_columns.get(format_sample_name(row.sample_name).lower())
                        if column is not None:
                            values[column] += int(row.site_count or 0)
                            values[column + 1] = row.site_abundance or 0
                    yield [
                        row.unified_id or "", row.transcript_id or "", row.gene_name or "",
                        row.chromosome or "", row.strand or "", species_label,
                        *values,
                    ]

        yield from stream_delimited(headers, matrix_rows(), delimiter)
