#!/usr/bin/env bash
#
# run.sh — wiki-consolidate-draft-to-stable 的一键执行脚本
#
# SKILL.md 描述了 5 步 SOP；本脚本把**只读扫描 + 人工确认 + 落盘 + 回执**
# 串成交互式命令。是 Wave 9 验证"skill 文档 + runfile"形态的第一个样本。
#
# 用法：
#   skills/wiki-consolidate-draft-to-stable/run.sh              # 只读扫描（dry-run）
#   skills/wiki-consolidate-draft-to-stable/run.sh --apply      # 真升级（会再问一次）
#   skills/wiki-consolidate-draft-to-stable/run.sh --ci         # CI 模式：有 🟢 未升即 exit 2
#
# 不做：
#   - 不自动决定"回执够不够硬核"——那是人工判断（参考 SKILL.md 第 2 步）
#   - 不在升级后自动 commit——用户自己决定
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

MODE="${1:-scan}"

banner() {
    echo ""
    echo "━━━ $1 ━━━"
}

case "$MODE" in
    scan|"")
        banner "Step 1 · 只读扫描 wiki stability"
        python3 tools/wiki_stability.py
        echo ""
        echo "下一步：人工过一遍 🟢 候选（见 SKILL.md 第 2 步），确认后再跑："
        echo "  $0 --apply"
        ;;
    --apply)
        banner "Step 1 · 扫描"
        python3 tools/wiki_stability.py
        echo ""
        read -r -p "已看到上面 🟢 候选，全部确认可升级 stable？(y/N) " ans
        if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
            echo "已取消。"
            exit 1
        fi
        banner "Step 2 · 落盘"
        python3 tools/wiki_stability.py --apply
        echo ""
        banner "Step 3 · 提醒"
        echo "下一步（手动）："
        echo "  1. 在当前 case 的 Curator Log 追加 wiki promoted_to_stable_at 回执"
        echo "  2. 若无对应 case，建 cases/$(date +%F)-consolidation.md"
        echo "  3. 跑 python3 tools/evolve.py --apply 让 INDEX 同步"
        ;;
    --ci)
        # CI 门禁：🟢 候选存在即 fail（逼 curator 看一眼）
        exec python3 tools/wiki_stability.py --strict
        ;;
    --help|-h)
        grep '^#' "$0" | sed 's/^# \?//'
        ;;
    *)
        echo "unknown mode: $MODE" >&2
        echo "用 --help 看用法。" >&2
        exit 1
        ;;
esac
