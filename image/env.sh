export JAVA_HOME=/opt/java/default
export HADOOP_HOME=/opt/hadoop HIVE_HOME=/opt/hive SPARK_HOME=/opt/spark KAFKA_HOME=/opt/kafka
export HADOOP_COMMON_HOME=$HADOOP_HOME HADOOP_HDFS_HOME=$HADOOP_HOME HADOOP_YARN_HOME=$HADOOP_HOME HADOOP_MAPRED_HOME=$HADOOP_HOME
export HADOOP_CONF_DIR=${HADOOP_CONF_DIR:-/opt/training/conf/hadoop}
export YARN_CONF_DIR=$HADOOP_CONF_DIR
export HIVE_CONF_DIR=${HIVE_CONF_DIR:-/opt/training/conf/hive}
export SPARK_CONF_DIR=${SPARK_CONF_DIR:-/opt/training/conf/spark}
export PYSPARK_PYTHON=/opt/venv/bin/python
export PYSPARK_DRIVER_PYTHON=$PYSPARK_PYTHON
export PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip
export HADOOP_LOG_DIR=/tmp/hadoop-logs YARN_LOG_DIR=/tmp/hadoop-logs HIVE_LOG_DIR=/tmp/hive-logs
export HADOOP_HEAPSIZE_MAX=${HADOOP_HEAPSIZE_MAX:-256}
export YARN_RESOURCEMANAGER_HEAPSIZE=256 YARN_NODEMANAGER_HEAPSIZE=256
export HADOOP_JOB_HISTORYSERVER_HEAPSIZE=256
export SPARK_WORKER_DIR=/data/spark-work SPARK_DAEMON_MEMORY=256m
export KAFKA_HEAP_OPTS=${KAFKA_HEAP_OPTS:--Xms256m -Xmx512m}
export LOG_DIR=${LOG_DIR:-/tmp/kafka-logs}
