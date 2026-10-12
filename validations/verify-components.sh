#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
kubectl -n bigdata rollout status statefulset/jupyter --timeout=600s
kubectl -n bigdata exec -i jupyter-0 -- bash -ec 'source /opt/training/env.sh; exec python -' < validations/check-workbench.py
mkdir -p airflow/dags
[[ -f airflow/dags/training_smoke.py ]] || cp validations/training_smoke.py airflow/dags/training_smoke.py
kubectl -n bigdata rollout status statefulset/airflow --timeout=600s
kubectl -n bigdata exec -i jupyter-0 -- python - < validations/check-airflow.py
