"""Regenerate the three architecture diagrams offline (requires Pillow)."""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parent
source = ROOT.parents[1] / '00-kubernetes-introduction/assets/render_diagrams.py'
spec = importlib.util.spec_from_file_location('course_figures', source)
figures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(figures)
figures.ROOT = ROOT
F = figures.Figure
B, G, P, A = figures.BLUE, figures.GREEN, figures.PURPLE, figures.AMBER


def render():
    f = F('cluster-overview', 'Our big data demonstration architecture',
          'One Ubuntu host, one Minikube node, and several application groups.')
    f.box(50, 170, 1100, 95, 'Ubuntu host: browser, terminal and source checkout',
          ['Guacamole desktop | ~/workspace (or chosen folder) | host Docker image store'], B)
    f.arrow([(600, 265), (600, 293)], B)
    f.rect(50, 295, 1100, 340, '#ffffff', P)
    f.text(70, 310, 'Docker container: bigdata Minikube node | application runtime: containerd', 22, P, True)
    f.box(70, 352, 340, 118, 'Cluster foundation',
          ['API / scheduler / controllers', 'kubelet / DNS / local storage'], P, 18)
    f.box(430, 352, 340, 118, 'Data services',
          ['SeaweedFS S3 / Polaris', 'PostgreSQL / MySQL'], G, 18)
    f.box(790, 352, 340, 118, 'Compute and streaming',
          ['Jupyter / HDFS / Spark', 'ZooKeeper / Kafka'], G, 18)
    f.box(70, 490, 340, 135, 'Visibility and access',
          ['Headlamp / metrics-server', 'Loki / Alloy / Prometheus', 'Grafana / Jaeger'], B, 17)
    f.box(430, 490, 340, 118, 'Separate sessions',
          ['YARN / MapReduce history', 'Hive metastore / HiveServer2'], A, 18)
    f.box(790, 490, 340, 118, 'Later lesson manifests',
          ['Airflow / Trino / Marquez', 'Optional Adminer SQL browser'], A, 18)
    f.footer('Green = current application group. Amber = optional/separate, not started by setup-demo.sh.')
    f.save()

    f = F('cluster-data-paths', 'How applications use data and metadata',
          'Arrows show selected relationships; they do not imply a job is currently running.')
    f.box(50, 175, 310, 110, 'Jupyter / Python / PySpark',
          ['Interactive code and Spark driver', 'Source checkout at /workspace'], B, 17)
    f.box(440, 175, 310, 110, 'Spark master + worker',
          ['Standalone Spark execution', 'Distributed tasks on worker'], G, 17)
    f.arrow([(360, 220), (440, 220)], B)
    f.box(840, 175, 310, 110, 'Kafka + ZooKeeper',
          ['Events stored in Kafka', 'ZooKeeper coordinates broker'], G, 17)
    f.box(50, 345, 310, 115, 'Polaris REST catalog',
          ['Iceberg catalog / table metadata', 'Service state in PostgreSQL'], G, 17)
    f.box(440, 345, 310, 115, 'SeaweedFS S3',
          ['Object files / warehouse', 'Iceberg data and metadata files'], G, 17)
    f.box(840, 345, 310, 115, 'HDFS',
          ['NameNode: file metadata', 'DataNode: file blocks'], G, 17)
    f.arrow([(595, 285), (595, 345)], G)
    f.arrow([(750, 255), (790, 255), (790, 400), (840, 400)], G)
    f.arrow([(205, 285), (205, 345)], B)
    f.box(50, 515, 310, 105, 'PostgreSQL', ['Polaris catalog service state', 'Also available for SQL exercises'], G, 17)
    f.arrow([(205, 460), (205, 515)], G)
    f.box(440, 515, 310, 105, 'MySQL', ['SQL database exercises', 'Hive metadata in later session'], G, 17)
    f.box(840, 515, 310, 105, 'Separate compute paths', ['YARN jobs run on HDFS', 'Hive uses metastore + MySQL'], A, 17)
    f.footer('The initial deployment creates services. Notebook exercises create tables, files, topics and jobs.')
    f.save()

    f = F('cluster-observability-storage', 'Monitoring and persistent storage',
          'Start monitoring before applications; distinguish source files from cluster data.')
    f.box(50, 175, 300, 110, 'Application Pods',
          ['Container stdout / stderr', 'Selected file-log sidecars'], G, 17)
    f.box(450, 175, 300, 110, 'Alloy -> Loki',
          ['Collect and store logs', 'Query logs through Grafana'], B, 17)
    f.arrow([(350, 220), (450, 220)], B)
    f.box(850, 175, 300, 110, 'Grafana',
          ['Log and performance views', 'Reads Loki and Prometheus'], B, 17)
    f.arrow([(750, 220), (850, 220)], B)
    f.box(50, 335, 300, 110, 'Metrics endpoints',
          ['Native / JMX / kubelet', 'CPU, memory, service metrics'], G, 17)
    f.box(450, 335, 300, 110, 'Prometheus',
          ['Scrapes configured targets', 'Stores time-series metrics'], B, 17)
    f.arrow([(350, 380), (450, 380)], B)
    f.arrow([(750, 380), (800, 380), (800, 250), (850, 250)], B)
    f.box(850, 335, 300, 110, 'Jaeger',
          ['Receives instrumented traces', 'Not automatic app tracing'], B, 17)
    f.box(50, 505, 510, 112, 'Host source files',
          ['Chosen workspace -> node /course-workspace', 'Jupyter /workspace; retained outside cluster'], A, 18)
    f.box(600, 505, 550, 112, 'PVCs -> local PVs -> node storage',
          ['Database, HDFS, Kafka and monitoring data', 'Docker volume bigdata; profile deletion loses data'], A, 18)
    f.footer('Headlamp views Kubernetes resources. metrics-server supplies current usage, not historical monitoring.')
    f.save()


if __name__ == '__main__':
    render()
