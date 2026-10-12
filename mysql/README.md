# MySQL module

Run every command from the `workspace/` root. This module creates a new Kubernetes database; it does not import the old host/Docker Hive database. Future Hive or Airflow metadata databases will be configured in their own sessions. Polaris continues using PostgreSQL.

`mysql.yaml` contains a Secret, Service, 5 GiB persistent volume claim and one StatefulSet. The existing MySQL 8.4 image is pinned by digest and resolves to 8.4.11. Configuration uses a 256 MiB InnoDB buffer pool and a 1 GiB container memory limit for the initial lab.

| Setting | Lab value |
|---|---|
| Service / port | `mysql.bigdata.svc.cluster.local:3306` |
| Database | `training` |
| Application user / password | `team` / `team1234` |
| Root user / password | `root` / `root1234` |
| Storage | `mysql-data`, 5 GiB |

These are public, disposable course credentials. Edit `mysql-credentials` in `mysql/mysql.yaml` before first deployment to change them. MySQL initialization grants `team` access to `training.*`; root is the administrator. Root remote access is not enabled by a wildcard host grant.

## Deploy and verify

```bash
kubectl config use-context bigdata
kubectl apply -f platform/namespace.yaml
kubectl apply -f mysql/mysql.yaml
kubectl -n bigdata rollout status statefulset/mysql --timeout=600s
kubectl -n bigdata exec mysql-0 -- sh -ec \
  'MYSQL_PWD="$MYSQL_PASSWORD" mysql -h mysql -u "$MYSQL_USER" -D training -e "SELECT CURRENT_USER(), DATABASE(), VERSION();"'
kubectl -n bigdata exec mysql-0 -- sh -ec \
  'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=TCP -h 127.0.0.1 -u root -e "SELECT CURRENT_USER();"'
```

The second command uses TCP explicitly to avoid depending on the client image's default socket path. Startup/readiness probes run authenticated SQL; liveness checks the server listener through mysqladmin.

## Access

```bash
kubectl -n bigdata port-forward service/mysql 3307:3306
```

From an installed workstation MySQL client, use `mysql -h 127.0.0.1 -P 3307 -u team -p training` and enter `team1234`. For a remote host add an SSH tunnel: `ssh -N -L 3307:127.0.0.1:3307 "${LAB_SSH_USER:?Set LAB_SSH_USER}@${LAB_SSH_HOST:?Set LAB_SSH_HOST}"`. The forward must also be running on that host.

The existing optional Adminer can connect by selecting MySQL, server `mysql`, username `team`, password `team1234`, database `training`.

## Persistence and maintenance

Root `bash validations/verify-data.sh` creates/reads a sample row and verifies root access and incorrect-password rejection. `VERIFY_READ_ONLY=true bash validations/verify-data.sh` checks existing data without recreating it. Keep the PVC when replacing pods or stopping Minikube.

Editing the Secret does not rotate passwords in an initialized database. Use explicit SQL account management and then synchronize the Secret and pod environment. Initialize additional application databases and grants deliberately in their later modules.

An optional database dump, written outside the profile:

```bash
mkdir -p backups
kubectl -n bigdata exec mysql-0 -- sh -ec \
  'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump -h mysql -u "$MYSQL_USER" --single-transaction --no-tablespaces training' \
  > backups/mysql-training.sql
```

This backup command is documented for later rehearsal; pod-persistence checks are not backup/restore validation. [Official MySQL image configuration](https://hub.docker.com/_/mysql).
