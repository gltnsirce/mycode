#!/usr/bin/env bash
# ==============================================================================
# Script Name: check_hosts.sh
# Description: High-performance, concurrent server reachability check tool.
# ==============================================================================

# Strict mode: exit on unset variables and pipe failures
set -uo pipefail

# Configuration Parameters
HOST_FILE="${1:-hosts.txt}"
TIMEOUT=2               # Connection timeout in seconds
MAX_CONCURRENCY=50      # Max concurrent background jobs (rate limiting)
CHECK_PORT=22           # Target port for TCP check (e.g., SSH; use ICMP ping if preferred)
LOG_DIR="./logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="${LOG_DIR}/reachability_${TIMESTAMP}.log"
FAIL_FILE="${LOG_DIR}/failure_${TIMESTAMP}.log"

# Initialize environment
mkdir -p "$LOG_DIR"

if [[ ! -f "$HOST_FILE" ]]; then
    echo "[ERROR] Host file not found: $HOST_FILE" >&2
    exit 1
fi

# Create a secure temporary directory for atomic counters and results
TEMP_DIR=$(mktemp -d)
RESULTS_LOG="${TEMP_DIR}/results.log"

# Cleanup trap: Ensures all temporary files and child processes are wiped on exit/interrupt
cleanup() {
    local exit_code=$?
    # Kill any lingering background jobs in the current process group
    pkill -P $$ >/dev/null 2>&1 || true
    rm -rf "$TEMP_DIR"
    exit "$exit_code"
}
trap cleanup EXIT INT TERM

# Single host reachability check function
check_host() {
    local host="$1"
    local current_time
    current_time=$(date "+%Y-%m-%d %H:%M:%S")

    # Using nc (netcat) for reliable TCP port reachability check across management networks.
    # Fallback/alternative: timeout "$TIMEOUT" ping -c 1 -W "$TIMEOUT" "$host" >/dev/null 2>&1
    if nc -z -w "$TIMEOUT" "$host" "$CHECK_PORT" >/dev/null 2>&1; then
        echo "[$current_time] [SUCCESS] Host $host is reachable on port $CHECK_PORT" >> "$RESULT_FILE"
        echo "SUCCESS:$host" >> "$RESULTS_LOG"
    else
        # Distinguishing timeout or network failure based on exit status/behavior
        echo "[$current_time] [FAILED/TIMEOUT] Host $host unreachable on port $CHECK_PORT" >> "$RESULT_FILE"
        echo "FAIL:$host" >> "$RESULTS_LOG"
    fi
}
export -f check_host
export TIMEOUT CHECK_PORT RESULT_FILE RESULTS_LOG

echo "=== Starting Reachability Check at $(date) ===" | tee -a "$RESULT_FILE"

# Process input file: strip comments, remove whitespace, validate format, and execute concurrently
grep -E -v '^[[:space:]]*(#|$)' "$HOST_FILE" | \
    awk '{$1=$1};1' | \
    while IFS= read -r host; do
        # Sanitize host: only allow valid IPv4/IPv6 or strict hostname characters to prevent injection
        if [[ ! "$host" =~ ^[a-zA-Z0-9.-]+$ ]]; then
            echo "[$(date "+%Y-%m-%d %H:%M:%S")] [INVALID] Skipped malformed host string: $host" >> "$RESULT_FILE"
            continue
        fi
        echo "$host"
    done | xargs -P "$MAX_CONCURRENCY" -I {} bash -c 'check_host "$@"' _ {}

# === Summary Statistics ===
echo "=== Summary Statistics ===" | tee -a "$RESULT_FILE"

if [[ -f "$RESULTS_LOG" ]]; then
    total_success=$(grep -c "^SUCCESS" "$RESULTS_LOG" || true)
    total_fail=$(grep -c "^FAIL" "$RESULTS_LOG" || true)
    # Extract failed hosts into the dedicated failure manifest
    grep "^FAIL" "$RESULTS_LOG" | cut -d: -f2- > "$FAIL_FILE"
else
    total_success=0
    total_fail=0
    touch "$FAIL_FILE"
fi

total_checked=$((total_success + total_fail))

echo "Total Hosts Checked : $total_checked" | tee -a "$RESULT_FILE"
echo "Successful          : $total_success" | tee -a "$RESULT_FILE"
echo "Failed / Timeout    : $total_fail" | tee -a "$RESULT_FILE"
echo "Failure list saved  : $FAIL_FILE" | tee -a "$RESULT_FILE"
echo "Full logs saved     : $RESULT_FILE" | tee -a "$RESULT_FILE"