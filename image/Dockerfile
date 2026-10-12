# One artifact, different startup roles. Component-specific JDKs and one shared Python environment.
FROM apache/hive:4.0.0@sha256:c0b241c544d341c16a6d8cafcb801a071be9b02054a5add255e9a0e826095e88 AS hive
FROM apache/spark:3.5.9-scala2.12-java11-python3-ubuntu@sha256:af02a459c8706e031c835c16f9db3c463816776e2543dd0f828af65606bcf392 AS spark
FROM apache/kafka:3.9.1@sha256:4ceccc577f03f51f6af8dbfda55194d0d892f4fa7913ffbded567ce3895622ed AS kafka
FROM trinodb/trino:476@sha256:00125e40d063bc4816d165482f6044872b18b56026fb959d3b28ce1f96ffbbee AS trino
FROM python:3.11-slim-bookworm@sha256:0a310eeecf4e1f5a0743f9a6520c90c88d089c903ca5fd283f501e3a805f5f89
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash tini curl ca-certificates procps openssh-client git unzip libxml2-utils \
    default-mysql-client postgresql-client libstdc++6 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=spark /opt/java/openjdk /opt/java/default
COPY --from=hive /opt/hadoop /opt/hadoop
COPY --from=hive /opt/hive /opt/hive
COPY --from=spark /opt/spark /opt/spark
COPY --from=kafka /opt/kafka /opt/kafka
COPY --from=trino /usr/lib/trino /opt/trino
COPY --from=trino /usr/lib/jvm /opt/java/trino-root
COPY --from=trino /usr/bin/trino /opt/trino/trino-cli.jar
COPY downloads/*.jar /opt/spark/jars/
RUN cp /opt/spark/jars/mysql-connector-j-8.4.0.jar /opt/hive/lib/
COPY requirements-notebook.txt /tmp/requirements-notebook.txt
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir 'apache-airflow[postgres]==3.3.1' \
      --constraint https://raw.githubusercontent.com/apache/airflow/constraints-3.3.1/constraints-3.11.txt && \
    /opt/venv/bin/pip install --no-cache-dir 'apache-airflow[postgres]==3.3.1' -r /tmp/requirements-notebook.txt && \
    /opt/venv/bin/pip check && \
    /opt/venv/bin/pip freeze > /opt/venv/installed.lock && \
    printf '/opt/spark/python\n/opt/spark/python/lib/py4j-0.10.9.7-src.zip\n' > /opt/venv/lib/python3.11/site-packages/spark-bundled.pth && \
    /opt/venv/bin/python -c "import pyspark; assert pyspark.__version__ == '3.5.9'; assert pyspark.__file__.startswith('/opt/spark/python/')"
RUN groupadd -g 1000 team && useradd -m -u 1000 -g 1000 -s /bin/bash team && \
    mkdir -p /data /workspace /opt/airflow /tmp/hive /opt/training && \
    chown -R team:team /data /workspace /opt/airflow /tmp/hive /opt/training
COPY --from=spark /opt/entrypoint.sh /opt/training/spark-k8s-entrypoint.sh
COPY entrypoint.sh env.sh render.py jupyter_config.py /opt/training/
COPY downloads/metrics/*.jar /opt/training/metrics/
RUN ln -sfn "$(dirname "$(dirname "$(find /opt/java/trino-root -type f -path '*/bin/java' -print -quit)")")" /opt/java/trino && \
    test -x /opt/java/trino/bin/java && \
    chmod 755 /opt/training/entrypoint.sh && \
    printf '\nsource /opt/training/env.sh\n' >> /home/team/.bashrc && \
    /opt/venv/bin/python -m ipykernel install --prefix=/opt/venv \
      --name pyspark --display-name 'Python / PySpark (Spark 3.5.9)' && \
    printf '#!/usr/bin/env bash\nexport JAVA_HOME=/opt/java/trino\nexec "$JAVA_HOME/bin/java" -jar /opt/trino/trino-cli.jar "$@"\n' >/usr/local/bin/trino && chmod 755 /usr/local/bin/trino
ENV JAVA_HOME=/opt/java/default HADOOP_HOME=/opt/hadoop HIVE_HOME=/opt/hive \
    SPARK_HOME=/opt/spark KAFKA_HOME=/opt/kafka AIRFLOW_HOME=/opt/airflow \
    HOME=/home/team USER=team LOGNAME=team
ENV PATH=/opt/venv/bin:/opt/java/default/bin:/opt/hadoop/bin:/opt/hadoop/sbin:/opt/hive/bin:/opt/spark/bin:/opt/kafka/bin:/usr/local/bin:/usr/bin:/bin
ENV HADOOP_CONF_DIR=/opt/training/conf/hadoop HIVE_CONF_DIR=/opt/training/conf/hive \
    SPARK_CONF_DIR=/opt/training/conf/spark PYSPARK_PYTHON=/opt/venv/bin/python \
    PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip
COPY downloads/lineage/*.jar /opt/spark/jars/
COPY downloads/hive-s3/*.jar /opt/hive/lib/
USER 1000:1000
WORKDIR /workspace
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/opt/training/entrypoint.sh"]
CMD ["jupyter"]
