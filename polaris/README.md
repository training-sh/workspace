# Polaris module

Run commands from `workspace/`. PostgreSQL must pass readiness and authenticated SQL verification before bootstrap. SeaweedFS must be running before catalog/S3 validation.

The Job uses `apache/polaris-admin-tool:1.7.0` and initializes realm `POLARIS` in PostgreSQL. The server uses `apache/polaris:1.7.0` and the same JDBC configuration. Bootstrap arguments resolve credentials from the Secret, rather than hardcoding a second copy in the Job. A server initContainer waits for authenticated PostgreSQL access, including working DNS, before launching Polaris. This also applies when the whole cluster resumes together.

```bash
kubectl apply -f polaris/bootstrap.yaml
kubectl -n bigdata wait --for=condition=complete job/polaris-bootstrap --timeout=600s
kubectl -n bigdata logs job/polaris-bootstrap
kubectl apply -f polaris/polaris.yaml
kubectl -n bigdata rollout status deployment/polaris --timeout=600s
kubectl -n bigdata port-forward service/polaris 8181:8181 8182:8182
```

Retain the completed Job on normal restarts. Do not infer that deleting and rerunning bootstrap rotates credentials or upgrades the schema. [Polaris 1.7.0 JDBC setup](https://polaris.apache.org/releases/1.7.0/metastores/relational-jdbc/).

In another terminal, obtain a token and list catalogs:

```bash
LAB_TOKEN=$(curl -fsS http://localhost:8181/api/catalog/v1/oauth/tokens \
  -H 'Polaris-Realm: POLARIS' \
  --data-urlencode grant_type=client_credentials \
  --data-urlencode client_id=root \
  --data-urlencode client_secret=s3cr3t \
  --data-urlencode scope=PRINCIPAL_ROLE:ALL | \
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
curl -fsS http://localhost:8181/api/management/v1/catalogs \
  -H "Authorization: Bearer $LAB_TOKEN" -H 'Polaris-Realm: POLARIS'
```

Create the training catalog once, or run root `bash validations/verify.sh`, which checks whether it exists:

```bash
curl -fsS -X POST http://localhost:8181/api/management/v1/catalogs \
  -H "Authorization: Bearer $LAB_TOKEN" -H 'Polaris-Realm: POLARIS' \
  -H 'Content-Type: application/json' --data-binary @polaris/catalog.json
```

`catalog.json` uses internal catalog `training`, warehouse `s3://warehouse/iceberg`, SeaweedFS service endpoints, path-style access and `stsUnavailable=true`. Static S3 credentials are for this lab; no temporary credential vending is promised. The exact insecure-storage property is passed through JAVA_TOOL_OPTIONS, preserving its quoted feature key. Catalog storage configuration is required separately from the server's AWS environment variables.

Polaris 1.7.0 refuses startup when the requested insecure-storage feature is enabled unless `polaris.readiness.ignore-severe-issues=true` is explicitly set. Both are passed as JVM properties for this local education configuration. This override is not a production configuration. Token signing keys are generated on server start, so obtain fresh tokens after restarting Polaris.

API port is 8181; management/health is 8182. Readiness and liveness use `/q/health/ready` and `/q/health/live`. Polaris metadata persists in PostgreSQL, so the Polaris Deployment itself needs no PVC. Use the root stop/start procedure and PostgreSQL backup instructions.
