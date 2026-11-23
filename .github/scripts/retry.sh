#!/usr/bin/env bash
# Retry a command with exponential backoff.
#
# Intended for the flaky network operations in CI (git clone, dnf install,
# curl downloads, micromamba/pip fetches) that have intermittently sunk whole
# matrix cells with transient errors - git "early EOF / fetch-pack" timeouts,
# dnf mirror hiccups, and GitHub "HTTP 503 Backend.max_conn reached".
#
# Usage:
#   retry.sh [-n MAX] [-d BASE_DELAY] -- CMD [ARGS...]
#
# Options (both optional; the -- before the command is also optional):
#   -n MAX          maximum attempts        (default: 5)
#   -d BASE_DELAY   seconds before retry #2  (default: 10; doubles each retry)
#
# The command runs with its given arguments; a pipeline must be wrapped in a
# `bash -c '...'` command rather than passed directly. Exits 0 on the first
# success, or with the last attempt's exit code once MAX attempts are exhausted.
set -u

max=5
delay=10
while [ $# -gt 0 ]; do
  case "$1" in
    -n) max="$2"; shift 2 ;;
    -d) delay="$2"; shift 2 ;;
    --) shift; break ;;
    *) break ;;
  esac
done

if [ $# -eq 0 ]; then
  echo "retry.sh: no command given" >&2
  exit 2
fi

attempt=1
while true; do
  "$@" && exit 0
  rc=$?
  if [ "$attempt" -ge "$max" ]; then
    echo "retry.sh: '$*' failed after ${attempt} attempt(s) (last exit ${rc})" >&2
    exit "$rc"
  fi
  echo "retry.sh: attempt ${attempt}/${max} of '$*' failed (exit ${rc}); retrying in ${delay}s" >&2
  sleep "$delay"
  attempt=$((attempt + 1))
  delay=$((delay * 2))
done
