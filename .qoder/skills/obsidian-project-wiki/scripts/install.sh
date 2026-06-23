#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# obsidian-project-wiki — 一键初始化工具
# 用法：
#   bash install.sh --project-name <name> [--target <path>]
#   bash install.sh --global
# ============================================================================

# ---- 颜色 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ---- 默认值 ----
PROJECT_NAME=""
TARGET_DIR=""
GLOBAL_MODE=false

# ---- 定位本脚本所在目录（即 Skill 根目录） ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
TEMPLATES_DIR="${SCRIPT_DIR}/templates"

# ---- 参数解析 ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-name)
      PROJECT_NAME="$2"
      shift 2
      ;;
    --target)
      TARGET_DIR="$2"
      shift 2
      ;;
    --global)
      GLOBAL_MODE=true
      shift
      ;;
    -h|--help)
      echo "用法："
      echo "  bash install.sh --project-name <name> [--target <path>]"
      echo "  bash install.sh --global"
      echo ""
      echo "选项："
      echo "  --project-name <name>  项目名称，用于填充模板中的 {project-name}"
      echo "  --target <path>        目标目录（默认：当前目录下的 docs/project-wiki）"
      echo "  --global               将 Skill 安装到 ~/.qoder/skills/obsidian-project-wiki"
      echo "  -h, --help             显示帮助信息"
      exit 0
      ;;
    *)
      echo -e "${RED}未知参数: $1${NC}"
      echo "使用 --help 查看帮助信息"
      exit 1
      ;;
  esac
done

# ---- 全局模式 ----
if [[ "$GLOBAL_MODE" == true ]]; then
  GLOBAL_DIR="${HOME}/.qoder/skills/obsidian-project-wiki"
  echo -e "${CYAN}[全局安装]${NC} 将 Skill 安装到 ${GLOBAL_DIR}"
  mkdir -p "$GLOBAL_DIR"
  # 复制 SKILL.md、README.md、templates/、scripts/
  cp -r "${SCRIPT_DIR}/SKILL.md" "$GLOBAL_DIR/"
  cp -r "${SCRIPT_DIR}/README.md" "$GLOBAL_DIR/"
  cp -r "${SCRIPT_DIR}/templates" "$GLOBAL_DIR/"
  cp -r "${SCRIPT_DIR}/scripts" "$GLOBAL_DIR/"
  cp -f "${SCRIPT_DIR}/LICENSE" "$GLOBAL_DIR/" 2>/dev/null || true
  cp -f "${SCRIPT_DIR}/_meta.json" "$GLOBAL_DIR/" 2>/dev/null || true
  echo -e "${GREEN}✓${NC} Skill 已安装到 ${GLOBAL_DIR}"
  echo ""
  echo -e "${BOLD}下一步：${NC}"
  echo "  在任意项目中运行："
  echo "  bash ${GLOBAL_DIR}/scripts/install.sh --project-name <项目名>"
  exit 0
fi

# ---- 项目模式（默认） ----

# 如果未指定项目名，尝试从 git remote 推断
if [[ -z "$PROJECT_NAME" ]]; then
  if command -v git &>/dev/null && git rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ -n "$REMOTE_URL" ]]; then
      PROJECT_NAME=$(basename "$REMOTE_URL" .git)
    fi
  fi
fi

# 仍未获取到则使用目录名
if [[ -z "$PROJECT_NAME" ]]; then
  PROJECT_NAME=$(basename "$(pwd)")
fi

# 默认目标目录
if [[ -z "$TARGET_DIR" ]]; then
  TARGET_DIR="$(pwd)/docs/project-wiki"
fi

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Obsidian Project Wiki — 初始化工具        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  项目名称：${BOLD}${PROJECT_NAME}${NC}"
echo -e "  目标目录：${BOLD}${TARGET_DIR}${NC}"
echo ""

# ---- 创建目录结构 ----
RAW_DIRS=("meetings" "requirements" "research" "incidents" "conversations" "archived")
WIKI_DIRS=("decisions" "runbooks" "architecture" "conventions" "patterns" "onboarding")

echo -e "${YELLOW}→ 创建目录结构...${NC}"

for dir in "${RAW_DIRS[@]}"; do
  mkdir -p "${TARGET_DIR}/raw/${dir}"
  touch "${TARGET_DIR}/raw/${dir}/.gitkeep"
done

for dir in "${WIKI_DIRS[@]}"; do
  mkdir -p "${TARGET_DIR}/wiki/${dir}"
  touch "${TARGET_DIR}/wiki/${dir}/.gitkeep"
done

echo -e "${GREEN}  ✓${NC} raw/ 子目录：${RAW_DIRS[*]}"
echo -e "${GREEN}  ✓${NC} wiki/ 子目录：${WIKI_DIRS[*]}"

# ---- 复制模板 ----
echo -e "${YELLOW}→ 复制模板文件...${NC}"

if [[ -f "${TEMPLATES_DIR}/AGENTS.md" ]]; then
  sed "s/{project-name}/${PROJECT_NAME}/g" "${TEMPLATES_DIR}/AGENTS.md" > "${TARGET_DIR}/AGENTS.md"
  echo -e "${GREEN}  ✓${NC} AGENTS.md（已替换项目名）"
else
  echo -e "${RED}  ✗${NC} 未找到 templates/AGENTS.md，跳过"
fi

if [[ -f "${TEMPLATES_DIR}/README.md" ]]; then
  sed "s/{project-name}/${PROJECT_NAME}/g" "${TEMPLATES_DIR}/README.md" > "${TARGET_DIR}/README.md"
  echo -e "${GREEN}  ✓${NC} README.md（已替换项目名）"
else
  echo -e "${RED}  ✗${NC} 未找到 templates/README.md，跳过"
fi

# ---- 完成 ----
echo ""
echo -e "${GREEN}${BOLD}初始化完成！${NC}"
echo ""
echo -e "${BOLD}下一步操作：${NC}"
echo ""
echo -e "  ${CYAN}1.${NC} 用 Obsidian 打开 vault："
echo -e "     Obsidian → Open folder as vault → ${TARGET_DIR}"
echo ""
echo -e "  ${CYAN}2.${NC} 放入第一份原始资料："
echo -e "     cp your-file.md ${TARGET_DIR}/raw/meetings/"
echo ""
echo -e "  ${CYAN}3.${NC} 让 Agent 整理资料："
echo -e "     请参考 templates/prompts.md 中的标准 Prompt 模板"
echo ""
echo -e "  ${CYAN}4.${NC} 提交到 Git："
echo -e "     git add ${TARGET_DIR} && git commit -m \"feat: init project wiki\""
echo ""
