#!/usr/bin/env bash
# Firebase デプロイスクリプト
# UIビルド → firebase deploy → ベクトルインデックス確認 を自動化
#
# 使い方:
#   bash scripts/deploy.sh              # 全体デプロイ
#   bash scripts/deploy.sh hosting      # Hosting のみ
#   bash scripts/deploy.sh functions    # Functions のみ
#   bash scripts/deploy.sh firestore    # Firestore インデックスのみ
#   bash scripts/deploy.sh --skip-build # UIビルドをスキップ

set -euo pipefail
cd "$(dirname "$0")/.."

TARGET=""
SKIP_BUILD=false

for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=true ;;
    hosting|functions|firestore) TARGET="$arg" ;;
    *) echo "Unknown argument: $arg"; echo "Usage: bash scripts/deploy.sh [hosting|functions|firestore] [--skip-build]"; exit 1 ;;
  esac
done

# --- 1. フロントエンドビルド ---
if [ "$SKIP_BUILD" = false ]; then
  echo "=== Building frontend ==="
  (cd ui && npm run build)
  echo ""
fi

# --- 2. デプロイ ---
echo "=== Deploying to Firebase ==="
if [ -n "$TARGET" ]; then
  echo "Target: --only $TARGET"
  firebase deploy --only "$TARGET"
else
  echo "Target: all (hosting + functions + firestore)"
  # --force は絶対に使わない（ベクトルインデックスが削除される）
  firebase deploy
fi

echo ""
echo "=== Deploy complete ==="

# --- 3. ベクトルインデックス確認（全体デプロイ or firestore デプロイ時） ---
if [ -z "$TARGET" ] || [ "$TARGET" = "firestore" ]; then
  echo ""
  echo "=== Checking vector index status ==="
  PROJECT=$(grep -oP 'GOOGLE_CLOUD_PROJECT=\K.*' .env.local 2>/dev/null || echo "poc-rag-490804")
  gcloud firestore indexes composite list \
    --project="$PROJECT" \
    --database="(default)" \
    --format="table(name.basename(),collectionGroup,state)" 2>/dev/null \
    || echo "[WARN] gcloud command failed. Check vector index manually."
fi
