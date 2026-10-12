from datetime import datetime, timezone
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG("training_smoke", start_date=datetime(2026, 1, 1, tzinfo=timezone.utc), schedule=None, catchup=False) as dag:
    BashOperator(task_id="shared_image_tools", bash_command="hadoop version && kafka-topics.sh --bootstrap-server kafka:9092 --list")
