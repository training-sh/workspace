# Workshop portals

Run these commands on the Kubernetes host, in the workspace root. Python 3 and
kubectl are required. The default context is `bigdata`.

```bash
python3 expose-uis.py --list
python3 expose-uis.py
```

The first command inspects Services and ready endpoints without opening ports.
The second starts forwards and prints each URL after kubectl opens its listener.
Keep it running. Ctrl+C stops its own forwards. Failed forwards retry every five
seconds. Missing Services, unready Pods and occupied host ports are reported;
the script does not deploy workloads or stop existing listeners. Rerun it after
deploying additional components. Logs are in `.state/ui-port-forwards/`.

The default bind address is `127.0.0.1`: use a browser on the host desktop.
To listen on one specific host interface, use `--bind <host-IPv4-address>`.
`--bind 0.0.0.0` listens on all host IPv4 interfaces; other machines then use the
host's reachable address, subject to firewall rules. These are HTTP forwards.

```bash
python3 expose-uis.py --only headlamp polaris-console seaweed-admin jupyter
python3 expose-uis.py --seconds 30 --only headlamp
```

| Portal | Host port | Service port | Login |
|---|---:|---:|---|
| Headlamp | 14466 | 80 | Service account token; command below |
| Polaris Console | 18180 | 8080 | Client ID `root`, client secret `s3cr3t` |
| SeaweedFS Admin | 19002 | 23646 | `team` / `team1234` |
| SeaweedFS Master | 19333 | 9333 | None |
| SeaweedFS Filer | 18889 | 8888 | None |
| SeaweedFS Volume | 19340 | 9340 | Root can return HTTP 400; component endpoint |
| NameNode | 19870 | 9870 | None |
| DataNode | 19864 | 9864 | None |
| YARN ResourceManager | 18088 | 8088 | None |
| YARN NodeManager | 18042 | 8042 | None |
| MapReduce History | 19888 | 19888 | None |
| HiveServer2 status | 10002 | 10002 | None |
| Spark Master | 18080 | 8080 | None |
| Spark Worker | 18081 | 8081 | None |
| Spark application | 14040 | 4040 | Requires active Spark context in Jupyter |
| JupyterLab | 18888 | 8888 | Token `team1234` |
| Airflow | 28080 | 8080 | `team` / `team1234` |
| Grafana | 13000 | 3000 | `team` / `team1234` |
| Prometheus | 19090 | 9090 | None |
| Jaeger | 16686 | 16686 | None |
| Alloy diagnostics | 12345 | 12345 | None |
| Adminer, optional | 18086 | 8080 | Database credentials from lab Secret |
| Trino | 18089 | 8080 | User name, e.g. `team` |
| Marquez lineage | 13001 | 3000 | None |

These are the repository's disposable workshop credentials. Existing clusters
with changed Secrets must use those values instead. The script does not print
passwords, change Secrets, or put tokens in URLs.

## Headlamp

```bash
bash start-components.sh headlamp
kubectl --context=bigdata -n headlamp create token workspace-ui --duration=8h
```

Paste the generated token into Headlamp. No username/password is needed.
The account can view resources across the cluster and manage Pods in namespace
`bigdata`, including logs and terminal access. It can create, edit and delete
Pods there. Controller-owned Pods are recreated after deletion. Editing controller
templates, scaling Deployments/StatefulSets and cluster administration are outside
this account's permissions. The Minikube addon also creates its own identity;
use `workspace-ui` for the permissions described here.

## Polaris Console

```bash
bash start-components.sh polaris-console
```

The first run builds the official Apache `polaris-tools/console` source at
`db1f8ea9a52feeb845278a677730f15dddb85ff6`, then imports the image into Minikube.
It needs Git, Docker and outbound build downloads. The build recipe is in
`polaris/console/`; the Kubernetes resources are in `polaris/console.yaml`.
No third-party console image is used. The frontend proxies `/api/` through its
own Nginx to `http://polaris:8181`; the browser uses the same origin for both
the UI and API. No browser DNS entries or Polaris CORS changes are required.
Credentials are entered at login and are not embedded in frontend assets.
The realm is `POLARIS`, and the scope is `PRINCIPAL_ROLE:ALL`.

## Other components

Airflow, YARN and monitoring use the existing startup commands:

```bash
bash start-monitoring.sh
bash start-components.sh airflow yarn
```

Trino, Marquez and Adminer are listed by the exposure script when deployed;
starting the exposure script does not install them. Polaris REST, S3, database
ports and telemetry ingestion ports are not browser portals and are not forwarded
by this script. Headlamp's addon may also provide a NodePort inside the Minikube
node network; the script provides a consistent host port independently of it.

References: [Headlamp](https://headlamp.dev/docs/latest/),
[Polaris Console source](https://github.com/apache/polaris-tools/tree/db1f8ea9a52feeb845278a677730f15dddb85ff6/console).
