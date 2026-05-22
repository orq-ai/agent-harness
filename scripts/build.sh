#!/usr/bin/env bash
# Build the Centaur overlay image for orq-ai/agent-harness.
#
# Images are tagged by git commit SHA so every deploy is deterministic and
# verifiable -- never rely on :latest for what is actually running.
#
# Usage:
#   scripts/build.sh           build agent-harness:sha-<sha> locally
#   scripts/build.sh --push    also publish to ghcr.io/orq-ai/agent-harness
set -euo pipefail

cd "$(dirname "$0")/.."

image="agent-harness"
registry="ghcr.io/orq-ai/agent-harness"

sha="$(git rev-parse --short HEAD)"
suffix=""
git diff --quiet HEAD 2>/dev/null || suffix="-dirty"
tag="sha-${sha}${suffix}"

echo "Building ${image}:${tag} ..."
docker build -t "${image}:${tag}" -t "${image}:latest" .
echo "Built ${image}:${tag}"

if [[ "${1:-}" == "--push" ]]; then
  docker tag "${image}:${tag}" "${registry}:${tag}"
  docker tag "${image}:${tag}" "${registry}:latest"
  docker push "${registry}:${tag}"
  docker push "${registry}:latest"
  echo "Published ${registry}:${tag}"
fi

cat <<EOF

Next: point the Centaur chart at this build --
  contrib/chart/values.dev.yaml:
    overlay:
      image:
        repository: ${image}
        tag: ${tag}
  then: just deploy
EOF
