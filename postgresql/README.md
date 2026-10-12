# PostgreSQL module

Run commands from the `workspace/` root. Apply `platform/namespace.yaml` and `platform/lab-secret.yaml` first.

`postgresql.yaml` contains the `postgres` Service, a 5 GiB PVC and one PostgreSQL 16 StatefulSet. The image is pinned by digest. The database is `polaris`; credentials come from the shared lab Secret. PGDATA uses a subdirectory of the mounted volume.

```bash
kubectl apply -f postgresql/postgresql.yaml
kubectl -n bigdata rollout status statefulset/postgres --timeout=600s
kubectl -n bigdata exec postgres-0 -- sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" psql -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT current_database(), current_user;"'
kubectl -n bigdata port-forward service/postgres 5432:5432
```

Optional Adminer:

```bash
kubectl apply -f postgresql/adminer.yaml
kubectl -n bigdata rollout status deployment/adminer --timeout=300s
kubectl -n bigdata port-forward service/adminer 8086:8080
```

At localhost:8086 select PostgreSQL, server `postgres`, database `polaris`, user `team`, password `team1234`. Pod readiness uses pg_isready; the authenticated SQL command proves credentials and Service discovery. Changing POSTGRES_PASSWORD in the Secret does not rotate an initialized database password. `minikube stop -p bigdata` preserves storage; deleting `postgres-data` does not. Backup commands are in the root README.
