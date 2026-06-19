#!/usr/bin/env bash
set -euo pipefail

export TZ="Australia/Brisbane"

BASE_DIR="/home/john/Projects/rotator"
ANCHOR_DATE="2026-06-16"   # Day 1 = EU long

DRY_RUN=false
SIM_DATE=""

# --- argument parsing ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --date)
      SIM_DATE="$2"
      DRY_RUN=true            # force dry-run when simulating
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

# --- determine date to evaluate ---
if [[ -n "$SIM_DATE" ]]; then
  eval_date="$SIM_DATE"
else
  eval_date="$(date +%F)"
fi

# --- compute Brisbane-local midnights ---
eval_midnight_s=$(date -d "$eval_date 00:00:00" +%s)
anchor_midnight_s=$(date -d "$ANCHOR_DATE 00:00:00" +%s)

eval_days=$(( eval_midnight_s / 86400 ))
anchor_days=$(( anchor_midnight_s / 86400 ))

slot=$(( (eval_days - anchor_days) % 2 ))
slot=$(( (slot + 2) % 2 ))

timestamp="$(date '+%F %T')"

# --- helper ---
run() {
  if $DRY_RUN; then
    echo "[DRY-RUN] $*"
  else
    exec "$@"
  fi
}

# --- output / execution ---
case "$slot" in
  0)
    echo "$timestamp (eval=$eval_date) Day 1 → EU long"
    run "$BASE_DIR/eu-long.sh"
    ;;
  1)
    echo "$timestamp (eval=$eval_date) Day 2 → EU short"
    run "$BASE_DIR/eu-short.sh"
    ;;
esac
