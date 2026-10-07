#!/bin/bash
# =============================================================================
#  IsoAPA – one-shot setup & launch script
#
#  Steps performed on every run:
#    1. Locate conda/mamba and create the 'isoapa' environment if needed
#    2. Activate the environment
#    3. Verify Node.js is available
#    4. Validate data files; rebuild SQLite DB + run ETL when needed
#    5. Build BED12 indices when needed
#    6. Install frontend npm deps if missing
#    7. Start the backend (uvicorn, port 8000)
#    8. Start the frontend (vite dev, port 3000)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$SCRIPT_DIR/data"
ENV_NAME="isoapa"
DB_FILE="$BACKEND_DIR/isoapa.db"
STAGED_DB_FILE="$BACKEND_DIR/isoapa.rebuild.db"
# Store hash alongside the DB so it travels with the project on the same machine
DATA_HASH_FILE="$BACKEND_DIR/.data_hash"
SCHEMA_VERSION_FILE="$BACKEND_DIR/.schema_version"
SCHEMA_VERSION="9"
STATS_CACHE_FILE="$BACKEND_DIR/stats_cache.json"
STAGED_STATS_CACHE_FILE="$BACKEND_DIR/stats_cache.rebuild.json"

# ─── helpers ──────────────────────────────────────────────────────────────────

log()  { echo ""; echo "$1"; }
info() { echo "  $1"; }
ok()   { echo "  [ok] $1"; }
warn() { echo "  [warn] $1"; }
die()  { echo ""; echo "ERROR: $1" >&2; exit 1; }

# MD5 (portable: md5sum on Linux, md5 on macOS)
md5_cmd() {
    if command -v md5sum &>/dev/null; then
        md5sum "$1" | awk '{print $1}'
    else
        md5 -q "$1"
    fi
}

# Hash all species-level APA data files. BED files are included because they
# drive the genome browser indices.
get_data_hash() {
    find "$DATA_DIR" -mindepth 2 -maxdepth 2 -type f \
        \( -name "*.txt" -o -name "*.tsv" -o -name "*.bed" \) -print0 2>/dev/null \
        | sort -z \
        | xargs -0 md5sum 2>/dev/null \
        | md5sum | awk '{print $1}' \
        || echo "none"
}

validate_data_files() {
    [[ -d "$DATA_DIR" ]] || die "Data directory not found: $DATA_DIR"

    local species_count=0
    local missing=0
    local species_dir species_name sites_count anno_count bed_count

    while IFS= read -r -d '' species_dir; do
        species_count=$((species_count + 1))
        species_name="$(basename "$species_dir")"

        sites_count="$(find "$species_dir" -maxdepth 1 -type f \
            \( -name "*_unified_apa_sites.txt" -o -name "*_unified_apa_sites.tsv" \) \
            | wc -l | tr -d ' ')"
        anno_count="$(find "$species_dir" -maxdepth 1 -type f \
            -name "*_unified_apa.anno.txt" \
            | wc -l | tr -d ' ')"
        bed_count="$(find "$species_dir" -maxdepth 1 -type f \
            -name "*.bed" \
            | wc -l | tr -d ' ')"

        if [[ "$sites_count" -lt 1 ]]; then
            warn "$species_name: missing *_unified_apa_sites.txt/tsv"
            missing=1
        elif [[ "$sites_count" -gt 1 ]]; then
            warn "$species_name: multiple unified APA site files found; ETL will use the first filesystem match"
        fi

        if [[ "$anno_count" -lt 1 ]]; then
            warn "$species_name: missing *_unified_apa.anno.txt"
            missing=1
        elif [[ "$anno_count" -gt 1 ]]; then
            warn "$species_name: multiple annotation files found; ETL will use the first filesystem match"
        fi

        if [[ "$bed_count" -lt 1 ]]; then
            warn "$species_name: missing BED file"
            missing=1
        elif [[ "$bed_count" -gt 1 ]]; then
            warn "$species_name: multiple BED files found; genome browser will use the first filesystem match"
        fi
    done < <(find "$DATA_DIR" -mindepth 1 -maxdepth 1 -type d ! -name ".*" -print0 | sort -z)

    [[ "$species_count" -gt 0 ]] || die "No species folders found under $DATA_DIR"
    [[ "$missing" -eq 0 ]] || die "Required data files are missing; fix data/ before rebuilding"

    ok "Validated $species_count species folders"
}

should_reload_db() {
    [[ ! -s "$DB_FILE" ]] && return 0
    [[ ! -f "$SCHEMA_VERSION_FILE" ]] && return 0
    [[ "$(cat "$SCHEMA_VERSION_FILE")" != "$SCHEMA_VERSION" ]] && return 0
    [[ ! -f "$DATA_HASH_FILE" ]] && return 0
    local current stored
    current=$(get_data_hash)
    stored=$(cat "$DATA_HASH_FILE")
    [[ "$current" != "$stored" ]] && return 0
    return 1
}

# ─── step 1 : conda / mamba environment ──────────────────────────────────────

log "=========================================="
log "  IsoAPA – setup & launch"
log "=========================================="

log "[1/8] Conda environment"

# Locate mamba or conda (prefer mamba)
CONDA_EXE=""
for candidate in mamba conda; do
    if command -v "$candidate" &>/dev/null; then
        CONDA_EXE="$candidate"
        break
    fi
done

# If neither is on PATH try the most common install locations
if [[ -z "$CONDA_EXE" ]]; then
    for base in \
        "$HOME/Tools/Miniforge3" \
        "$HOME/miniforge3" \
        "$HOME/mambaforge" \
        "$HOME/miniconda3" \
        "$HOME/anaconda3" \
        "/opt/conda" \
        "/opt/homebrew/Caskroom/mambaforge/base"
    do
        for candidate in mamba conda; do
            if [[ -x "$base/bin/$candidate" ]]; then
                CONDA_EXE="$base/bin/$candidate"
                CONDA_BASE="$base"
                break 2
            fi
        done
    done
fi

[[ -z "$CONDA_EXE" ]] && die "conda/mamba not found. Install Miniforge3 from https://github.com/conda-forge/miniforge and re-run."

info "Using: $CONDA_EXE"

# Derive base prefix so we can source activate
if [[ -z "${CONDA_BASE:-}" ]]; then
    CONDA_BASE="$("$CONDA_EXE" info --base 2>/dev/null || true)"
fi

# Activate helper: source the conda shell functions then activate
activate_env() {
    local init_script=""
    for candidate in \
        "$CONDA_BASE/etc/profile.d/conda.sh" \
        "$CONDA_BASE/etc/profile.d/mamba.sh"
    do
        if [[ -f "$candidate" ]]; then
            init_script="$candidate"
            break
        fi
    done

    if [[ -n "$init_script" ]]; then
        # shellcheck disable=SC1090
        source "$init_script"
        conda activate "$ENV_NAME" 2>/dev/null || true
    else
        # Fallback: prepend env bin to PATH directly
        local env_bin
        env_bin="$("$CONDA_EXE" run -n "$ENV_NAME" python -c 'import sys,os; print(os.path.dirname(sys.executable))' 2>/dev/null || true)"
        if [[ -n "$env_bin" ]]; then
            export PATH="$env_bin:$PATH"
        fi
    fi
}

# Create environment if it doesn't exist
if "$CONDA_EXE" env list 2>/dev/null | grep -qE "(^|\s)${ENV_NAME}(\s|$)"; then
    ok "Environment '$ENV_NAME' already exists"
else
    info "Creating environment '$ENV_NAME' from $BACKEND_DIR/environment.yml ..."
    "$CONDA_EXE" env create -f "$BACKEND_DIR/environment.yml" \
        || die "Failed to create conda environment"
    ok "Environment created"
fi

# ─── step 2 : activate ────────────────────────────────────────────────────────

log "[2/8] Activating environment"
activate_env

# Resolve python inside the environment (robust even if activate did nothing)
PYTHON="$("$CONDA_EXE" run -n "$ENV_NAME" which python 2>/dev/null \
          || command -v python3 \
          || die "python not found")"
info "Python: $PYTHON ($($PYTHON --version 2>&1))"

# ─── step 3 : node.js ─────────────────────────────────────────────────────────

log "[3/8] Checking Node.js"
if ! command -v node &>/dev/null; then
    die "node not found. Install Node.js (https://nodejs.org) and re-run."
fi
ok "Node $(node --version) / npm $(npm --version)"

# ─── step 4 : database / ETL ─────────────────────────────────────────────────

log "[4/8] Database & ETL"

validate_data_files
info "Validating tabular schemas and cluster annotations ..."
"$PYTHON" "$SCRIPT_DIR/scripts/data_processing/validate_database_inputs.py" "$DATA_DIR" \
    || die "Input validation failed; database was not changed"
ok "Input schemas and annotation coverage validated"

if should_reload_db; then
    info "Data change detected (or DB missing) — rebuilding database for all species ..."
    rm -f "$STAGED_DB_FILE" "${STAGED_DB_FILE}-shm" "${STAGED_DB_FILE}-wal" \
        "$STAGED_STATS_CACHE_FILE"
    info "Running ETL pipeline ..."
    (cd "$BACKEND_DIR" && \
        DATABASE_URL="sqlite:///$STAGED_DB_FILE" "$PYTHON" -m app.services.etl) \
        || die "ETL failed; active database was not changed"
    [[ -s "$STAGED_DB_FILE" ]] \
        || die "ETL produced an empty staged database; active database was not changed"
    info "Importing NCBI Gene ortholog relationships ..."
    "$PYTHON" "$SCRIPT_DIR/scripts/data_processing/import_gene_orthologs.py" \
        --database "$STAGED_DB_FILE" \
        || die "Ortholog import failed; active database was not changed"
    info "Precomputing statistics cache ..."
    (cd "$BACKEND_DIR" && \
        DATABASE_URL="sqlite:///$STAGED_DB_FILE" "$PYTHON" -c \
        'from app.services.precompute_stats import build_stats_cache; import sys; build_stats_cache(sys.argv[1])' \
        "$STAGED_STATS_CACHE_FILE") \
        || die "Statistics cache generation failed; active database was not changed"
    info "Checking staged database integrity ..."
    "$PYTHON" -c \
        'import sqlite3, sys; db = sqlite3.connect(sys.argv[1]); result = db.execute("PRAGMA quick_check").fetchone()[0]; db.close(); print(result); raise SystemExit(0 if result == "ok" else 1)' \
        "$STAGED_DB_FILE" \
        || die "Staged database integrity check failed; active database was not changed"
    mv -f "$STAGED_DB_FILE" "$DB_FILE"
    mv -f "$STAGED_STATS_CACHE_FILE" "$STATS_CACHE_FILE"
    get_data_hash > "$DATA_HASH_FILE"
    echo "$SCHEMA_VERSION" > "$SCHEMA_VERSION_FILE"
    ok "Database ready"
else
    ok "No data changes — using existing database"
fi

if [[ ! -f "$STATS_CACHE_FILE" ]]; then
    info "Statistics cache missing — generating ..."
    (cd "$BACKEND_DIR" && "$PYTHON" -m app.services.precompute_stats) \
        || die "Statistics cache generation failed"
    ok "Statistics cache ready"
else
    ok "Statistics cache present"
fi

# ─── step 5 : BED12 indices ──────────────────────────────────────────────────

log "[5/8] BED12 indices"

_bed12_any_built=0
while IFS= read -r -d '' _bed; do
    if [[ ! -f "${_bed}.bidx" ]]; then
        info "Building BED12 index: $(basename "$(dirname "$_bed")")/$(basename "$_bed") ..."
        "$PYTHON" "$BACKEND_DIR/build_bed12_index.py" "$_bed" \
            || warn "Failed to build index for $_bed"
        _bed12_any_built=1
    fi
done < <(find "$DATA_DIR" -mindepth 2 -maxdepth 2 -type f -name "*.bed" -print0 | sort -z)
if [[ "$_bed12_any_built" -eq 0 ]]; then
    ok "All BED12 indices present"
else
    ok "BED12 index build complete"
fi

# ─── step 6 : frontend dependencies ──────────────────────────────────────────

log "[6/8] Frontend dependencies"

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    info "Installing npm packages (first run) ..."
    (cd "$FRONTEND_DIR" && npm install) \
        || die "npm install failed"
    ok "npm packages installed"
else
    ok "node_modules present"
fi

# ─── step 6 : start backend ───────────────────────────────────────────────────

log "[7/8] Starting backend (port 8000)"

(cd "$BACKEND_DIR" && "$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!
info "PID $BACKEND_PID"

# Wait briefly and confirm the process is still alive
sleep 2
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    die "Backend failed to start. Check the output above for errors."
fi
ok "Backend running"

# ─── step 7 : start frontend ──────────────────────────────────────────────────

log "[8/8] Starting frontend (port 3000)"

(cd "$FRONTEND_DIR" && npm run dev) &
FRONTEND_PID=$!
info "PID $FRONTEND_PID"

sleep 3
if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null
    die "Frontend failed to start. Check the output above for errors."
fi
ok "Frontend running"

# ─── ready ────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo "  IsoAPA is running!"
echo "=========================================="
echo ""
echo "  Backend API : http://localhost:8000"
echo "  Frontend    : http://localhost:3000"
echo "  API docs    : http://localhost:8000/docs"
echo ""
echo "  Press Ctrl+C to stop"
echo ""

# Save PIDs for the trap
echo "$BACKEND_PID"  > /tmp/isoapa_backend.pid
echo "$FRONTEND_PID" > /tmp/isoapa_frontend.pid

cleanup() {
    echo ""
    echo "Stopping servers ..."
    kill "$(cat /tmp/isoapa_backend.pid 2>/dev/null)"  2>/dev/null || true
    kill "$(cat /tmp/isoapa_frontend.pid 2>/dev/null)" 2>/dev/null || true
    rm -f /tmp/isoapa_backend.pid /tmp/isoapa_frontend.pid
    conda deactivate 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

wait
