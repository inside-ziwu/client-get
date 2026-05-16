#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/sync_prod_db_to_local.sh [options]

Sync the remote ClientGet PostgreSQL database into the local development database.
The current local database is backed up and kept before the final switch.

Options:
  --remote-url URL       Remote PostgreSQL URL. Overrides env/file.
  --local-url URL        Local PostgreSQL URL. Default: postgresql://postgres:postgres@localhost:5432/clientget
  --remote-db NAME       Remote database name when remote URL has no database. Default: clientget
  --local-db NAME        Local database name. Default: database name from --local-url
  --backup-dir DIR       Dump backup directory. Default: ~/.clientget/db-backups
  --dry-run              Validate settings and dependencies without dumping or switching databases.
  -h, --help             Show this help.

Remote URL resolution order:
  1. --remote-url
  2. CLIENTGET_PROD_DATABASE_URL
  3. ~/.clientget/prod-db-url

Examples:
  CLIENTGET_PROD_DATABASE_URL='postgresql://...' ./scripts/sync_prod_db_to_local.sh
  ./scripts/sync_prod_db_to_local.sh --dry-run
EOF
}

log() {
  printf '[sync-prod-db] %s\n' "$*"
}

die() {
  printf '[sync-prod-db] ERROR: %s\n' "$*" >&2
  exit 1
}

REMOTE_URL="${CLIENTGET_PROD_DATABASE_URL:-}"
LOCAL_URL="postgresql://postgres:postgres@localhost:5432/clientget"
REMOTE_DB="clientget"
LOCAL_DB=""
BACKUP_DIR="${HOME}/.clientget/db-backups"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote-url)
      [[ $# -ge 2 ]] || die "--remote-url requires a value"
      REMOTE_URL="$2"
      shift 2
      ;;
    --local-url)
      [[ $# -ge 2 ]] || die "--local-url requires a value"
      LOCAL_URL="$2"
      shift 2
      ;;
    --remote-db)
      [[ $# -ge 2 ]] || die "--remote-db requires a value"
      REMOTE_DB="$2"
      shift 2
      ;;
    --local-db)
      [[ $# -ge 2 ]] || die "--local-db requires a value"
      LOCAL_DB="$2"
      shift 2
      ;;
    --backup-dir)
      [[ $# -ge 2 ]] || die "--backup-dir requires a value"
      BACKUP_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
done

for bin in psql pg_dump pg_restore createdb dropdb; do
  command -v "$bin" >/dev/null 2>&1 || die "Missing required command: $bin"
done

if [[ -z "$REMOTE_URL" && -f "${HOME}/.clientget/prod-db-url" ]]; then
  REMOTE_URL="$(tr -d '\r\n' < "${HOME}/.clientget/prod-db-url")"
fi

[[ -n "$REMOTE_URL" ]] || die "Remote URL not configured. Set CLIENTGET_PROD_DATABASE_URL or create ~/.clientget/prod-db-url"

REMOTE_URL="${REMOTE_URL%%\?*}"
LOCAL_URL="${LOCAL_URL%%\?*}"

remote_db_from_url="$(python3 - "$REMOTE_URL" <<'PY'
from urllib.parse import urlparse
import sys

path = urlparse(sys.argv[1]).path.strip("/")
print(path)
PY
)"

if [[ -n "$remote_db_from_url" ]]; then
  REMOTE_DB="$remote_db_from_url"
else
  REMOTE_URL="${REMOTE_URL%/}/${REMOTE_DB}"
fi

local_db_from_url="$(python3 - "$LOCAL_URL" <<'PY'
from urllib.parse import urlparse
import sys

path = urlparse(sys.argv[1]).path.strip("/")
print(path)
PY
)"

local_admin_url="$(python3 - "$LOCAL_URL" <<'PY'
from urllib.parse import urlparse, urlunparse
import sys

parsed = urlparse(sys.argv[1])
print(urlunparse(parsed._replace(path="/postgres", query="", fragment="")))
PY
)"

if [[ -z "$LOCAL_DB" ]]; then
  [[ -n "$local_db_from_url" ]] || die "Local database name is missing. Pass --local-db."
  LOCAL_DB="$local_db_from_url"
fi

[[ "$LOCAL_DB" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die "Local database name must be a simple PostgreSQL identifier."

local_target_url="$(python3 - "$LOCAL_URL" "$LOCAL_DB" <<'PY'
from urllib.parse import quote, urlparse, urlunparse
import sys

parsed = urlparse(sys.argv[1])
db = quote(sys.argv[2], safe="")
print(urlunparse(parsed._replace(path=f"/{db}", query="", fragment="")))
PY
)"

if [[ "$REMOTE_URL" == *"localhost"* || "$REMOTE_URL" == *"127.0.0.1"* ]]; then
  die "Remote URL points to localhost; refusing to treat it as production."
fi

if [[ "$LOCAL_URL" != *"localhost"* && "$LOCAL_URL" != *"127.0.0.1"* ]]; then
  die "Local URL must point to localhost or 127.0.0.1."
fi

log "remote database: ${REMOTE_DB}"
log "local database: ${LOCAL_DB}"
log "backup directory: ${BACKUP_DIR}"

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "dry run passed"
  exit 0
fi

mkdir -p "$BACKUP_DIR"

timestamp="$(date +%Y%m%d-%H%M%S)"
safe_timestamp="${timestamp//-/_}"
local_backup_dump="${BACKUP_DIR}/local-${LOCAL_DB}-before-sync-${timestamp}.dump"
remote_dump="${BACKUP_DIR}/remote-${REMOTE_DB}-${timestamp}.dump"
restore_db="${LOCAL_DB}_restore_check_${safe_timestamp}"
previous_db="${LOCAL_DB}_before_sync_${safe_timestamp}"

cleanup_restore_db() {
  if [[ "${restore_db:-}" != "" ]]; then
    psql "$local_admin_url" -v ON_ERROR_STOP=1 -qAtc "drop database if exists ${restore_db};" >/dev/null 2>&1 || true
  fi
}
trap cleanup_restore_db EXIT

log "backing up current local database to ${local_backup_dump}"
pg_dump "$local_target_url" -Fc --no-owner --no-acl -f "$local_backup_dump"

log "dumping remote database to ${remote_dump}"
pg_dump "$REMOTE_URL" -Fc --no-owner --no-acl -f "$remote_dump"

log "restoring remote dump into temporary database ${restore_db}"
psql "$local_admin_url" -v ON_ERROR_STOP=1 -qAtc "create database ${restore_db};" >/dev/null
restore_url="$(python3 - "$LOCAL_URL" "$restore_db" <<'PY'
from urllib.parse import quote, urlparse, urlunparse
import sys

parsed = urlparse(sys.argv[1])
db = quote(sys.argv[2], safe="")
print(urlunparse(parsed._replace(path=f"/{db}", query="", fragment="")))
PY
)"

if ! pg_restore --dbname="$restore_url" --no-owner --no-acl "$remote_dump"; then
  log "pg_restore returned non-zero; continuing only if business table row counts match"
fi

row_count_sql="select string_agg(format('select %L as table_name, count(*)::bigint as row_count from %I.%I', table_schema || '.' || table_name, table_schema, table_name), ' union all ') from information_schema.tables where table_schema='public' and table_type='BASE TABLE' and table_name not in ('spatial_ref_sys');"
remote_count_query="$(psql "$REMOTE_URL" -v ON_ERROR_STOP=1 -Atc "$row_count_sql")"
restore_count_query="$(psql "$restore_url" -v ON_ERROR_STOP=1 -Atc "$row_count_sql")"

[[ -n "$remote_count_query" ]] || die "Remote database has no public base tables."
[[ -n "$restore_count_query" ]] || die "Temporary restored database has no public base tables."

remote_counts_file="$(mktemp)"
restore_counts_file="$(mktemp)"
psql "$REMOTE_URL" -v ON_ERROR_STOP=1 -Atc "${remote_count_query} order by table_name" | sort > "$remote_counts_file"
psql "$restore_url" -v ON_ERROR_STOP=1 -Atc "${restore_count_query} order by table_name" | sort > "$restore_counts_file"

if ! diff -u "$remote_counts_file" "$restore_counts_file"; then
  die "Remote and temporary local table row counts differ; local database was not switched."
fi

log "row counts match; switching local database"
psql "$local_admin_url" -v ON_ERROR_STOP=1 \
  -c "select pg_terminate_backend(pid) from pg_stat_activity where datname in ('${LOCAL_DB}', '${restore_db}') and pid <> pg_backend_pid();" \
  -c "alter database ${LOCAL_DB} rename to ${previous_db};" \
  -c "alter database ${restore_db} rename to ${LOCAL_DB};"

restore_db=""
trap - EXIT

log "sync complete"
log "previous local database kept as: ${previous_db}"
log "local backup dump: ${local_backup_dump}"
log "remote dump: ${remote_dump}"
