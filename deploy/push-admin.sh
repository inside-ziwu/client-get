#!/usr/bin/env bash
set -euo pipefail

# ── 配置 ────────────────────────────────────────────────────────────────────
REGISTRY="crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com"
REPO="lay_inside/clientget-admin"
API_URL="https://api.xinanpcb.com"
DOCKERFILE="Dockerfile.admin"
PLATFORM="linux/amd64"
REV_FILE="$(dirname "$0")/.admin-rev"   # 记录当天已推次数
MODE="${1:---load}"

if [[ "${MODE}" != "--load" && "${MODE}" != "--push" ]]; then
  echo "用法: bash deploy/push-admin.sh [--load|--push]"
  echo "  --load  本地构建 amd64 镜像，不推送（默认）"
  echo "  --push  构建并推送到阿里云 ACR"
  exit 1
fi

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

if [[ -n "${REV:-}" ]]; then
  NEXT_REV="${REV}"
elif [[ "$SAVED_DATE" == "$TODAY" ]]; then
  NEXT_REV=$((SAVED_REV + 1))
else
  NEXT_REV=1
fi

if [[ -n "${TAG:-}" ]]; then
  :
else
  TAG="${TODAY}-r${NEXT_REV}"
fi

FULL_IMAGE="${REGISTRY}/${REPO}:${TAG}"

echo "▶ 构建目标: ${FULL_IMAGE}"
echo "▶ 平台: ${PLATFORM}"
echo "▶ API: ${API_URL}"
echo "▶ 模式: ${MODE}"
echo ""

# ── 构建 / 推送 ───────────────────────────────────────────────────────────────
cd "$(dirname "$0")/.."

docker buildx build \
  --platform "${PLATFORM}" \
  --build-arg NEXT_PUBLIC_ADMIN_API_BASE_URL="${API_URL}" \
  -f "${DOCKERFILE}" \
  -t "${FULL_IMAGE}" \
  "${MODE}" \
  .

echo ""
if [[ "${MODE}" == "--push" ]]; then
  # 只有真实推送才递增发布计数；本地验证不占用 release rev。
  if [[ "${TAG}" =~ ^([0-9]{4}\.[0-9]{2}\.[0-9]{2})-r([0-9]+)$ ]]; then
    echo "${BASH_REMATCH[1]}:${BASH_REMATCH[2]}" > "$REV_FILE"
  fi

  echo "✅ 推送完成: ${FULL_IMAGE}"
  echo ""
  echo "Sealos 更新镜像 tag 为:"
  echo "  ${FULL_IMAGE}"
else
  echo "✅ 本地镜像构建完成: ${FULL_IMAGE}"
  echo ""
  echo "推送到阿里云 ACR 时运行:"
  echo "  TAG=${TAG} bash deploy/push-admin.sh --push"
fi
