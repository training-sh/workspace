# Workshop portals

## Open forwarded links in Chrome on Ubuntu

In GNOME Terminal, right-click a forwarded URL and choose **Open Link**.
If the browser does not open, run the following in a second terminal as your
normal desktop user, while keeping `expose-uis.py` running:

```bash
# Set Chrome as the default browser and verify the setting.
xdg-settings set default-web-browser google-chrome.desktop
xdg-settings get default-web-browser

# Test a forwarded URL (Jupyter in this example).
xdg-open http://127.0.0.1:18888/

# If opening through the desktop fails, try Chrome directly and check its errors.
google-chrome http://127.0.0.1:18888/
```

### GNOME Terminal on XFCE: Open Link does nothing

If `xdg-open` works but the terminal's **Open Link** does nothing, test the
GNOME application handler in a second terminal:

```bash
gio open http://127.0.0.1:18888/
```

In our XFCE session, this tried to launch Snap Firefox and printed an error
ending with `is not a snap cgroup for tag snap.firefox.firefox`. Setting Chrome
as the HTTP and HTTPS handler fixed both `gio open` and terminal link clicks:

```bash
gio mime x-scheme-handler/http google-chrome.desktop
gio mime x-scheme-handler/https google-chrome.desktop

# Verify that the default application is google-chrome.desktop, then test.
gio mime x-scheme-handler/http
gio mime x-scheme-handler/https
gio open http://127.0.0.1:18888/
```

Try **right-click → Open Link** again. If needed, test in a new terminal window
while leaving the forwarding terminal running. Run these commands as your normal
desktop user, without `sudo`.

These commands assume an Ubuntu graphical desktop session. In an SSH session,
the remote machine may have no graphical desktop available. Open the URL in your
local browser after forwarding the remote port over SSH; `127.0.0.1` in the
browser always refers to the machine running that browser.

References: [GNOME Terminal links](https://help.gnome.org/gnome-terminal/txt-links.html)
and [Chrome default browser setup](https://chromium.googlesource.com/chromium/src/+/main/docs/linux/dev_build_as_default_browser.md).
See also [GNOME application associations](https://help.gnome.org/system-admin-guide/mime-types-application.html).

## Start UI forwards

Run these commands on the Kubernetes host, in the workspace root. Python 3 and
kubectl are required. The default context is `bigdata`.

```bash
python3 expose-uis.py --help
python3 expose-uis.py --components
python3 expose-uis.py --list
python3 expose-uis.py
```

`--help` shows all options; `--components` lists supported component names and
port mappings without requiring kubectl or a running cluster.
`--list` inspects Services and ready endpoints without opening ports.
Running without these options starts forwards and prints each URL after kubectl opens its listener.
Keep it running. Press Esc or Q to stop its own forwards (no Enter needed).
Ctrl+C is ignored so accidental copy shortcuts leave forwards running.
Without an interactive terminal, use `--seconds` or send SIGTERM to stop.
Failed forwards retry every five
seconds. Missing Services, unready Pods and occupied host ports are reported;
the script does not deploy workloads or stop existing listeners. Rerun it after
deploying additional components. Logs are in `.state/ui-port-forwards/`.
Inspection and forwarding failures show a short status and diagnostic clue instead
of a Python traceback. A failed namespace inspection does not block other namespaces.

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
