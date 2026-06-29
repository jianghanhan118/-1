#!/usr/bin/env bash
# 昆仑洞天 v6 — 合包还原脚本
# 用法: bash join.sh
# 会在当前目录生成 kunlun-system.tar.gz

set -e
echo "🔧 正在合包..."
cat kunlun-part-* > kunlun-system.tar.gz
echo "✅ 还原完成: kunlun-system.tar.gz"
ls -lh kunlun-system.tar.gz

echo ""
echo "📦 在新电脑上解包:"
echo "  cd ~"
echo "  tar xzf kunlun-system.tar.gz"
echo ""
echo "  然后再执行:"
echo "  cd ~/kunlun-v6"
echo "  bash bootstrap.sh"
