#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
bash start-components.sh hdfs hive spark kafka jupyter
kubectl -n bigdata rollout status deployment/polaris --timeout=300s
kubectl -n bigdata rollout status statefulset/seaweedfs --timeout=300s
kubectl -n bigdata exec jupyter-0 -- python /workspace/pyspark/streaming/streaming_lab.py initial
# Only the notebook pod is replaced; host files and HDFS/S3 checkpoints persist.
kubectl -n bigdata rollout restart statefulset/jupyter
kubectl -n bigdata rollout status statefulset/jupyter --timeout=300s
kubectl -n bigdata exec jupyter-0 -- python /workspace/pyspark/streaming/streaming_lab.py resume
kubectl -n bigdata exec jupyter-0 -- python /workspace/pyspark/streaming/streaming_lab.py replay
