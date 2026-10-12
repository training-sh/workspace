# OpenLineage and Marquez

For remote SSH examples, set `LAB_SSH_USER` and `LAB_SSH_HOST` in your workstation shell to your Ubuntu login and host address.

Run all commands from `workspace/`. OpenLineage 1.53.0's Scala 2.12 Spark JAR is baked into the common image, checksum-verified at build time. There is no pip PySpark or runtime Maven download. Generated Spark defaults enable the listener and send events to `http://marquez:5000/api/v1/lineage`, namespace `training`.

Marquez 0.50.0 stores lineage in the existing PostgreSQL service's dedicated `marquez` database; its web viewer proxies API requests to the internal API service. Both have one replica. PostgreSQL's existing PVC retains the lineage. OpenSearch is disabled to keep the training setup small; advanced search is unavailable. Marquez displays dataset/job lineage, while Jaeger displays traces and Grafana displays metrics.

```bash
bash start-components.sh lineage
bash lineage-access.sh
# Separate terminal:
curl -fsS http://127.0.0.1:5000/api/v1/namespaces/training/jobs
```

Browse `http://127.0.0.1:3000` and select namespace `training`, then the `person_hive_to_polaris_jdbc` jobs and their dataset graph. For a remote training machine, run this on your laptop while the forward runs on the training host:

```bash
ssh -L 3000:127.0.0.1:3000 -L 5000:127.0.0.1:5000 "${LAB_SSH_USER:?Set LAB_SSH_USER}@${LAB_SSH_HOST:?Set LAB_SSH_HOST}"
```

Pause only the viewer/collector with `bash stop-components.sh lineage`; the database remains. Spark jobs should run while the collector is available to retain their events. This collector's API has no authentication and is exposed only through localhost forwards; the SSH connection provides remote access.

Sources: [OpenLineage Spark installation](https://openlineage.io/docs/integrations/spark/installation/), [transport configuration](https://openlineage.io/docs/integrations/spark/configuration/transport/), [Marquez 0.50.0](https://github.com/MarquezProject/marquez/tree/0.50.0).

The forwarding supervisor actively checks HTTP health and reconnects after pod replacement. The Spark integration covers the person migration and both JDBC branches; native Hive SQL is not separately instrumented. Some auxiliary metadata plans can produce nonfatal integration diagnostics; the exercise checks the required graph edges explicitly.
