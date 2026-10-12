# Kafka with ZooKeeper

Command-by-command setup: [Kafka](../00-setup/13-kafka.ipynb).

For remote SSH examples, set `LAB_SSH_USER` and `LAB_SSH_HOST` in your workstation shell to your Ubuntu login and host address.

Run commands from `workspace/`. This module uses Apache Kafka 3.9.1 from the [common course image](../SHARED_IMAGE.md) and the digest-pinned ZooKeeper 3.9.3 image. It starts one standalone ZooKeeper and one Kafka broker. The common image selects `args: [kafka]`, retaining ZooKeeper-mode startup through kafka-server-start.sh and the existing explicit properties file.

## Files and configuration

- `zookeeper.yaml`: Service, 1 GiB PVC and one standalone StatefulSet.
- `kafka.yaml`: ConfigMap, bootstrap Service, headless Service and a broker StatefulSet with a 5 GiB volume claim per broker.

`kafka-config` contains the readable broker configuration and a small startup script. The script converts the pod ordinal into a stable broker ID: `kafka-0` is broker 1, `kafka-1` is broker 2. Each broker advertises its own address, such as `kafka-0.kafka-headless.bigdata.svc.cluster.local:9092`. This permits broker-to-broker and independent client connections after scaling.

Bootstrap address for future Spark, Trino or other in-cluster clients:

```text
kafka.bigdata.svc.cluster.local:9092
```

The short address `kafka:9092` works in namespace bigdata. ZooKeeper is `zookeeper.bigdata.svc.cluster.local:2181`. Kafka uses plaintext connections within this local training cluster; no username/password or TLS is configured. ZooKeeper stores cluster metadata; Kafka stores records on separate per-broker volumes. [Kafka 3.9 broker configuration](https://kafka.apache.org/39/configuration/broker-configs/).

## Deploy

```bash
kubectl config use-context bigdata
bash build-image.sh  # First build only; loads the common image into containerd.
kubectl apply -f platform/namespace.yaml
kubectl apply -f kafka/zookeeper.yaml
kubectl -n bigdata rollout status statefulset/zookeeper --timeout=600s
kubectl apply -f kafka/kafka.yaml
kubectl -n bigdata rollout status statefulset/kafka --timeout=600s
kubectl -n bigdata get pods -l app=kafka
kubectl -n bigdata get pvc
```

The broker initContainer waits for the ZooKeeper TCP listener and DNS; readiness then checks the Kafka protocol using kafka-broker-api-versions.sh.

## Create a topic, produce and consume

```bash
kubectl -n bigdata exec kafka-0 -- /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 --create --if-not-exists \
  --topic training-events --partitions 3 --replication-factor 1

printf 'hello from Kubernetes\n' | kubectl -n bigdata exec -i kafka-0 -- \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server kafka:9092 \
  --topic training-events --producer-property acks=all

kubectl -n bigdata exec kafka-0 -- /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 --topic training-events \
  --from-beginning --max-messages 1 --timeout-ms 30000

kubectl -n bigdata exec kafka-0 -- /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 --describe --topic training-events
```

Root `bash validations/verify-data.sh` also tests Kafka from a separate temporary client pod, so the advertised addresses must actually be reachable from other pods. The client is removed afterwards; its test topic `training-check` remains for persistence practice.

## Add another broker

Change the Kafka StatefulSet's `replicas: 1` to `replicas: 2` in kafka.yaml to make the change survive subsequent apply/start commands. For a temporary scaling demonstration:

```bash
kubectl -n bigdata scale statefulset/kafka --replicas=2
kubectl -n bigdata rollout status statefulset/kafka --timeout=600s
kubectl -n bigdata get pods -l app=kafka
kubectl -n bigdata get pvc

kubectl -n bigdata exec kafka-0 -- /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 --create --if-not-exists \
  --topic replicated-events --partitions 3 --replication-factor 2
kubectl -n bigdata exec kafka-0 -- /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 --describe --topic replicated-events

printf 'replicated event\n' | kubectl -n bigdata exec -i kafka-0 -- \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server kafka:9092 \
  --topic replicated-events --producer-property acks=all
kubectl -n bigdata exec kafka-1 -- /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 --topic replicated-events \
  --from-beginning --max-messages 1 --timeout-ms 30000
```

The description must show two replicas and both broker IDs in ISR. Scaling creates a PVC for the additional broker automatically. Existing topics retain their original replica assignments; adding brokers does not automatically redistribute them or increase replication. Internal offsets/transaction topics initially use replication factor 1. A later resilience lesson will cover reassignment and minimum ISR settings.

Keep one ZooKeeper for this lesson. Do not scale its standalone StatefulSet to create an ensemble; an ensemble requires separate configuration and quorum planning. Multiple brokers on this Minikube node do not provide host-level high availability.

Scale down only after reviewing topic assignments and moving any data you need to retain. Reapplying the unedited `replicas: 1` manifest also scales back to one. Kafka broker PVCs are retained on scale-down and can be reused on scale-up.

## Access and troubleshoot

Kafka has two named listeners. INTERNAL binds port 9092 and advertises each broker's Kubernetes DNS name; replication uses this listener. EXTERNAL binds port 9093 in each broker and advertises `127.0.0.1:19092` for broker 0, `127.0.0.1:19093` for broker 1, and so on. External metadata therefore gives clients reachable forwarded addresses instead of cluster DNS. [Kafka listener configuration](https://kafka.apache.org/39/security/listener-configuration/).

From the project root on Ubuntu, keep this terminal open:

```bash
bash kafka-access.sh
```

Host CLI and future host notebook clients use `127.0.0.1:19092` as bootstrap. The script starts one loopback-only forward per configured broker and reconnects when a broker pod is replaced. Restart the script after changing broker count. It fails early if a required local port is already occupied. A normal single Service forward cannot cover multiple externally advertised brokers. Pod termination closes a port-forward connection; the helper retries it, but clients still need their normal retry/reconnect behaviour. [kubectl port-forward](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_port-forward/).

To check external discovery from the Ubuntu host without installing Java or Kafka CLI on it, use the same pinned client image with the host network. Run these in another terminal; the client container runs outside Kubernetes:

```bash
KAFKA_CLIENT_IMAGE=$(kubectl -n bigdata get statefulset kafka -o jsonpath='{.spec.template.spec.containers[0].image}')
docker run --rm --network host --memory=768m \
  -e KAFKA_HEAP_OPTS='-Xms128m -Xmx256m' \
  --entrypoint /opt/kafka/bin/kafka-broker-api-versions.sh "$KAFKA_CLIENT_IMAGE" \
  --bootstrap-server 127.0.0.1:19092

docker run --rm --network host --memory=768m \
  -e KAFKA_HEAP_OPTS='-Xms128m -Xmx256m' \
  --entrypoint /opt/kafka/bin/kafka-topics.sh "$KAFKA_CLIENT_IMAGE" \
  --bootstrap-server 127.0.0.1:19092 --list
```

Discovery must show one loopback endpoint per broker and no Kubernetes DNS endpoints. These Docker host-network commands target Ubuntu; laptop clients can instead use their native Kafka library through the SSH tunnel below.

The equivalent manual command for one broker is:

```bash
kubectl -n bigdata port-forward --address=127.0.0.1 pod/kafka-0 19092:9093
# For a second broker, in another terminal:
kubectl -n bigdata port-forward --address=127.0.0.1 pod/kafka-1 19093:9093
```

If the cluster runs on a remote Ubuntu VM, run the helper there. On your laptop, keep an SSH tunnel open using your own account and VM address:

```bash
# One broker
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:19092:127.0.0.1:19092 "${LAB_SSH_USER:?Set LAB_SSH_USER}@${LAB_SSH_HOST:?Set LAB_SSH_HOST}"
# Two brokers: replace the preceding tunnel with this one
ssh -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:19092:127.0.0.1:19092 \
  -L 127.0.0.1:19093:127.0.0.1:19093 "${LAB_SSH_USER:?Set LAB_SSH_USER}@${LAB_SSH_HOST:?Set LAB_SSH_HOST}"
```

Keep the same local port numbers because they appear in Kafka metadata. Laptop clients also bootstrap to `127.0.0.1:19092`. Repeat a tunnel for every additional broker. This is local/SSH-tunnel access, not a direct LAN or public Kafka endpoint. No hosts-file edits are required. Distributed Spark executors and other clients inside Kubernetes must use INTERNAL addresses; loopback points to their own container. Direct cloud/LAN access will require per-broker routable addresses and an appropriate Service exposure design later. Jupyter configuration is outside this change.

Kafka is plaintext without Kafka authentication in this training setup; keep forwards bound to loopback. Do not change only the bootstrap hostname or expose a shared external Service and expect broker discovery to work.

```bash
kubectl -n bigdata logs statefulset/zookeeper
kubectl -n bigdata logs kafka-0 -c kafka
kubectl -n bigdata logs kafka-0 -c wait-for-zookeeper
kubectl -n bigdata describe pod kafka-0
kubectl -n bigdata get events --sort-by=.metadata.creationTimestamp
```

When editing the ConfigMap, restart brokers to regenerate runtime properties: `kubectl -n bigdata rollout restart statefulset/kafka`, then wait for rollout. During abrupt simultaneous broker/ZooKeeper replacement, a broker can briefly retry while its old ZooKeeper session expires; wait for rollout and check the logs. Use `minikube stop -p bigdata` at session end. Preserve both ZooKeeper and broker data; losing ZooKeeper metadata while retaining broker logs can cause cluster-ID conflicts. Old Docker training volumes have not been imported or deleted.
