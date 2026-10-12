# SeaweedFS module

Run commands from `workspace/`. Apply the namespace and lab Secret first.

`seaweedfs.yaml` contains one mini-mode StatefulSet, a 10 GiB PVC and a Service exposing S3/admin and the internal ports used by mini. The supplied image is fixed to its SeaweedFS 4.47 digest. Mini combines master, volume server, filer, S3 and admin in one process. This keeps the first lab small; it is not a distributed or replicated object store.

The StatefulSet advertises `seaweedfs` and binds to all pod interfaces. The startup bucket is `warehouse`. AWS keys configure S3 authentication. Explicit admin user/password flags enable authenticated admin access; do not assume that S3 credentials alone enable admin login. Authentication flags use the shared Secret values.

```bash
kubectl apply -f seaweedfs/seaweedfs.yaml
kubectl -n bigdata rollout status statefulset/seaweedfs --timeout=600s
kubectl -n bigdata logs statefulset/seaweedfs
kubectl -n bigdata port-forward service/seaweedfs 9001:8333 9002:23646
```

Use S3 endpoint localhost:9001, region us-east-1, access key team and secret team1234. The browser admin UI at localhost:9002 uses team/team1234. In-cluster S3 clients use `http://seaweedfs.bigdata.svc.cluster.local:8333` and path-style access.

Root `bash validations/verify.sh` checks a signed upload/download and rejects a bad secret. TCP readiness confirms the S3 listener only; it does not replace the authenticated check. Mini stores all data under `/data` on the PVC. Stop/start preserves it; deleting the PVC or profile can destroy it. S3 object backups are documented in the root README. [SeaweedFS mini documentation](https://github.com/seaweedfs/seaweedfs/wiki/Getting-Started-with-weed-mini).
