#!/usr/bin/env python3
import sys
import os
import json
import time


def build_index(bed12_path: str, index_path: str):
    print(f"Building BED12 index for {bed12_path} ...")
    t0 = time.time()

    index = {}
    skipped = 0

    with open(bed12_path, "rb") as f:
        while True:
            offset = f.tell()
            line_bytes = f.readline()
            if not line_bytes:
                break

            if line_bytes.startswith(b"#") or line_bytes.startswith(b"track") or line_bytes.startswith(b"browser"):
                continue

            fields = line_bytes.split(b"\t")
            if len(fields) < 12:
                skipped += 1
                continue

            tid = fields[3].decode("utf-8", errors="replace").strip()
            if not tid:
                skipped += 1
                continue

            index[tid] = [offset, len(line_bytes)]

    t1 = time.time()
    print(f"Indexed {len(index):,} transcripts in {t1 - t0:.1f}s  (skipped {skipped} malformed lines)")
    print(f"Writing index to {index_path} ...")

    with open(index_path, "w") as f:
        json.dump(index, f)

    size_mb = os.path.getsize(index_path) / 1024 / 1024
    print(f"Done. Index size: {size_mb:.1f} MB")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_bed12_index.py <path/to/annotation.junctions.bed>", file=sys.stderr)
        sys.exit(1)

    bed12 = sys.argv[1]
    if not os.path.isfile(bed12):
        print(f"Error: BED12 file not found: {bed12}", file=sys.stderr)
        sys.exit(1)

    build_index(bed12, bed12 + ".bidx")
