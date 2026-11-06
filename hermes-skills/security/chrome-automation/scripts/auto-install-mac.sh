#!/bin/bash
# 已停用：不要往 ~/.claude 装 Rust/pnpm/agent-browser。
echo "[stop] 测绘引擎不跑这套安装。"
echo "      抓页: python3 tools/scrapling/bin/scrapling_fetch.py <url> --mode browser --case <案卷>"
echo "      有头: bash .cursor/skills/chrome-automation/scripts/start-chrome-mac.sh"
echo "      会员: python3 tools/ops/session_pipeline.py --domain … --input cookies.json --case …"
exit 1
