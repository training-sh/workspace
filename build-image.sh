#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
python3 image/fetch.py
docker build -t "${TRAINING_IMAGE:-dataeng-training:1.2.0}" image/
# Stream the large artifact rather than buffering it in Minikube's loader.
# This course profile uses the Docker driver and containerd runtime.
mkdir -p .state
docker save -o .state/training-image.tar "${TRAINING_IMAGE:-dataeng-training:1.2.0}"
docker exec -i bigdata ctr --namespace k8s.io images import - < .state/training-image.tar
rm .state/training-image.tar
