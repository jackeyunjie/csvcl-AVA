#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# obsidian-project-wiki — 知识库体检工具
# 用法：bash check.sh [vault-path]
# 默认 vault-path: docs/project-wiki
# ============================================================================

# ---- 颜色 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

VAULT_DIR="${1:-docs/project-wiki}"
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

pass() { ((PASS_COUNT++)) || true; echo -e "  ${GREEN}✓ PASS${NC}  $1"; }
warn() { ((WARN_COUNT++)) || true; echo -e "  ${YELLOW}⚠ WARN${NC}  $1"; }
fail() { ((FAIL_COUNT++)) || true; echo -e "  ${RED}✗ FAIL${NC}  $1"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Obsidian Project Wiki — 知识库体检        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Vault 路径：${BOLD}${VAULT_DIR}${NC}"
echo ""

# ---- 0. 检查 vault 目录是否存在 ----
echo -e "${BOLD}[1/7] 目录存在性${NC}"
if [[ ! -d "$VAULT_DIR" ]]; then
  fail "Vault 目录不存在：${VAULT_DIR}"
  echo ""
  echo -e "  ${YELLOW}提示：运行 install.sh 初始化项目知识库${NC}"
  exit 1
fi
pass "Vault 目录存在"

# ---- 1. 检查核心目录结构 ----
echo ""
echo -e "${BOLD}[2/7] 核心目录结构${NC}"

REQUIRED_DIRS=(
  "raw/meetings"
  "raw/requirements"
  "raw/research"
  "raw/incidents"
  "raw/conversations"
  "wiki/decisions"
  "wiki/runbooks"
  "wiki/architecture"
  "wiki/conventions"
  "wiki/patterns"
  "wiki/onboarding"
)

MISSING_DIRS=()
for dir in "${REQUIRED_DIRS[@]}"; do
  if [[ ! -d "${VAULT_DIR}/${dir}" ]]; then
    MISSING_DIRS+=("$dir")
  fi
done

if [[ ${#MISSING_DIRS[@]} -eq 0 ]]; then
  pass "所有核心目录均存在（${#REQUIRED_DIRS[@]} 个）"
else
  warn "缺失 ${#MISSING_DIRS[@]} 个目录：${MISSING_DIRS[*]}"
  echo -e "         运行 install.sh 可自动补全"
fi

# ---- 2. 检查 AGENTS.md ----
echo ""
echo -e "${BOLD}[3/7] Agent 约定文件${NC}"

if [[ -f "${VAULT_DIR}/AGENTS.md" ]]; then
  AGENTS_SIZE=$(wc -c < "${VAULT_DIR}/AGENTS.md" | tr -d ' ')
  if [[ "$AGENTS_SIZE" -lt 50 ]]; then
    warn "AGENTS.md 存在但内容过少（${AGENTS_SIZE} 字节），可能尚未填写"
  else
    pass "AGENTS.md 存在且已填写（${AGENTS_SIZE} 字节）"
  fi
else
  fail "AGENTS.md 不存在 — Agent 将无法遵守知识分层约定"
fi

# ---- 3. 文件统计 ----
echo ""
echo -e "${BOLD}[4/7] 文件统计${NC}"

RAW_COUNT=$(find "${VAULT_DIR}/raw" -name '*.md' -type f 2>/dev/null | wc -l | tr -d ' ')
WIKI_COUNT=$(find "${VAULT_DIR}/wiki" -name '*.md' -type f 2>/dev/null | wc -l | tr -d ' ')

echo -e "  raw/  文件数：${BOLD}${RAW_COUNT}${NC}"
echo -e "  wiki/ 文件数：${BOLD}${WIKI_COUNT}${NC}"

if [[ "$RAW_COUNT" -eq 0 && "$WIKI_COUNT" -eq 0 ]]; then
  warn "知识库为空，尚未放入任何资料"
elif [[ "$RAW_COUNT" -gt 0 && "$WIKI_COUNT" -eq 0 ]]; then
  warn "raw/ 有 ${RAW_COUNT} 份资料但 wiki/ 为空 — 尚未开始整理"
elif [[ "$WIKI_COUNT" -gt 0 ]]; then
  pass "已有 ${WIKI_COUNT} 份 wiki 知识页"
fi

# ---- 4. 过期文件检测（>90 天未更新） ----
echo ""
echo -e "${BOLD}[5/7] 过期文件（>90 天未更新）${NC}"

STALE_RAW=$(find "${VAULT_DIR}/raw" -name '*.md' -type f -mtime +90 2>/dev/null | wc -l | tr -d ' ')
STALE_WIKI=$(find "${VAULT_DIR}/wiki" -name '*.md' -type f -mtime +90 2>/dev/null | wc -l | tr -d ' ')

if [[ "$STALE_RAW" -gt 0 ]]; then
  echo -e "  ${YELLOW}raw/ 中有 ${STALE_RAW} 个文件超过 90 天未更新：${NC}"
  find "${VAULT_DIR}/raw" -name '*.md' -type f -mtime +90 2>/dev/null | head -10 | while read -r f; do
    echo -e "    - $(basename "$f")"
  done
  echo -e "    建议：归档到 raw/archived/ 或重新整理入 wiki/"
else
  pass "raw/ 无过期文件"
fi

if [[ "$STALE_WIKI" -gt 0 ]]; then
  echo -e "  ${YELLOW}wiki/ 中有 ${STALE_WIKI} 个文件超过 90 天未更新：${NC}"
  find "${VAULT_DIR}/wiki" -name '*.md' -type f -mtime +90 2>/dev/null | head -10 | while read -r f; do
    echo -e "    - $(basename "$f")"
  done
  echo -e "    建议：检查内容是否仍然准确"
else
  pass "wiki/ 无过期文件"
fi

# ---- 5. 孤立页面检测（无 [[ 链接） ----
echo ""
echo -e "${BOLD}[6/7] 孤立页面（无 [[ 双向链接）${NC}"

ORPHAN_COUNT=0
ORPHAN_FILES=()

while IFS= read -r file; do
  # 跳过 .gitkeep
  [[ "$(basename "$file")" == ".gitkeep" ]] && continue
  if ! grep -q '\[\[' "$file" 2>/dev/null; then
    ORPHAN_FILES+=("$(basename "$file")")
    ((ORPHAN_COUNT++)) || true
  fi
done < <(find "${VAULT_DIR}/wiki" -name '*.md' -type f 2>/dev/null)

if [[ "$ORPHAN_COUNT" -eq 0 ]]; then
  pass "wiki/ 中所有页面均包含双向链接"
elif [[ "$ORPHAN_COUNT" -le 3 ]]; then
  warn "${ORPHAN_COUNT} 个 wiki 页面缺少双向链接："
  for f in "${ORPHAN_FILES[@]}"; do
    echo -e "    - ${f}"
  done
  echo -e "    建议：为这些页面添加 [[...]] 链接以增强知识网络"
else
  warn "${ORPHAN_COUNT} 个 wiki 页面缺少双向链接（显示前 5 个）："
  for f in "${ORPHAN_FILES[@]:0:5}"; do
    echo -e "    - ${f}"
  done
  echo -e "    建议：运行 Prompt 模板 3（月度体检）获取完整列表"
fi

# ---- 6. 重复文件名检测 ----
echo ""
echo -e "${BOLD}[7/7] 重复文件名${NC}"

DUPLICATES=$(find "${VAULT_DIR}" -name '*.md' -type f -exec basename {} \; 2>/dev/null | sort | uniq -d)

if [[ -z "$DUPLICATES" ]]; then
  pass "无重复文件名"
else
  warn "发现重复文件名："
  echo "$DUPLICATES" | while read -r name; do
    echo -e "    - ${name}"
    find "${VAULT_DIR}" -name "$name" -type f 2>/dev/null | while read -r path; do
      echo -e "      → ${path}"
    done
  done
  echo -e "    建议：合并或重命名以避免混淆"
fi

# ---- 汇总报告 ----
echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "${BOLD}  体检报告${NC}"
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}通过：${PASS_COUNT}${NC}"
echo -e "  ${YELLOW}警告：${WARN_COUNT}${NC}"
echo -e "  ${RED}失败：${FAIL_COUNT}${NC}"
echo ""

TOTAL_ISSUES=$((WARN_COUNT + FAIL_COUNT))
if [[ "$FAIL_COUNT" -gt 0 ]]; then
  echo -e "  ${RED}${BOLD}状态：需要修复${NC}"
  echo -e "  请优先处理失败项，然后重新运行本脚本。"
elif [[ "$WARN_COUNT" -gt 0 ]]; then
  echo -e "  ${YELLOW}${BOLD}状态：基本健康，有改进空间${NC}"
  echo -e "  建议逐项处理警告，提升知识库质量。"
else
  echo -e "  ${GREEN}${BOLD}状态：知识库健康${NC}"
  echo -e "  继续保持！记得每月运行一次体检。"
fi
echo ""
