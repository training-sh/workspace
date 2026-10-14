# UI portal verification

Verified on 2026-10-14 against context `bigdata`, with the applications running
inside Kubernetes and browser ports forwarded on the host.

The final `expose-uis.py` passed two consecutive complete runs. Each run started
21 forwards, checked 20 HTTP endpoints, authenticated through the Console proxy
to Polaris, listed the `training` catalog, read the Iceberg REST configuration,
and authenticated to Grafana. Each run stopped its own child processes and
confirmed that all 21 host listeners were closed. A separate occupied-port
check confirmed that an existing listener was reported and left running.

The Spark application port was forwarded but excluded from HTTP checks because
there was no active Spark context. SeaweedFS Volume returned HTTP 400 at `/`,
as its component endpoint did in the internal inspection. All other 19 checked
browser endpoints returned HTTP 200, including redirects to their normal pages.
Adminer, Trino and Marquez were not deployed; the script reported them as such.

Headlamp's `workspace-ui` account passed two independent Pod operation checks:
create a temporary Pod, wait for readiness, read logs, execute `hostname`, and
delete the Pod. Both runs also verified denial of Pod deletion in `kube-system`
and direct Secret reads in `bigdata`. No test Pods were retained.
Headlamp also accepted this account's token in Chromium and rendered the live
`bigdata` Pod list, including `jupyter-0`.

Polaris Console was built from official Apache source revision
`db1f8ea9a52feeb845278a677730f15dddb85ff6` and exercised against Polaris 1.7.0.
Two Chromium logins rendered the `training` catalog successfully, without
JavaScript page errors. This verifies login and catalog listing, not every
administration feature of the Console.

SeaweedFS Admin also passed two fresh Chromium sessions using the workshop
username and password. The tested exposure script SHA-256 is
`dab755c73cdf3b49a088b611f2b2e21053af834ad402797df8e5a7a5aed95a71`.

The first forwarding check found that NodeManager bound its web service only
to the Pod IP. `hadoop/yarn.yaml` now passes
`-Dyarn.nodemanager.bind-host=0.0.0.0`, and the rollout and both final checks
succeeded. A rapid-restart check also led to using `SO_REUSEADDR` during the
Unix port availability probe so TIME_WAIT connections do not cause false
occupied-port reports. Active listeners still cause the port to be skipped.

The tested forwards were restarted after validation and left running on
`127.0.0.1`. They are a host process, not a system service; restart the script
after a host reboot. Instructions and credentials are in [UI_ACCESS.md](../UI_ACCESS.md).
