#!/usr/bin/env bash
# Requires Ubuntu curl with --aws-sigv4, python3, and the training context.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
kubectl -n bigdata wait --for=condition=Ready pod -l app=postgres --timeout=300s
kubectl -n bigdata wait --for=condition=Ready pod -l app=seaweedfs --timeout=300s
kubectl -n bigdata wait --for=condition=Ready pod -l app=polaris --timeout=300s
LAB_CHECK_DIR=$(mktemp -d)
LAB_FORWARD_PIDS=()
cleanup() {
  local status=$?
  if [[ "$status" != 0 ]]; then
    cat "$LAB_CHECK_DIR"/*forward.log >&2 2>/dev/null || true
  fi
  for pid in "${LAB_FORWARD_PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  rm -rf -- "$LAB_CHECK_DIR"
  return "$status"
}
trap cleanup EXIT
secret_value() {
  kubectl -n bigdata get secret lab-credentials -o "jsonpath={.data.$1}" | base64 -d
}
LAB_S3_ACCESS=$(secret_value s3-access-key)
LAB_S3_SECRET=$(secret_value s3-secret-key)
LAB_CLIENT_ID=$(secret_value polaris-client-id)
LAB_CLIENT_SECRET=$(secret_value polaris-client-secret)
# Dedicated check ports avoid disrupting the accounts' usual forwards.
kubectl -n bigdata port-forward service/seaweedfs 19001:8333 >"$LAB_CHECK_DIR/s3-forward.log" 2>&1 &
LAB_FORWARD_PIDS+=("$!")
kubectl -n bigdata port-forward service/polaris 18181:8181 18182:8182 >"$LAB_CHECK_DIR/polaris-forward.log" 2>&1 &
LAB_FORWARD_PIDS+=("$!")
for attempt in $(seq 1 60); do
  # A node restart may replace the selected pod sandbox after forwarding begins.
  if ! kill -0 "${LAB_FORWARD_PIDS[0]}" 2>/dev/null; then
    kubectl -n bigdata port-forward service/seaweedfs 19001:8333 >"$LAB_CHECK_DIR/s3-forward.log" 2>&1 &
    LAB_FORWARD_PIDS[0]=$!
  fi
  if ! kill -0 "${LAB_FORWARD_PIDS[1]}" 2>/dev/null; then
    kubectl -n bigdata port-forward service/polaris 18181:8181 18182:8182 >"$LAB_CHECK_DIR/polaris-forward.log" 2>&1 &
    LAB_FORWARD_PIDS[1]=$!
  fi
  if grep -q 'Forwarding from' "$LAB_CHECK_DIR/s3-forward.log" && \
     curl -fsS http://127.0.0.1:18182/q/health/ready >"$LAB_CHECK_DIR/health.json" 2>/dev/null; then break; fi
  sleep 1
done
for pid in "${LAB_FORWARD_PIDS[@]}"; do kill -0 "$pid"; done
curl -fsS http://127.0.0.1:18182/q/health/ready >/dev/null
kubectl -n bigdata exec postgres-0 -- sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" psql -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT current_database(), current_user;"'

s3() {
  curl -fsS --aws-sigv4 aws:amz:us-east-1:s3 \
    --user "$LAB_S3_ACCESS:$LAB_S3_SECRET" "$@"
}
s3 http://127.0.0.1:19001/warehouse >"$LAB_CHECK_DIR/bucket.xml"
printf 'Kubernetes training storage check\n' >"$LAB_CHECK_DIR/expected.txt"
LAB_PAYLOAD_HASH=$(sha256sum "$LAB_CHECK_DIR/expected.txt" | cut -d ' ' -f 1)
if [[ "${VERIFY_READ_ONLY:-false}" != true ]]; then
  s3 -H "x-amz-content-sha256: $LAB_PAYLOAD_HASH" \
    --upload-file "$LAB_CHECK_DIR/expected.txt" \
    http://127.0.0.1:19001/warehouse/training-check.txt
fi
s3 http://127.0.0.1:19001/warehouse/training-check.txt >"$LAB_CHECK_DIR/actual.txt"
cmp "$LAB_CHECK_DIR/expected.txt" "$LAB_CHECK_DIR/actual.txt"
LAB_BAD_STATUS=$(curl -sS -o /dev/null -w '%{http_code}' \
  --aws-sigv4 aws:amz:us-east-1:s3 --user "$LAB_S3_ACCESS:wrong-secret" \
  http://127.0.0.1:19001/warehouse)
[[ "$LAB_BAD_STATUS" == 403 ]] || { echo "S3 failed to reject bad credentials: $LAB_BAD_STATUS"; exit 1; }
echo 'PASS: existing S3 object contents match; invalid secret rejected.'

LAB_TOKEN=$(curl -fsS http://127.0.0.1:18181/api/catalog/v1/oauth/tokens \
  -H 'Polaris-Realm: POLARIS' \
  --data-urlencode grant_type=client_credentials \
  --data-urlencode "client_id=$LAB_CLIENT_ID" \
  --data-urlencode "client_secret=$LAB_CLIENT_SECRET" \
  --data-urlencode scope=PRINCIPAL_ROLE:ALL | \
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
api() {
  curl -fsS -H "Authorization: Bearer $LAB_TOKEN" \
    -H 'Polaris-Realm: POLARIS' -H 'Content-Type: application/json' "$@"
}
api http://127.0.0.1:18181/api/management/v1/catalogs >"$LAB_CHECK_DIR/catalogs.json"
# Create the training catalog only if absent; report other failures.
LAB_CATALOG_STATUS=$(curl -sS -o "$LAB_CHECK_DIR/catalog.json" -w '%{http_code}' \
  -H "Authorization: Bearer $LAB_TOKEN" -H 'Polaris-Realm: POLARIS' \
  http://127.0.0.1:18181/api/management/v1/catalogs/training)
case "$LAB_CATALOG_STATUS" in
  404) [[ "${VERIFY_READ_ONLY:-false}" != true ]] || { echo 'Missing persisted catalog'; exit 1; }
       api -X POST --data-binary @polaris/catalog.json \
         http://127.0.0.1:18181/api/management/v1/catalogs >"$LAB_CHECK_DIR/catalog.json" ;;
  200) ;;
  *) cat "$LAB_CHECK_DIR/catalog.json"; exit 1 ;;
esac
api http://127.0.0.1:18181/api/management/v1/catalogs/training >"$LAB_CHECK_DIR/catalog.json"
python3 - "$LAB_CHECK_DIR/catalog.json" <<'PY'
import json, sys
catalog = json.load(open(sys.argv[1]))
catalog = catalog.get('catalog', catalog)
expected = json.load(open('polaris/catalog.json'))['catalog']
assert catalog['name'] == expected['name']
assert catalog['properties']['default-base-location'] == expected['properties']['default-base-location']
for key, value in expected['storageConfigInfo'].items():
    assert catalog['storageConfigInfo'][key] == value, f'Catalog setting mismatch: {key}'
PY
echo 'PASS: Polaris token, management API and SeaweedFS-backed training catalog.'

# Namespace and table creation exercise Polaris writing metadata through S3FileIO.
# Read-only mode must find existing resources; it never repairs missing data.
ensure_resource() {
  local url=$1 payload=$2
  local status
  status=$(curl -sS -o "$LAB_CHECK_DIR/resource.json" -w '%{http_code}' \
    -H "Authorization: Bearer $LAB_TOKEN" -H 'Polaris-Realm: POLARIS' "$url")
  case "$status" in
    200) ;;
    404) [[ "${VERIFY_READ_ONLY:-false}" != true ]] || { echo "Missing persisted resource: $url"; exit 1; }
         api -X POST --data "$payload" "${url%/*}" >"$LAB_CHECK_DIR/resource.json" ;;
    *) cat "$LAB_CHECK_DIR/resource.json"; exit 1 ;;
  esac
}
ensure_resource http://127.0.0.1:18181/api/catalog/v1/training/namespaces/training_check \
  '{"namespace":["training_check"]}'
ensure_resource http://127.0.0.1:18181/api/catalog/v1/training/namespaces/training_check/tables/storage_check \
  '{"name":"storage_check","schema":{"type":"struct","schema-id":0,"fields":[{"id":1,"name":"id","required":true,"type":"int"}]}}'
api http://127.0.0.1:18181/api/catalog/v1/training/namespaces/training_check/tables/storage_check \
  >"$LAB_CHECK_DIR/table.json"
LAB_METADATA_KEY=$(python3 - "$LAB_CHECK_DIR/table.json" <<'PY'
import json, sys
location = json.load(open(sys.argv[1]))['metadata-location']
assert location.startswith('s3://warehouse/iceberg/')
print(location.removeprefix('s3://warehouse/'))
PY
)
s3 "http://127.0.0.1:19001/warehouse/$LAB_METADATA_KEY" >"$LAB_CHECK_DIR/metadata.json"
python3 - "$LAB_CHECK_DIR/table.json" "$LAB_CHECK_DIR/metadata.json" <<'PY'
import json, sys
table, stored = (json.load(open(p)) for p in sys.argv[1:])
assert table['metadata']['table-uuid'] == stored['table-uuid']
assert stored['schemas'][0]['fields'][0]['name'] == 'id'
print('PASS: Polaris table metadata read directly from SeaweedFS; UUID:', stored['table-uuid'])
PY
kubectl -n bigdata get pods,pvc
