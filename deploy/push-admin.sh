#!/usr/bin/env bash
set -euo pipefail

# ── 配置 ────────────────────────────────────────────────────────────────────
REGISTRY="crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com"
REPO="lay_inside/clientget-admin"
API_URL="https://api.xinanpcb.com"
DOCKERFILE="Dockerfile.admin"
REV_FILE="$(dirname "$0")/.admin-rev"   # 记录当天已推次数

# ── 生成 tag ─────────────────────────────────────────────────────────────────
TODAY=$(date +%Y.%m.%d)

if [[ -f "$REV_FILE" ]]; then
  SAVED=$(cat "$REV_FILE")
  SAVED_DATE="${SAVED%%:*}"
  SAVED_REV="${SAVED##*:}"
else
  SAVED_DATE=""
  SAVED_REV=0
fi

if [[ "$SAVED_DATE" == "$TODAY" ]]; then
  REV=$((SAVED_REV + 1))
else
  REV=1
fi

TAG="${TODAY}-r${REV}"
FULL_IMAGE="${REGISTRY}/${REPO}:${TAG}"

echo "▶ 构建目标: ${FULL_IMAGE}"
echo "▶ 平台: linux/amd64"
echo "▶ API: ${API_URL}"
echo ""

# ── 构建 + 推送 ───────────────────────────────────────────────────────────────
cd "$(dirname "$0")/.."

docker buildx build \
  --platform linux/amd64 \
  -f "${DOCKERFILE}" \
  --build-arg VITE_API_BASE_URL="${API_URL}" \
  -t "${FULL_IMAGE}" \
  --push \
  .

# ── 写回版本号 ────────────────────────────────────────────────────────────────
echo "${TODAY}:${REV}" > "$REV_FILE"

echo ""
echo "✅ 推送完成: ${FULL_IMAGE}"
echo ""
echo "Sealos 更新镜像 tag 为:"
echo "  ${FULL_IMAGE}"
