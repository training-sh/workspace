#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
revision=db1f8ea9a52feeb845278a677730f15dddb85ff6
source_dir="$PWD/.state/ui-tools/polaris-tools"
mkdir -p .state/ui-tools
if [[ ! -d "$source_dir/.git" ]]; then
  git clone https://github.com/apache/polaris-tools.git "$source_dir"
fi
git -C "$source_dir" fetch origin "$revision"
git -C "$source_dir" checkout --detach "$revision"
docker build -f polaris/console/Dockerfile -t polaris-console:db1f8ea "$source_dir/console"
minikube -p bigdata image load polaris-console:db1f8ea
