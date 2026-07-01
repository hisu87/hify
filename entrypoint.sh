#!/bin/sh

LOG_LEVEL="${HIFY_LOG_LEVEL:-info}"

exec python main.py web \
    --host 0.0.0.0 \
    --port "${HIFY_PORT}" \
    --log-level "${LOG_LEVEL}"
