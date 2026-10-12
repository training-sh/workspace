#!/usr/bin/env bash
# Deploy only the MySQL and Kafka modules from the root.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
kubectl config set-context bigdata --namespace=bigdata
kubectl apply -f platform/namespace.yaml
kubectl apply -f mysql/mysql.yaml
kubectl -n bigdata rollout status statefulset/mysql --timeout=600s
kubectl apply -f kafka/zookeeper.yaml
kubectl -n bigdata rollout status statefulset/zookeeper --timeout=600s
kubectl apply -f kafka/kafka.yaml
kubectl -n bigdata rollout status statefulset/kafka --timeout=600s
kubectl -n bigdata get pods,services,pvc
