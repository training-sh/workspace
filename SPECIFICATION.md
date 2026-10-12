# Workspace specification

The project directory is `workspace`, copied to `~/workspace` on Ubuntu. The containing `bigdata` directory contains only this project. `WORKSPACE_HOME` selects the host project location and is recorded in `.bashrc`; root scripts resolve their own location. No account name, host address or SSH key belongs in setup instructions.

Initial sequence: host preparation ? Minikube ? namespace/configuration ? S3 ? PostgreSQL ? Polaris ? MySQL. Each setup notebook explains apply, readiness, persistent storage, a small working example, stop and resume. Polaris starts after both S3 and PostgreSQL. Group starts follow this order; group stops reverse it and retain data. `all` currently means these four initial services.

Use Ubuntu AMD64, Docker driver, containerd node runtime, one Minikube profile/context and namespace named `bigdata`. Tool versions are pinned in `versions.env`; manifests contain pinned application images. The initial node allocation is four CPUs and 8192 MiB. Later Spark/Trino sessions may need 10240 MiB on a host with enough available memory.

Keep application YAML together by module. Namespace and example credentials live in `platform/`. Ordinary restarts preserve PVCs and the completed Polaris bootstrap Job. Destructive resets delete only the explicitly selected Minikube profile and its storage. Existing unrelated host applications are outside this project.

Source layout: setup guides in `00-setup/`, interactive exercises in `notebooks/`, Python modules in `python/`, Spark jobs in `pyspark/`, SQL in `sql/trino/`, and DAGs in `airflow/dags/`. Later Jupyter/Airflow pods share the complete project at `/workspace`. DAGs additionally map to `/opt/airflow/dags`. Runtime artifacts and environments remain ignored.

Validation code and operational records belong in `validations/`. Execute notebook shell blocks on Ubuntu before recording success. Record conditional steps skipped because prerequisites already exist. Do not include execution output, personal identifiers or host addresses in notebook sources.

Notebook 01 creates Minikube and adds Headlamp/metrics-server. Notebook 02 starts monitoring before S3, PostgreSQL, Polaris and MySQL. The next stages add the shared image/workbench, HDFS, YARN, Hive, standalone Spark and ZooKeeper-backed Kafka. The 8 GiB profile uses staged lessons: pause YARN after its readiness checks; run the optional MapReduce validation separately. Centralized logs and CPU/memory collection are prerequisites for compute. Each component also verifies its native or JVM metrics and relevant application-file logs. Airflow and Trino remain later tutorials.
