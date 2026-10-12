# Reviewed replay and clean handoff

Validated on Ubuntu on 12 October 2026 within the requested 60-minute limit. This replay used the existing validated image; no image was rebuilt. YARN, MapReduce and Hive execution were deferred.

## Notebook and path review

- All notebook Markdown links and 78 static setup manifest/script references resolved.
- All 18 notebooks validated against the notebook schema in the retained image Python environment. Two older exercise notebooks received missing cell IDs and current format metadata. Unique cell IDs, ASCII headings and empty execution outputs passed checks. The temporary read-only validation container removed itself.
- Python/YAML parsing and documentation links passed.
- 243 shell scripts/notebook Bash blocks parsed with bash -n without warnings.
- Known personal/host identifiers and old kubes paths were absent from supported source files.
- UI forward commands now explicitly use a second terminal. The destructive reset block is clearly optional and must be skipped when continuing setup.
- Notebook 08 reuses an existing validated image. Export/import remains required for each new node. Missing-image construction stays a separate conditional branch.

## Executed replay

The exact notebook commands were extracted with:

```bash
python3 validations/run-setup.py --from-notebook 00 --to-notebook 13 \
  --skip-notebooks 10,11 --emit .state/validate-reuse-image.sh
bash .state/validate-reuse-image.sh
```

All 172 selected Bash blocks completed with exit code 0. The two separate image-build-phase blocks also passed their existing-image branches without fetching connectors or building an image. The replay script matched the final source extraction: SHA-256 3adaec244d52146b27a993f91ee6a5ec8c0ffa3899c18c5020059c56c834551d.

Passed live checks:

- Minikube, DNS/storage, metrics-server, Headlamp deployment and permissions; actual Headlamp UI HTTP access and a fresh viewer-token Kubernetes API request. No token was saved; manual browser clicks were not automated.
- Monitoring first: Prometheus/Grafana/Jaeger APIs, dashboard provisioning, trace round-trip, real logs and CPU/memory collection, plus monitoring stop/resume.
- S3 object round-trip, PostgreSQL/MySQL sample rows, Polaris catalog/namespace/Iceberg metadata, and actual first-start service logs without a log-generation restart workaround.
- Individual and grouped lifecycle checks, actual Minikube node stop/start, retained SQL/S3/Iceberg data, and the same PostgreSQL SQL log marker in Loki without repeating its query.
- Existing-image export/import, temporary archive removal, Jupyter Python/PySpark 3.5.9 and shared directories, and workbench stop/resume.
- HDFS file upload/download, native metrics, logs and retained file after restart.
- Spark distributed Python execution and HDFS Parquet write/read, native metrics and actual driver/executor log markers; the job passed again after restart.
- ZooKeeper-first Kafka startup, topic/message round-trip, separate client pod and retained message after broker/ZooKeeper restart; Kafka JVM and ZooKeeper native/JVM metrics, logs and CPU/memory passed.

Before cleanup, all 16 active application pods were healthy and all 12 PVCs were Bound. YARN/Hive workloads were absent. There were no manual configuration repairs between stages.

## Clean handoff

After successful validation, the course bigdata Minikube profile was deleted. Its node container, node volume, all Kubernetes data/PVCs and kubeconfig context were removed. Workspace mount/forward processes were stopped. Ignored .state files, the mount marker and the generated Spark smoke script were removed. Source notebooks/scripts and the configured host tools/workspace path remain available.

The prebuilt dataeng-training:1.2.0 image was preserved unchanged: sha256:e175f6f4c6315d947856abaf5f2e2b292b018210d9ae8eda97f2a879c9b24470. Other host applications and their Docker resources were not altered.

For the manual replay, begin at notebook 00, complete 00-09, then 12-13. Monitoring is notebook 02 and starts before the data services. Notebook 08 will reuse/import the retained image. Leave 10 YARN and 11 Hive for later; pause Spark/Hive/Kafka before returning to YARN on the 8 GiB profile. The longer MapReduce validation is a separate optional section at the end of notebook 10.

No course cluster or browser forwards are left running at handoff. Their URLs become available after following the notebooks again. The application replay completed at 11:50:20 UTC; subsequent health review and cleanup were verified before handoff. Airflow, Trino and lineage lesson execution were outside this replay.
