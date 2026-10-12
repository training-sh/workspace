# Initial setup execution

Validated on 12 October 2026 on Ubuntu 24.04.5 LTS, AMD64, four CPUs and approximately 16 GiB host RAM. The fresh `bigdata` Minikube profile uses four CPUs and 8192 MiB RAM. Tool versions: Minikube v1.39.0, Kubernetes/kubectl v1.35.0, Docker 29.1.3 and node containerd 2.3.4.

The previous Minikube profile and its node storage were deleted before this run. The previous source directory and shared-image tags 1.0.0, 1.1.0 and 1.1.1 were removed. Images referenced by pre-existing Compose containers and their volumes were preserved; other host applications were not reset.

The final notebook sequence emitted and executed 88 Bash blocks using `validations/run-setup.py`. Destructive reset and conditional Docker installation/admin-authentication blocks were excluded. Docker, curl, Python, certificates and Docker-group membership already existed; their reuse branches ran. Installing missing system packages and changing group membership requires interactive sudo and was not repeated on this host. All routine Docker, Minikube and kubectl commands ran without sudo.

Passed:

- Minikube and kubectl downloads, SHA-256 checksums and user-local installation.
- Workspace path saved once in `.bashrc`; local checks also covered a changed path, paths containing spaces, repeated updates and retention of other settings.
- Node readiness, CoreDNS, local storage provisioner, default storage and API permissions.
- Sequential SeaweedFS, PostgreSQL, Polaris bootstrap/server and MySQL deployment.
- Bound PVCs `seaweedfs-data` (10 GiB), `postgres-data` (5 GiB), and `mysql-data` (5 GiB).
- Authenticated S3 `test-bucket` creation/reuse, object upload, listing, read and exact content comparison.
- PostgreSQL/MySQL `test_database.test_table` creation and row read using in-pod database clients.
- Polaris token authentication, `test_catalog`, `test_namespace`, Iceberg `test_table`, and the reusable `training` catalog.
- Individual service stop/resume, grouped ordered start/reverse stop, and actual Minikube node stop/start.
- Existing SQL rows, byte-identical S3 object and the same Iceberg table UUID and metadata location after service and node restart; completed bootstrap Job retained.
- Plain ASCII notebook headings, clean notebook JSON, Bash/Python syntax and local documentation links.

Final state: the four initial services are running and their three PVCs remain Bound. Local validation forwards were closed. No Kafka, Spark, Trino, Airflow or monitoring deployment was started in this initial run. Later component paths were updated for the complete-project `/workspace` mount, but those later deployments were not revalidated here.

Raw execution logs remain in the ignored remote `.state/` directory. Source notebooks contain instructions only, with no saved execution outputs or host identifiers.
