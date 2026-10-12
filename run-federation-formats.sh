#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
# Prepare the earlier person lesson, including a JSON SerDe shared with Trino.
bash run-person-lab.sh
bash start-components.sh trino
kubectl -n bigdata exec jupyter-0 -c jupyter -- python /workspace/pyspark/federation/formats_lab.py
