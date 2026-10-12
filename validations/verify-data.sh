#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
kubectl -n bigdata wait --for=condition=Ready pod -l app=mysql --timeout=600s
kubectl -n bigdata wait --for=condition=Ready pod -l app=zookeeper --timeout=600s
kubectl -n bigdata wait --for=condition=Ready pod -l app=kafka --timeout=600s
if [[ "${VERIFY_READ_ONLY:-false}" != true ]]; then
  kubectl -n bigdata exec mysql-0 -- sh -ec \
    'MYSQL_PWD="$MYSQL_PASSWORD" mysql -h mysql -u "$MYSQL_USER" -D training -e "CREATE TABLE IF NOT EXISTS training_check (id INT PRIMARY KEY, message VARCHAR(100)); INSERT INTO training_check VALUES (1, '\''kubernetes-mysql-check'\'') ON DUPLICATE KEY UPDATE message=VALUES(message);"'
fi
LAB_MYSQL_RESULT=$(kubectl -n bigdata exec mysql-0 -- sh -ec \
  'MYSQL_PWD="$MYSQL_PASSWORD" mysql -h mysql -u "$MYSQL_USER" -D training -Nse "SELECT message FROM training_check WHERE id=1;"')
[[ "$LAB_MYSQL_RESULT" == kubernetes-mysql-check ]]
kubectl -n bigdata exec mysql-0 -- sh -ec \
  'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=TCP -h 127.0.0.1 -u root -Nse "SELECT CURRENT_USER(), VERSION();"'
if kubectl -n bigdata exec mysql-0 -- sh -ec \
  'MYSQL_PWD=wrong-password mysql -h mysql -u "$MYSQL_USER" -D training -e "SELECT 1"' >/dev/null 2>&1; then
  echo 'FAIL: MySQL accepted an incorrect password' >&2
  exit 1
fi
if kubectl -n bigdata exec mysql-0 -- sh -ec \
  'MYSQL_PWD=wrong-password mysql --protocol=TCP -h 127.0.0.1 -u root -e "SELECT 1"' >/dev/null 2>&1; then
  echo 'FAIL: MySQL root accepted an incorrect password' >&2
  exit 1
fi
echo 'PASS: MySQL persisted SQL row, team/root authentication and bad-password rejection.'

# This client runs in its own pod: service discovery and advertised broker DNS
# must work from outside the broker pod, including after scaling.
LAB_KAFKA_CLIENT="kafka-check-$(date +%s)-$$"
cleanup() {
  kubectl -n bigdata delete pod "$LAB_KAFKA_CLIENT" --ignore-not-found --wait=false >/dev/null
}
trap cleanup EXIT
LAB_CLIENT_COMMAND=$(cat <<'BASH'
set -euo pipefail
export KAFKA_HEAP_OPTS='-Xms128m -Xmx256m'
bootstrap=kafka.bigdata.svc.cluster.local:9092
if [[ "$VERIFY_READ_ONLY" != true ]]; then
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$bootstrap" --create --if-not-exists --topic training-check --partitions 1 --replication-factor 1
  printf 'kubernetes-kafka-check\n' | /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server "$bootstrap" --topic training-check --producer-property acks=all
fi
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$bootstrap" --describe --topic training-check
/opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server "$bootstrap" --topic training-check --from-beginning --max-messages 1 --timeout-ms 30000 > /tmp/received.txt
grep -qx 'kubernetes-kafka-check' /tmp/received.txt
echo 'PASS: independent Kafka client read the persisted message using service and broker DNS.'
BASH
)
kubectl -n bigdata run "$LAB_KAFKA_CLIENT" \
  --image=apache/kafka:3.9.1@sha256:4ceccc577f03f51f6af8dbfda55194d0d892f4fa7913ffbded567ce3895622ed \
  --restart=Never \
  --env="VERIFY_READ_ONLY=${VERIFY_READ_ONLY:-false}" \
  --overrides="{\"spec\":{\"activeDeadlineSeconds\":180,\"containers\":[{\"name\":\"$LAB_KAFKA_CLIENT\",\"resources\":{\"requests\":{\"cpu\":\"100m\",\"memory\":\"256Mi\"},\"limits\":{\"cpu\":\"1\",\"memory\":\"768Mi\"}}}]}}" \
  --override-type=strategic --command -- /bin/bash -ec "$LAB_CLIENT_COMMAND"
LAB_PHASE=Pending
for attempt in $(seq 1 180); do
  LAB_PHASE=$(kubectl -n bigdata get pod "$LAB_KAFKA_CLIENT" -o jsonpath='{.status.phase}')
  case "$LAB_PHASE" in Succeeded|Failed) break ;; esac
  sleep 1
done
kubectl -n bigdata logs "$LAB_KAFKA_CLIENT" --all-containers
[[ "$LAB_PHASE" == Succeeded ]] || { kubectl -n bigdata describe pod "$LAB_KAFKA_CLIENT"; exit 1; }
