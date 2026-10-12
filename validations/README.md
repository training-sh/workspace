# Validation commands

The exact initial notebook commands can be extracted with `python3 validations/run-setup.py --emit .state/validate-setup.sh`, then run using `bash .state/validate-setup.sh`. This includes service/node stop and resume checks; destructive reset and conditional Docker installation are excluded. See [reviewed replay and clean handoff record](EXTENDED_SETUP.md); [INITIAL_SETUP.md](INITIAL_SETUP.md) preserves the earlier storage-only run.

Run these optional checks from the `workspace/` root on Ubuntu after starting the required modules. They use the existing `bigdata` context and namespace; they do not replace setup or teaching steps.

| Command | Scope and effects |
|---|---|
| `bash validations/verify.sh` | PostgreSQL, S3 and Polaris. Initializes the validation bucket/catalog/table when needed. |
| `bash validations/verify-data.sh` | MySQL accounts, sample row and Kafka message delivery. Creates validation data. |
| `bash validations/verify-components.sh` | Jupyter environment, connectors and Airflow execution. Installs the smoke-test DAG into `airflow/dags/` if absent and triggers a run. |
| `bash validations/verify-monitoring.sh` | Prometheus, Grafana and Jaeger through temporary local forwards. Writes a sample trace. |
| `bash validations/verify-telemetry.sh` | Logs, native metrics and Spark executor markers. Restarts Loki and Alloy to check persistence. |

For existing-data checks, use `VERIFY_READ_ONLY=true bash validations/verify.sh` or `VERIFY_READ_ONLY=true bash validations/verify-data.sh`. Monitoring can reuse a saved trace with `VERIFY_TRACE_ID`.

The `check-*.py`, `spark_probe.py` and `training_smoke.py` files support these commands. Pod checks are streamed over `kubectl exec -i`; they do not require mounting this folder into the workbench. Telemetry reports are written to the ignored `validations/results/results.json` path.

[Recorded deployment results](VALIDATION.md) describe earlier runs. The recorded old telemetry report path was `workspace/telemetry/results.json`; that local report has now moved to `validations/results/results.json`. Reorganizing these files does not constitute a new deployment validation.

`.ops/` preserves old operational experiments, generators and snapshots. It is excluded from Git and is not part of the setup or supported validation commands. Use the current manifests and commands above rather than rerunning old generators.


For a component lesson, extract its actual commands using, for example, `python3 validations/run-setup.py --from-notebook 09 --to-notebook 09 --emit .state/validate-hdfs.sh`, then run the emitted Bash file. For the one-time image build include `--phases main,image-build,image-import`. UI foreground commands and login-token output are excluded from automated execution; Headlamp installation/access checks and deliberate stage pauses are included by default.

`check-observability.py` verifies actual Loki records, container CPU/memory and selected native Prometheus jobs. Each notebook names only the jobs for its current stage; not-yet-started or intentionally paused modules may correctly have down targets. [Extended results](EXTENDED_SETUP.md) record the deployed versions, data examples and restart checks.

The default sequence is monitoring first (02), then storage/databases (03-06), grouped lifecycle (07), image/workbench (08) and compute (09-13). Long YARN application execution is excluded from the default phases. Run it separately with `python3 validations/run-setup.py --from-notebook 10 --to-notebook 10 --phases mapreduce --emit .state/validate-mapreduce.sh`, then `bash start-components.sh yarn`, `bash .state/validate-mapreduce.sh` and `bash stop-components.sh yarn`. Run this while Hive/Spark/Kafka are paused on the 8 GiB profile.

To validate the complete monitoring-first setup after an intentional fresh profile reset, extract notebooks 00-13 with the image build included:

```bash
python3 validations/run-setup.py --from-notebook 00 --to-notebook 13 \
  --phases main,pause,resume,persistence,ui-setup,ui-check,stage-pause,log-persistence,image-build,image-import \
  --emit .state/validate-fresh.sh
bash .state/validate-fresh.sh
```

The image build uses `--no-cache`. This command does not delete the profile and does not include interactive package installation, login-token output, foreground browser forwards or optional MapReduce execution. The setup notebooks document the separate one-time administrator steps and intentional reset command.

For a fresh cluster using an existing validated image, defer YARN/Hive and avoid rebuilding with `python3 validations/run-setup.py --from-notebook 00 --to-notebook 13 --skip-notebooks 10,11 --emit .state/validate-reuse-image.sh`. Run the emitted script. The default phases include image export/import, but exclude image construction and MapReduce.
