#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
mkdir -p .state user_notebooks
# This marker distinguishes the real host share from an empty node directory.
[[ -f .training-workspace ]] || printf 'dataeng-training-workspace\n' > .training-workspace
# Carry 9p over the node's existing SSH endpoint. Both listeners bind loopback;
# no inbound host firewall exception or public file-sharing port is needed.
node_ssh_port=$(docker inspect bigdata | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["NetworkSettings"]["Ports"]["22/tcp"][0]["HostPort"])')
ssh -i "$HOME/.minikube/machines/bigdata/id_rsa" -p "$node_ssh_port" \
  -o BatchMode=yes -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$(pwd)/.state/minikube-known-hosts" \
  -N -R 127.0.0.1:39090:127.0.0.1:39090 docker@127.0.0.1 &
tunnel_pid=$!
mount_pid=''
cleanup() { kill "$tunnel_pid" 2>/dev/null || true; [[ -z "$mount_pid" ]] || kill "$mount_pid" 2>/dev/null || true; wait || true; }
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
sleep 1
kill -0 "$tunnel_pid"
minikube -p bigdata mount --ip=127.0.0.1 --port=39090 --uid=1000 --gid=1000 "$(pwd):/course-workspace" & mount_pid=$!
# End both processes if either the SSH tunnel or mount exits.
wait -n "$tunnel_pid" "$mount_pid"
