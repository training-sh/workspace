# Monitoring

Follow [02-monitoring.ipynb](../00-setup/02-monitoring.ipynb) for deployment, readiness, actual log/metric/trace checks and stop/resume. Use the browser inside the Guacamole Ubuntu desktop. No laptop tunnel is needed.

| UI | Local URL | Login |
|---|---|---|
| Grafana | http://127.0.0.1:3001 | team / team1234 |
| Prometheus | http://127.0.0.1:9090 | No application login in this local lab |
| Jaeger | http://127.0.0.1:16686 | No application login in this local lab |

Keep `bash monitoring-access.sh` running in a terminal on Ubuntu to provide these loopback endpoints. Grafana queries Prometheus and Loki through internal Services; the browser does not need direct access to every daemon.

Prometheus, Loki, Alloy, Grafana and Jaeger run in the existing bigdata namespace. Their PVCs are retained by `bash stop-monitoring.sh`; resume with `bash start-monitoring.sh`. The notebook lists each PVC and mount. Configuration changes require the affected pod to reload or restart, which the notebook and start helper handle explicitly.

[Telemetry coverage](TELEMETRY.md) describes collected application-file logs and the native/JVM metric endpoints. Prometheus targets for modules that are not yet started, or intentionally paused, are expected to be down. Every component lesson verifies only its own running targets. Jaeger receives traces only from explicitly instrumented workloads; it does not collect ordinary logs.

Monitoring starts immediately after Minikube, before any storage or compute services. Their first startup logs are collected without restarting them for demonstration. The grouped lifecycle notebook verifies that a PostgreSQL SQL log record survives a Minikube node restart without repeating the query.
