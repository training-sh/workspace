# Apache Spark Setup

```

cd /tmp

wget -O spark-3.5.9-bin-hadoop3.tgz \
  https://archive.apache.org/dist/spark/spark-3.5.9/spark-3.5.9-bin-hadoop3.tgz \
  --no-check-certificate
```

```
sudo tar -xzf /tmp/spark-3.5.9-bin-hadoop3.tgz -C /opt

sudo mv /opt/spark-3.5.9-bin-hadoop3 /opt/spark

sudo chown -R "$USER:$(id -gn)" /opt/spark
```

Check all fine

Environment variable for Spark 

```
ls -ld /opt/spark
ls /opt/spark/bin
```

```
tee -a "$HOME/.bashrc" >/dev/null <<'EOF'

# --- Spark configuration ---
export SPARK_HOME=/opt/spark
export PATH="$SPARK_HOME/bin:$SPARK_HOME/sbin:$PATH"

# Use the existing Python virtual environment
export PYSPARK_PYTHON="$HOME/dataengenv/bin/python"
export PYSPARK_DRIVER_PYTHON="$HOME/dataengenv/bin/python"

# Spark's included Python and Py4J libraries
export PYTHONPATH="$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip${PYTHONPATH:+:$PYTHONPATH}"
# --- end Spark configuration ---
EOF
```

### Delta Lake 3.3.2

```

curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/delta-spark_2.12-3.3.2.jar" \
  https://repo.maven.apache.org/maven2/io/delta/delta-spark_2.12/3.3.2/delta-spark_2.12-3.3.2.jar
```
```
curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/delta-storage-3.3.2.jar" \
  https://repo.maven.apache.org/maven2/io/delta/delta-storage/3.3.2/delta-storage-3.3.2.jar


```

# Apache Iceberg 1.10.0

# Spark 3.5 / Scala 2.12 / Java 11 compatible choice

```

curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/iceberg-spark-runtime-3.5_2.12-1.10.0.jar" \
  https://repo.maven.apache.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.10.0/iceberg-spark-runtime-3.5_2.12-1.10.0.jar
```

# Kafka Connectors

For spark kafka connectors

```
curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/spark-sql-kafka-0-10_2.12-3.5.9.jar" \
  https://repo.maven.apache.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.9/spark-sql-kafka-0-10_2.12-3.5.9.jar
```

```
curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/kafka-clients-3.4.1.jar" \
  https://repo.maven.apache.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar
```

used for consumer poll by spark


```
curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/commons-pool2-2.11.1.jar" \
  https://repo.maven.apache.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar
```

if avro used..

```
curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/spark-avro_2.12-3.5.9.jar" \
  https://repo.maven.apache.org/maven2/org/apache/spark/spark-avro_2.12/3.5.9/spark-avro_2.12-3.5.9.jar
```

optional for local developemnt, only for kafka in secured mode, like aws/azure managed kafka, auth/sasl/ configuration

```
curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/spark-token-provider-kafka-0-10_2.12-3.5.9.jar" \
  https://repo.maven.apache.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.9/spark-token-provider-kafka-0-10_2.12-3.5.9.jar
```


## MySQL

```
curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/mysql-connector-j-8.4.0.jar" \
  https://repo.maven.apache.org/maven2/com/mysql/mysql-connector-j/8.4.0/mysql-connector-j-8.4.0.jar
```

## PostgreSQL

```
curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/postgresql-42.7.8.jar" \
  https://repo.maven.apache.org/maven2/org/postgresql/postgresql/42.7.8/postgresql-42.7.8.jar
```


## For Polaris REST catalog, S3 not for intern batch

```
curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/iceberg-aws-bundle-1.10.0.jar" \
  https://repo.maven.apache.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.10.0/iceberg-aws-bundle-1.10.0.jar
```


# Hadoop S3A connector

```
curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/hadoop-aws-3.3.4.jar" \
  https://repo.maven.apache.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
```

```
curl -k --fail --location --retry 5 --continue-at - \
  --output "$SPARK_HOME/jars/aws-java-sdk-bundle-1.12.262.jar" \
  https://repo.maven.apache.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar
```

 
 
```
source "$HOME/.bashrc"
```

```
echo "$SPARK_HOME"
which pyspark
which spark-submit
echo "$PYSPARK_PYTHON"

spark-submit --version
```

local spark server, embedded mode

```
pyspark --master local[*]
```

Some python code to test spark hello world

```
spark.range(1, 11).show()
```

Another way to run spark

```
python - <<'PY'
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("SparkTest")
    .master("local[*]")
    .getOrCreate()
)

print("Spark version:", spark.version)
spark.range(1, 11).show()

spark.stop()
PY
```


spark master

```
/opt/spark/sbin/start-master.sh
```

```
jps
```

check in local browser

http://localhost:8080

spark worker

```
/opt/spark/sbin/start-worker.sh "spark://$(hostname):7077"
```

```
jps
```

and Check the spark master ui

http://localhost:8080

spark submit

```
spark-submit \
  --master "spark://$(hostname):7077" \
  /opt/spark/examples/src/main/python/pi.py 10
```

# now run spark over yarn, check README.md for starting hdfs, yarn

```
pyspark \
  --master yarn \
  --deploy-mode client
```



```
spark.range(1, 11).show()

print("Spark version:", spark.version)
print("Spark master:", spark.sparkContext.master)
print("Application ID:", spark.sparkContext.applicationId)
```

```
spark.stop()
exit()
```


# submit using yarn, client mode, discussed later

```
spark-submit \
  --master yarn \
  --deploy-mode client \
  /opt/spark/examples/src/main/python/pi.py 10
```

# submit using yarn, cluster mode, discussed later

```
spark-submit \
  --master yarn \
  --deploy-mode cluster \
  /opt/spark/examples/src/main/python/pi.py 10
```

# submit on EMR S3 

```
spark-submit \
  --master yarn \
  --total-executor-cores 1 \
  --executor-memory 1g \
  --deploy-mode client \
  s3://BUCKET_NAME/src/Movies-Bronze-To-Silver.py  \
  --input s3://BUCKET_NAME/movielens/movies/  \
  --output s3://BUCKET_NAME/movielens/silver-emr/movies/
```

  


## SPARK CONF, DO NOT ATTEMPT NOW, explained later

```
cd /opt/spark/conf

cp -n spark-env.sh.template spark-env.sh
cp -n spark-defaults.conf.template spark-defaults.conf
cp -n log4j2.properties.template log4j2.properties
``


# HADOOP DOWNLOAD

```
wsl
```

```
cd ~
```

```
wget -O hadoop-3.3.6.tar.gz \
  https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz --no-check-certificate
```

For faster download especially archive.apache.org slow sometimes

```
sudo apt update
sudo apt install -y aria2

aria2c -x 16 -s 16 -k 1M -c --check-certificate=false \
  -o hadoop-3.3.6.tar.gz \
  "https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz"
```



temporary arrangement
```
wsl
cd /mnt/c/username/Downloads
ls

cp hadoop-3.3.6.tar.gz  /tmp
```


## DONT FOLLOW FURTHER NOTES

Extract and copy hadoop binaries to /opt directory.

opt means optional software components. a standard, conventional approach to install additional components on Linux eco system

```
sudo tar -xzf /tmp/hadoop-3.3.6.tar.gz -C /opt

sudo mv /opt/hadoop-3.3.6 /opt/hadoop

sudo chown -R "$USER:$(id -gn)" /opt/hadoop
```

#### Java setup



```
sudo apt update
```


```
sudo apt install -y \
  openjdk-11-jdk \
  openssh-server \
  libxml2-utils \
  wget \
  curl \
  rsync
```

Ensure java 11

```
java -version
```

```
javac -version
```
check the path where java available
```
dirname "$(dirname "$(readlink -f "$(which java)")")"
```


check java installation location

```
/usr/lib/jvm/java-11-openjdk-amd64/bin/java -version
```



```
sudo cat /etc/environment
```

if below files, you will brick your linux, no warranty, no support

```
sudo tee -a /etc/environment > /dev/null <<'EOF'
JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"
HADOOP_HOME="/opt/hadoop"
HADOOP_CONF_DIR="/opt/hadoop/etc/hadoop"
EOF
```

check again , if we could see java env added, 



```
sudo cat /etc/environment
```

.bashrc support

```
tee -a "$HOME/.bashrc" > /dev/null <<'EOF'

# Hadoop environment
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR="$HADOOP_HOME/etc/hadoop"
export PATH="$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin"
EOF
```

```
source "$HOME/.bashrc"
```
 


```
hadoop version
```

```
mkdir -p "$HOME/hadoop-data/tmp"
mkdir -p "$HOME/hadoop-data/namenode"
mkdir -p "$HOME/hadoop-data/datanode"
mkdir -p "$HOME/hadoop-data/yarn/local"
mkdir -p "$HOME/hadoop-data/yarn/log"
mkdir -p "$HOME/hadoop-logs"

mkdir -p "$HOME/hadoop-data/namesecondary"

```

available storage

```
df -h "$HOME"
free -h
```

core-site.xml


```
tee "$HADOOP_CONF_DIR/core-site.xml" > /dev/null <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<configuration>

    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://localhost:9000</value>
    </property>

    <property>
        <name>hadoop.tmp.dir</name>
        <value>${user.home}/hadoop-data/tmp</value>
    </property>

    <property>
        <name>io.file.buffer.size</name>
        <value>65536</value>
    </property>

</configuration>
EOF
```

hdfs-site.xml

```
tee "$HADOOP_CONF_DIR/hdfs-site.xml" > /dev/null <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<configuration>

    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>

    <property>
        <name>dfs.blocksize</name>
        <value>67108864</value>
        <description>64 MB blocks for a small training cluster</description>
    </property>

    <property>
        <name>dfs.namenode.name.dir</name>
        <value>file://${user.home}/hadoop-data/namenode</value>
    </property>

    <property>
        <name>dfs.datanode.data.dir</name>
        <value>file://${user.home}/hadoop-data/datanode</value>
    </property>

    <property>
        <name>dfs.namenode.checkpoint.dir</name>
        <value>file://${user.home}/hadoop-data/namesecondary</value>
    </property>

    <property>
        <name>dfs.permissions.enabled</name>
        <value>true</value>
    </property>

</configuration>
EOF
```

mapred-site.xml

```
tee "$HADOOP_CONF_DIR/mapred-site.xml" > /dev/null <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<configuration>

    <property>
        <name>mapreduce.framework.name</name>
        <value>yarn</value>
    </property>

    <property>
        <name>mapreduce.application.classpath</name>
        <value>$HADOOP_MAPRED_HOME/share/hadoop/mapreduce/*:$HADOOP_MAPRED_HOME/share/hadoop/mapreduce/lib/*</value>
    </property>

    <property>
        <name>mapreduce.map.memory.mb</name>
        <value>1024</value>
    </property>

    <property>
        <name>mapreduce.map.java.opts</name>
        <value>-Xmx768m</value>
    </property>

    <property>
        <name>mapreduce.reduce.memory.mb</name>
        <value>1536</value>
    </property>

    <property>
        <name>mapreduce.reduce.java.opts</name>
        <value>-Xmx1024m</value>
    </property>

    <property>
        <name>yarn.app.mapreduce.am.resource.mb</name>
        <value>768</value>
    </property>

    <property>
        <name>yarn.app.mapreduce.am.command-opts</name>
        <value>-Xmx512m</value>
    </property>

    <property>
        <name>mapreduce.jobhistory.address</name>
        <value>localhost:10020</value>
    </property>

    <property>
        <name>mapreduce.jobhistory.webapp.address</name>
        <value>localhost:19888</value>
    </property>

</configuration>
EOF
```

yarn-site.xml

```
tee "$HADOOP_CONF_DIR/yarn-site.xml" > /dev/null <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<configuration>

    <property>
        <name>yarn.resourcemanager.hostname</name>
        <value>localhost</value>
    </property>

    <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle</value>
    </property>

    <property>
        <name>yarn.nodemanager.aux-services.mapreduce_shuffle.class</name>
        <value>org.apache.hadoop.mapred.ShuffleHandler</value>
    </property>

    <property>
        <name>yarn.nodemanager.resource.memory-mb</name>
        <value>8192</value>
        <description>Maximum total memory available to YARN containers</description>
    </property>

    <property>
        <name>yarn.scheduler.minimum-allocation-mb</name>
        <value>512</value>
    </property>

    <property>
        <name>yarn.scheduler.maximum-allocation-mb</name>
        <value>8192</value>
    </property>

    <property>
        <name>yarn.nodemanager.resource.cpu-vcores</name>
        <value>4</value>
    </property>

    <property>
        <name>yarn.scheduler.minimum-allocation-vcores</name>
        <value>1</value>
    </property>

    <property>
        <name>yarn.scheduler.maximum-allocation-vcores</name>
        <value>4</value>
    </property>

    <property>
        <name>yarn.nodemanager.local-dirs</name>
        <value>${user.home}/hadoop-data/yarn/local</value>
    </property>

    <property>
        <name>yarn.nodemanager.log-dirs</name>
        <value>${user.home}/hadoop-data/yarn/log</value>
    </property>

    <property>
        <name>yarn.nodemanager.vmem-check-enabled</name>
        <value>false</value>
        <description>Avoid unreliable virtual-memory checks under WSL</description>
    </property>

    <property>
        <name>yarn.nodemanager.pmem-check-enabled</name>
        <value>true</value>
    </property>

    <property>
        <name>yarn.log-aggregation-enable</name>
        <value>false</value>
        <description>Disabled to avoid accumulating training logs in HDFS</description>
    </property>

    <property>
        <name>yarn.nodemanager.env-whitelist</name>
        <value>JAVA_HOME,HADOOP_HOME,HADOOP_COMMON_HOME,HADOOP_HDFS_HOME,HADOOP_CONF_DIR,HADOOP_YARN_HOME,HADOOP_MAPRED_HOME,CLASSPATH_PREPEND_DISTCACHE</value>
    </property>

</configuration>
EOF
```


```

tee -a "$HADOOP_CONF_DIR/hadoop-env.sh" > /dev/null <<'EOF'

# Training-cluster environment
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

export HADOOP_LOG_DIR="${HOME}/hadoop-logs"

# Small single-node cluster heap limits
export HDFS_NAMENODE_OPTS="-Xmx512m ${HDFS_NAMENODE_OPTS}"
export HDFS_DATANODE_OPTS="-Xmx512m ${HDFS_DATANODE_OPTS}"
export HDFS_SECONDARYNAMENODE_OPTS="-Xmx256m ${HDFS_SECONDARYNAMENODE_OPTS}"
EOF
```

```
tee -a "$HADOOP_CONF_DIR/yarn-env.sh" > /dev/null <<'EOF'

# Training-cluster environment
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

export YARN_RESOURCEMANAGER_HEAPSIZE=512
export YARN_NODEMANAGER_HEAPSIZE=512
EOF
```

job history

```
tee -a "$HADOOP_CONF_DIR/mapred-env.sh" > /dev/null <<'EOF'

# Training-cluster environment
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_JOB_HISTORYSERVER_HEAPSIZE=256
EOF
```

configure workers list

```
printf '%s\n' localhost > "$HADOOP_CONF_DIR/workers"
```

check 

```
cat "$HADOOP_CONF_DIR/workers"
```

XML validation

 

Copy whole thing, ensure all four xml are good, no syntactical error, here we validate xml format, not hadoop conf right or wrong.

```
for file in core-site.xml hdfs-site.xml mapred-site.xml yarn-site.xml
do
    echo "Checking $file"
    xmllint --noout "$HADOOP_CONF_DIR/$file"
done
```

Resolved home directory, especially to validate ${user.home} worked or not,
it must show your home directory

Confirm resolved directories

Hadoop can show the resolved values:

```
hdfs getconf -confKey fs.defaultFS
hdfs getconf -confKey hadoop.tmp.dir
hdfs getconf -confKey dfs.namenode.name.dir
hdfs getconf -confKey dfs.datanode.data.dir
```

CRITICAL PART

Verify passwordless SSH

```
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

ssh-keyscan -H localhost >> "$HOME/.ssh/known_hosts"
chmod 600 "$HOME/.ssh/known_hosts"
```

```
ssh -o BatchMode=yes localhost 'echo "SSH working as $(whoami)"'
```

if above failed, you need to configure ssh key

```
if [ ! -f "$HOME/.ssh/id_ed25519" ]; then
    ssh-keygen -t ed25519 -N "" -f "$HOME/.ssh/id_ed25519"
fi

touch "$HOME/.ssh/authorized_keys"

grep -qxF "$(cat "$HOME/.ssh/id_ed25519.pub")" \
    "$HOME/.ssh/authorized_keys" ||
    cat "$HOME/.ssh/id_ed25519.pub" >> "$HOME/.ssh/authorized_keys"

chmod 600 "$HOME/.ssh/authorized_keys"
```

check again, you must see echo msg printed

```
ssh -o BatchMode=yes localhost 'echo "SSH working as $(whoami)"'
```

Hadoop Formatting

Below command is to test, if hadoop has some files, if no shows shown, means , we need to format hdfs freshly

```
find "$HOME/hadoop-data/namenode" -maxdepth 2 -type f
```

format hdfs now. it is like formatting your pen drive, harddisk etc but limited to hadoop. 

```
hdfs namenode -format hadoop-training
```

check again, if any files found, we expect few defaults added by hadoop format command

```
find "$HOME/hadoop-data/namenode" -maxdepth 2 -type f
```

Now real fun start, did we really configure correctly or not

Start HDFS

```
start-dfs.sh
```

check namenode, datanode, secondary data node, also adding your host into known host list

to check these services alive or dead,

jps command print running java processes

```
jps
```

must print 

xyz SecondaryNameNode

xyz DataNode

xyz NameNode

xyz is process id

HDFS Health check

```
hdfs dfsadmin -report
```

while it prints more details, validate it has a line

Live datanodes (1):


Now you are reaching The Shawshank Redemption  climax, whether Andy escaped jail, living happily on sea shore with his dream boat else ??

create directories in hdfs

```
hdfs dfs -mkdir -p "/user/$USER"
hdfs dfs -chown "$USER:$(id -gn)" "/user/$USER"
```

```
hdfs dfs -ls /user
```

List them

Now real test start, can we upload file, creating directories did not use datanodes, it uses only namenode.

Let us upload a file into hdfs

```
mkdir -p "$HOME/hadoop-lab/input"
```

create a localfile to upload into cloud files

```
tee "$HOME/hadoop-lab/input/file1.txt" > /dev/null <<'EOF'
hadoop stores large data
hadoop uses hdfs
mapreduce processes data
EOF
```

yet another local file to test your patience

```
tee "$HOME/hadoop-lab/input/file2.txt" > /dev/null <<'EOF'
hdfs stores blocks
yarn manages resources
mapreduce runs on yarn
EOF
```

yet another hdfs directory

```
hdfs dfs -mkdir -p input
```

upload files.. pray favorite gods, most hdfs setup fails here due to datanode, hdfs formatting

```
hdfs dfs -put -f "$HOME/hadoop-lab/input/"*.txt input/
```

sure, done, take deep breath!!, check if upload successful yet

```
hdfs dfs -ls input
```

```
hdfs dfs -cat 'input/*.txt'
```

does it print content?, celebrate!!, have small talk, non technical.. you earned 10 mins break

Still not yet done fully, we have to check Map Reduce/YARN

## Start YARN


```
start-yarn.sh
```

must start resourcemanager, nodemanagers

```
jps
```



# Utilities, logs

```
find "$HOME/hadoop-logs" -maxdepth 1 -type f \
  -printf '%T@ %p\n' |
  sort -nr |
  head -10 |
  cut -d' ' -f2-
```

```
grep -RniE \
  'exception|error|failed|inaccessible|unsupported|could not' \
  "$HOME/hadoop-logs" |
  tail -80
```

end of daemon logs, if any error in resource or nodemanager, if they didn't start these logs unlikely present or may have last known errors

```
for file in "$HOME"/hadoop-logs/*resourcemanager* \
            "$HOME"/hadoop-logs/*nodemanager*
do
    [ -f "$file" ] || continue
    echo "===== $file ====="
    tail -80 "$file"
done
```


```
yarn node -list
```

Now start the MapReduce JobHistory Server

```
mapred --daemon start historyserver
```

```
jps
```

check JobHistoryServer

For Word count.. a hello world ritual in big data

```
hdfs dfs -mkdir -p "/user/$USER/input"
```

```
printf '%s\n' \
  'hadoop stores data in hdfs' \
  'hadoop mapreduce runs on yarn' \
  'yarn manages mapreduce resources' \
  > /tmp/wordcount.txt
```

```
hdfs dfs -put -f /tmp/wordcount.txt "/user/$USER/input/"
```


verify files exist

```
hdfs dfs -ls "/user/$USER/input"
hdfs dfs -cat "/user/$USER/input/wordcount.txt"
```

remove old word count output if any

```
hdfs dfs -rm -r -f "/user/$USER/output"
```

another big test,, worth another prayer for map reduce

```
hadoop jar \
  "$HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar" \
  wordcount \
  "/user/$USER/input" \
  "/user/$USER/output"
```

map % reduce %, must reach 100% for both

check output, do you see word count output? celebrate..

```
hdfs dfs -cat "/user/$USER/output/part-r-00000"
```

```
yarn application -list -appStates ALL
```

to stop the server at the end

```
mapred --daemon stop historyserver
stop-yarn.sh
stop-dfs.sh
```


```
| Component                 |  Port | Protocol   | Nginx HTTP proxy? Local browser access            |
| ------------------------- | ----: | ---------- | ---------------------------- |
| NameNode UI               |  9870 | HTTP       | Yes                          |
| DataNode UI               |  9864 | HTTP       | Yes, but usually unnecessary |
| ResourceManager UI        |  8088 | HTTP       | Yes                          |
| NodeManager UI            |  8042 | HTTP       | Yes, but usually unnecessary |
| JobHistory UI             | 19888 | HTTP       | Yes                          |
| NameNode filesystem       |  9000 | Hadoop RPC | No                           |
| DataNode transfer         |  9866 | Native TCP | No                           |
| DataNode IPC              |  9867 | Hadoop RPC | No                           |
| ResourceManager client    |  8032 | Hadoop RPC | No                           |
| ResourceManager scheduler |  8030 | Hadoop RPC | No                           |
| Resource tracker          |  8031 | Hadoop RPC | No                           |
| ResourceManager admin     |  8033 | Hadoop RPC | No                           |
| JobHistory RPC            | 10020 | Hadoop RPC | No                           |

```



```
sudo ss -lntp |
  grep -E ':(9870|9864|8088|8042|19888|9000|9866|9867|8030|8031|8032|8033|10020)\b'
```


```
curl -I http://127.0.0.1:8088/
curl -I http://127.0.0.1:9870/
curl -I http://127.0.0.1:19888/
```



Hive setup for wsl/ubuntu linux for single node, testing purpose

### do not follow, instructions is in progress

```
wsl
```

```
cd ~
```


```
wget -O apache-hive-4.0.0-bin.tar.gz \
  https://archive.apache.org/dist/hive/hive-4.0.0/apache-hive-4.0.0-bin.tar.gz \
  --no-check-certificate
```

```
aria2c -x 16 -s 16 -k 1M -c --check-certificate=false \
  -o apache-hive-4.0.0-bin.tar.gz \
  "https://archive.apache.org/dist/hive/hive-4.0.0/apache-hive-4.0.0-bin.tar.gz"
```

```
sudo tar -xzf /tmp/apache-hive-4.0.0-bin.tar.gz -C /opt
```

```
sudo mv /opt/apache-hive-4.0.0-bin /opt/hive
```

we will run hive on logged in user credentials, not as backend. this is not a good practice.

```
sudo chown -R "$USER:$(id -gn)" /opt/hive
```

check ownership

```
ls -ld /opt/hive
```

```
tee -a "$HOME/.bashrc" > /dev/null <<'EOF'

# Apache Hive environment
export HIVE_HOME=/opt/hive
export HIVE_CONF_DIR="$HIVE_HOME/conf"
export PATH="$PATH:$HIVE_HOME/bin"
EOF
```

### Local filesystem

```
sudo mkdir -p /tmp/hive-local
sudo chmod 1777 /tmp/hive-local
```

# HDFS

```
hdfs dfs -mkdir -p /tmp/hive
hdfs dfs -chmod 1777 /tmp/hive
```

```
hdfs dfs -mkdir -p /user/hive/warehouse
hdfs dfs -chmod 775 /user/hive/warehouse
```


```
source "$HOME/.bashrc"
```
validate all the available templates, templates are config files examples.

```
ls "$HIVE_CONF_DIR" | sort
```

we clone or create existing template or create $HIVE_CONF_DIR/hive-env.sh

```
if [ -f "$HIVE_CONF_DIR/hive-env.sh.template" ]; then
    cp "$HIVE_CONF_DIR/hive-env.sh.template" \
       "$HIVE_CONF_DIR/hive-env.sh"
else
    touch "$HIVE_CONF_DIR/hive-env.sh"
fi
```

append JAVA, hadoop, hadoop, hive env into hive-env.sh file

```
tee -a "$HIVE_CONF_DIR/hive-env.sh" > /dev/null <<'EOF'
 

# Hadoop training-lab environment
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop

# Hive environment
export HIVE_HOME=/opt/hive
export HIVE_CONF_DIR=/opt/hive/conf
export HIVE_LOG_DIR="${HOME}/hive-logs"

# Heap for small WSL training environment
export HADOOP_HEAPSIZE=1024
EOF
```


```
mkdir -p "$HOME/hive-logs"
mkdir -p "$HOME/hive-data/scratch"
mkdir -p "$HOME/hive-data/resources"
```

check hive version , should be 4.0.0

```
hive --version
```

beeline version same as hive version

```
beeline --version
```

```
mysql -u root -p
```

copy paste one after another

```
CREATE DATABASE IF NOT EXISTS hive_metastore;

CREATE USER IF NOT EXISTS 'hive'@'localhost'
IDENTIFIED BY 'HiveLab@123';

ALTER USER 'hive'@'localhost'
IDENTIFIED BY 'HiveLab@123';

GRANT ALL PRIVILEGES
ON hive_metastore.*
TO 'hive'@'localhost';

FLUSH PRIVILEGES;

SHOW DATABASES LIKE 'hive_metastore';

SELECT user, host, plugin
FROM mysql.user
WHERE user = 'hive';

SHOW GRANTS FOR 'hive'@'localhost';

EXIT;
```

test your mysql account for hive working

```
mysql \
  --protocol=TCP \
  -h 127.0.0.1 \
  -P 3306 \
  -u hive \
  -p \
  hive_metastore
```

enter password

ensure database, user..

```
SELECT DATABASE(), CURRENT_USER(), VERSION();
SHOW TABLES;
EXIT;
```

```
wget -O mysql-connector-j-8.4.0.jar \
  https://repo.maven.apache.org/maven2/com/mysql/mysql-connector-j/8.4.0/mysql-connector-j-8.4.0.jar --no-check-certificate
```

copy mysql connector to hive lib directory

```
cp /tmp/mysql-connector-j-8.4.0.jar "$HIVE_HOME/lib/"
```


The example uses local temporary directories rather than a particular login account.

Setup hive config

```
tee "$HIVE_CONF_DIR/hive-site.xml" > /dev/null <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<configuration>

    <!-- ====================================================== -->
    <!-- MySQL external metastore                               -->
    <!-- Derby embedded metastore is deliberately not used      -->
    <!-- ====================================================== -->

    <property>
        <name>javax.jdo.option.ConnectionURL</name>
        <value>jdbc:mysql://127.0.0.1:3306/hive_metastore?useSSL=false&amp;allowPublicKeyRetrieval=true&amp;serverTimezone=UTC</value>
    </property>

    <property>
        <name>javax.jdo.option.ConnectionDriverName</name>
        <value>com.mysql.cj.jdbc.Driver</value>
    </property>

    <property>
        <name>javax.jdo.option.ConnectionUserName</name>
        <value>hive</value>
    </property>

    <property>
        <name>javax.jdo.option.ConnectionPassword</name>
        <value>HiveLab@123</value>
    </property>

    <property>
        <name>datanucleus.schema.autoCreateAll</name>
        <value>false</value>
    </property>

    <property>
        <name>hive.metastore.schema.verification</name>
        <value>true</value>
    </property>

    <!-- ====================================================== -->
    <!-- Standalone Hive Metastore service                      -->
    <!-- ====================================================== -->

    <property>
        <name>hive.metastore.uris</name>
        <value>thrift://localhost:9083</value>
    </property>

    <!-- ====================================================== -->
    <!-- HDFS warehouse and scratch directories                 -->
    <!-- ====================================================== -->

    <property>
        <name>hive.metastore.warehouse.dir</name>
        <value>/user/hive/warehouse</value>
    </property>

<!--  
    <property>
        <name>hive.metastore.warehouse.external.dir</name>
        <value>/user/hive/external</value>
    </property>
-->

    <property>
        <name>hive.exec.scratchdir</name>
        <value>/tmp/hive</value>
    </property>

    <!-- linux path, instead of actual linux user, kept in temp -->
    <property>
        <name>hive.exec.local.scratchdir</name>
        <value>/tmp/hive-local</value>
        
    </property>

<!--
    <property>
        <name>hive.downloaded.resources.dir</name>
        <value>/tmp/hive-resources</value>
        
    </property>
-->

    <!-- ====================================================== -->
    <!-- MapReduce execution through YARN                       -->
    <!-- ====================================================== -->

    <property>
        <name>hive.execution.engine</name>
        <value>mr</value>
    </property>

    <property>
        <name>hive.fetch.task.conversion</name>
        <value>none</value>
        <description>
            Make query execution visible through MapReduce during training
        </description>
    </property>

    <!-- ====================================================== -->
    <!-- HiveServer2                                            -->
    <!-- ====================================================== -->

    <property>
        <name>hive.server2.thrift.bind.host</name>
        <value>localhost</value>
    </property>

    <property>
        <name>hive.server2.thrift.port</name>
        <value>10000</value>
    </property>

    <property>
        <name>hive.server2.webui.host</name>
        <value>localhost</value>
    </property>

    <property>
        <name>hive.server2.webui.port</name>
        <value>10002</value>
    </property>

    <property>
        <name>hive.server2.authentication</name>
        <value>NONE</value>
    </property>

    <property>
        <name>hive.server2.enable.doAs</name>
        <value>false</value>
        <description>
            Suitable for this single-user WSL training environment
        </description>
    </property>

<property>
    <name>hive.metastore.event.db.notification.api.auth</name>
    <value>false</value>
    <description>
        Allow HiveServer2 notification API access in this local training setup
    </description>
</property>

<!-- SET mapreduce.job.user.classpath.first=true; -->
<property>
    <name>mapreduce.job.user.classpath.first</name>
    <value>true</value>
    <description>
        Load Hive and ORC dependencies before Hadoop dependencies in MapReduce >
    </description>
</property>


</configuration>
EOF
```

```
cat $HIVE_CONF_DIR/hive-site.xml
```

run jps command check if hdfs and yarn components working NameNode, DataNode, SecondaryNameNode, ResourceManager, NodeManager, JobHistoryServer
else start them

```
start-dfs.sh
```

```
start-yarn.sh
```

history server

```
mapred --daemon start historyserver
```

run jps again..

hdfs health check
check live nodes (1), 

```
hdfs dfsadmin -report
```

hive needs tmp, warehouse

```
hdfs dfs -mkdir -p /tmp
hdfs dfs -chmod 1777 /tmp

hdfs dfs -mkdir -p /tmp/hive
hdfs dfs -chmod 1777 /tmp/hive

hdfs dfs -mkdir -p /user/hive/warehouse
hdfs dfs -chown "$USER:$(id -gn)" /user/hive/warehouse
hdfs dfs -chmod 775 /user/hive/warehouse

hdfs dfs -mkdir -p /user/hive/external
hdfs dfs -chown "$USER:$(id -gn)" /user/hive/external
hdfs dfs -chmod 775 /user/hive/external



```

verify all directories created working

```
hdfs dfs -ls -d \
  /tmp \
  /tmp/hive \
  /user/hive/warehouse \
  /user/hive/external
```

yarn must show one node

```
yarn node -list
```

create database for hive metadata

```
schematool -dbType mysql -initSchema --verbose
```

```
schematool -dbType mysql -info
```


Start Hive Metastore

```
mkdir -p "$HOME/hive-logs"
```

```
nohup hive --service metastore \
  > "$HOME/hive-logs/metastore.log" 2>&1 &
```

check if hive metastore listening on 9083

```
ss -lnt | grep ':9083'
```

if you don't see metastore, see the errors , even check if running

```
tail -80 "$HOME/hive-logs/metastore.log"
```

Start HiveServer2

```
nohup hiveserver2 \
  > "$HOME/hive-logs/hiveserver2.log" 2>&1 &
```

check if it is listening on port 10000 or 10002 after a minute

```
ss -lnt | grep -E ':(10000|10002)\b'
```

if you don't see the port,

```
tail -100 "$HOME/hive-logs/hiveserver2.log"
```

trouble-shooting commands

```
find /tmp "$HOME" -type f -name 'hive.log' \
  -printf '%T@ %p\n' 2>/dev/null |
sort -nr | head
```

For the current login account, check the usual Hive log location:

```
tail -150 "/tmp/$(id -un)/hive.log"
```

## beeline

beeline is a client tool for hive, it connect to hive server 2

```
beeline -u 'jdbc:hive2://localhost:10000/default' -n "$USER"
```

```
SHOW DATABASES;
CREATE DATABASE IF NOT EXISTS training;
USE training;
```

Create a simple managed table:

```
CREATE TABLE test_message (
    id INT,
    message STRING
);
```

Insert and query:

```
INSERT INTO test_message
VALUES (1, 'Hive is working');
SELECT * FROM test_message;
```

Expected:

1    Hive is working

Check the execution engine:

```
SET hive.execution.engine;
```

Expected:

```
hive.execution.engine=mr
```

```
USE training;

SET hive.execution.engine=mr;
SET hive.fetch.task.conversion=none;
```

```
CREATE TABLE sales (
    city STRING,
    amount INT
);

INSERT INTO sales VALUES
('Bengaluru', 100),
('Hyderabad', 200),
('Bengaluru', 300),
('Chennai', 150);
```

```
SELECT city, SUM(amount) AS total
FROM sales
GROUP BY city;
```

use EXPLAIN

## DONT RUN THESE COMMANDS

```
yarn application -list -appStates ALL
```






```
 pkill -f HiveServer2
 pkill -f HiveMetaStore
```


# Downgrade hive to 4.0.0


copy to home directory 

```
cp $HIVE_HOME/lib/mysql-connector-j-8.4.0.jar ~
```


```
sudo rm -rf /opt/hive
```

```
cp ~/mysql-connector-j-8.4.0.jar $HIVE_HOME/lib/
```

## DO NOT FOLLOW   

if queries needs to be stored

```xml
<property>
  <name>hive.server2.logging.operation.enabled</name>
  <value>true</value>
</property>

<property>
  <name>hive.server2.logging.operation.log.location</name>
  <value>/logs/hive/operation_logs</value>
</property>

<property>
  <name>hive.server2.logging.operation.level</name>
  <value>VERBOSE</value>
</property>
```


```
sudo apt install -y openjdk-8-jdk

```

```
update-java-alternatives --list
```

fix in hive env file

```
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

## ICEBERG DELTA


 
# DELTA LAKE 3.3.2
# Spark 3.5.x / Scala 2.12
 

```
curl --fail --location --retry 5 --continue-at - \
  --output downloads/delta-spark_2.12-3.3.2.jar \
  https://repo.maven.apache.org/maven2/io/delta/delta-spark_2.12/3.3.2/delta-spark_2.12-3.3.2.jar

```


```
curl --fail --location --retry 5 --continue-at - \
  --output downloads/delta-storage-3.3.2.jar \
  https://repo.maven.apache.org/maven2/io/delta/delta-storage/3.3.2/delta-storage-3.3.2.jar
```

 
# APACHE ICEBERG 1.10.0
# Spark 3.5 / Scala 2.12 / Java 11
 


```
curl --fail --location --retry 5 --continue-at - \
  --output downloads/iceberg-spark-runtime-3.5_2.12-1.10.0.jar \
  https://repo.maven.apache.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.10.0/iceberg-spark-runtime-3.5_2.12-1.10.0.jar

```

 
# ICEBERG AWS BUNDLE
# For Iceberg + S3/AWS support
 


```
curl --fail --location --retry 5 --continue-at - \
  --output downloads/iceberg-aws-bundle-1.10.0.jar \
  https://repo.maven.apache.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.10.0/iceberg-aws-bundle-1.10.0.jar

```

we need iceberg also for trino, s3 for trino, hive for  trino.