#!/usr/bin/env bash
# =============================================================================
# 昆仑洞天 v6 — 一键部署脚本 (bootstrap)
#
# 用法:
#   bash bootstrap.sh
#
# 前提:
#   1. OpenClaw 已安装 (如果没有,脚本会自动装)
#   2. 当前目录是 git clone 下来的仓库根目录
#   3. 新机器需要能访问 GitHub
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════╗"
echo "║     昆仑洞天 v6 — 一键部署                      ║"
echo "║     协同人才·平台·AI                            ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. 检查 OpenClaw ──────────────────────────────────────────────
echo -e "\n${YELLOW}[1/5]${NC} 检查 OpenClaw 环境..."

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw}"
OPENCLAW_CONFIG="${OPENCLAW_CONFIG:-$HOME/.openclaw}"

if command -v openclaw &>/dev/null; then
    echo -e "  ${GREEN}✅${NC} OpenClaw 已安装: $(openclaw --version 2>/dev/null || echo '未知')"
elif [ -f "$OPENCLAW_HOME/openclaw" ]; then
    echo -e "  ${GREEN}✅${NC} OpenClaw 已存在: $OPENCLAW_HOME/openclaw"
else
    echo -e "  ${YELLOW}⚠️  OpenClaw 未安装，开始安装...${NC}"
    curl -fsSL https://openclaw.ai/install.sh | bash
    echo -e "  ${GREEN}✅${NC} OpenClaw 安装完成"
fi

# ── 2. 创建目录结构 ──────────────────────────────────────────────
echo -e "\n${YELLOW}[2/5]${NC} 创建目录结构..."

mkdir -p "$OPENCLAW_CONFIG"/workspace/{memory,brain,scripts,diting,taiyi,tiangong,langhuan,zhenshang,export}
mkdir -p "$OPENCLAW_CONFIG"/agents
mkdir -p "$OPENCLAW_CONFIG"/cron
mkdir -p "$HOME"/core_skills
mkdir -p "$HOME"/.agents/skills
mkdir -p "$HOME"/.meyo

echo -e "  ${GREEN}✅${NC} 目录结构已创建"

# ── 3. 复制工作区 ──────────────────────────────────────────────
echo -e "\n${YELLOW}[3/5]${NC} 复制工作区文件..."
echo -e "  ${YELLOW}→ 正在复制 workspace (技能/代码/记忆)...${NC}"

# 排除不需要复制的内容
rsync -a --progress \
    --exclude='repo/' \
    --exclude='node_modules/' \
    --exclude='tmp/' \
    --exclude='tmp_img/' \
    --exclude='__pycache__/' \
    --exclude='.git/' \
    --exclude='agents/' \
    workspace/ "$OPENCLAFF_CONFIG/workspace/"

echo "  复制完成" 2>/dev/null || cp -r workspace/* "$OPENCLAFC_CONFIG/workspace/" 2>/dev/null || {
    echo -e "  ${YELLOW}→ workspace 较大，改用 tar 传输...${NC}"
    tar cf - --exclude='repo' --exclude='node_modules' --exclude='tmp' \
        --exclude='__pycache__' --exclude='.git' \
        -C "$(dirname "$0")/workspace" . | tar xf - -C "$OPENCLAW_CONFIG/workspace/"
}

echo -e "  ${GREEN}✅${NC} 工作区文件复制完成"

# ── 4. 复制 Agent 定义 ──────────────────────────────────────────
echo -e "\n${YELLOW}[4/5]${NC} 部署 Agent 定义..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -d "$SCRIPT_DIR/agents" ]; then
    for agent_dir in "$SCRIPT_DIR/agents"/*/; do
        agent_name=$(basename "$agent_dir")
        mkdir -p "$OPENCLAW_CONFIG/agents/$agent_name"
        cp "$agent_dir/SYSTEM.md" "$OPENCLAW_CONFIG/agents/$agent_name/SYSTEM.md" 2>/dev/null || true
        echo -e "  ${GREEN}✅${NC} Agent: $agent_name"
    done
fi

# 复制 openclaw.json 配置模板
if [ -f "$SCRIPT_DIR/openclaw.json.tpl" ]; then
    mkdir -p "$OPENCLAW_CONFIG"
    # 不要直接覆盖用户的 openclaw.json，先备份
    if [ -f "$OPENCLAW_CONFIG/openclaw.json" ]; then
        cp "$OPENCLAW_CONFIG/openclaw.json" "$OPENCLAW_CONFIG/openclaw.json.backup.$(date +%Y%m%d%H%M%S)"
        echo -e "  ${YELLOW}⚠️  已有 openclaw.json，已备份${NC}"
    fi
    python3 -c "
import json
with open('$SCRIPT_DIR/openclaw.json.tpl') as f:
    config = json.load(f)
# 自动替换网关地址和令牌
if 'gateway' in config:
    print('  配置模板包含网关设置')
with open('$OPENCLAW_CONFIG/openclaw.json', 'w') as f:
    json.dump(config, f, indent=2)
" 2>/dev/null || cp "$SCRIPT_DIR/openclaw.json.tpl" "$OPENCLAW_CONFIG/openclaw.json"
    echo -e "  ${GREEN}✅${NC} 配置已部署 (openclaw.json)"
fi

# ── 5. 配置引导 ──────────────────────────────────────────────
echo -e "\n${YELLOW}[5/5]${NC} 引导配置 (手动步骤)"

echo ""
echo -e "${CYAN}═════════════════════════════════════════════${NC}"
echo -e "  部署完成！还需要手动配置以下内容："
echo -e "${CYAN}═════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${YELLOW}①${NC} 安装 npm 依赖:"
echo -e "     cd ~/openclaw && npm install"
echo ""
echo -e "  ${YELLOW}②${NC} 配置小艺通道凭据:"
echo -e "     将 .xiaoyienv 文件中的内容配置到新环境"
echo ""
echo -e "  ${YELLOW}③${NC} 配置 API Key/Token:"
echo -e "     openclaw vault set [KEY名] [值]"
echo "     需要设置的包括:"
echo "       - Tavily API Key"
echo "       - 百度地图 Token"
echo "       - 和风天气 Key"
echo "       - 觅游社区 Credential"
echo ""
echo -e "  ${YELLOW}④${NC} 重启网关:"
echo -e "     openclaw gateway restart"
echo ""
echo -e "  ${YELLOW}⑤${NC} 验证安装:"
echo -e "     openclaw status"
echo -e "     openclaw cron list"
echo -e "     openclaw agents list"
echo ""
echo -e "  ${YELLOW}⑥${NC} 如果有MCP云容器，重新注册:"
echo -e "     openclaw mcp set 知识卡云容器 '{\"url\":\"...\"}'"
echo ""

echo -e "${GREEN}✅✅✅ 部署引导完成！${NC}"
echo -e "${CYAN}你只需要完成上面的5个步骤，兔兔就在新电脑上活过来了 🐰${NC}"
