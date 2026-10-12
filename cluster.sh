#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
action=${1:-status}
[[ $# -eq 0 ]] || shift
[[ $# -gt 0 ]] || set -- all
declare -A selected=()
for component in "$@"; do
  case "$component" in
    all|initial) selected[s3]=1; selected[postgres]=1; selected[polaris]=1; selected[mysql]=1 ;;
    s3|postgres|polaris|mysql) selected[$component]=1 ;;
    *) echo 'Choose: all s3 postgres polaris mysql' >&2; exit 2 ;;
  esac
done
case "$action" in start|stop|status) ;; *) echo 'Usage: bash cluster.sh start|stop|status [all|s3|postgres|polaris|mysql ...]' >&2; exit 2 ;; esac
kubectl --context=bigdata get namespace default >/dev/null
k() { kubectl --context=bigdata -n bigdata "$@"; }
if [[ "$action" == status ]]; then k get pods,services,pvc; exit; fi
if [[ "$action" == start ]]; then
  if [[ -v selected[polaris] ]]; then selected[s3]=1; selected[postgres]=1; fi
  kubectl --context=bigdata apply -f platform/namespace.yaml
  k apply -f platform/lab-secret.yaml
  for component in s3 postgres polaris mysql; do
    [[ -v selected[$component] ]] || continue
    case "$component" in
      s3) k apply -f seaweedfs/seaweedfs.yaml; k scale statefulset/seaweedfs --replicas=1; k rollout status statefulset/seaweedfs --timeout=600s ;;
      postgres) k apply -f postgresql/postgresql.yaml; k scale statefulset/postgres --replicas=1; k rollout status statefulset/postgres --timeout=600s ;;
      polaris)
        k apply -f polaris/bootstrap.yaml
        k wait --for=condition=complete job/polaris-bootstrap --timeout=600s
        k apply -f polaris/polaris.yaml
        k scale deployment/polaris --replicas=1
        k rollout status deployment/polaris --timeout=600s ;;
      mysql) k apply -f mysql/mysql.yaml; k scale statefulset/mysql --replicas=1; k rollout status statefulset/mysql --timeout=600s ;;
    esac
  done
else
  # Stop the catalog before either of its dependencies.
  if [[ -v selected[s3] || -v selected[postgres] ]]; then selected[polaris]=1; fi
  for component in mysql polaris postgres s3; do
    [[ -v selected[$component] ]] || continue
    case "$component" in s3) kind=statefulset; app=seaweedfs ;; postgres) kind=statefulset; app=postgres ;; mysql) kind=statefulset; app=mysql ;; polaris) kind=deployment; app=polaris ;; esac
    if k get "$kind/$app" >/dev/null 2>&1; then
      k scale "$kind/$app" --replicas=0
      k wait --for=delete pod -l "app=$app" --timeout=180s
    fi
  done
fi
k get pods,services,pvc
