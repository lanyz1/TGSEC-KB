#!/bin/bash
# gate_runtime.sh —— 本地 Web 工程「一条命令」运行期闸门
#
# 为什么需要：`npm run build` 绿 ≠ 工程能跑（前端重建产物已多次实证）。把每次迭代的固定动作固化，
#   避免手工链条（长内联命令被拦、后台进程丢 stdout、Chrome 实例互相干扰）。
# 用法:  bash gate_runtime.sh <工程目录> [端口] [启动路径]
#        bash gate_runtime.sh D:/work/myapp 9231 "/"
# 前置:  同目录的 navwatch_cdp.js（本 skill scripts/）；工目录里有 npm run build 与 vite preview
# 环境:  WS_PATH 指向装了 ws 的独立 scratch 工程（Node 22+ 可省，navwatch 会回退全局 WebSocket）
# 输出:  build 退出码 / 预览可达性 / 重载请求数 / 已提交导航数 / 崩溃 / 异常（可选 DOM 读数）
set -u
APP="${1:?用法: gate_runtime.sh <工程目录> [端口] [启动路径]}"
PORT="${2:-9231}"
APPPATH="${3:-/}"
J="$(cd "$(dirname "$0")" && pwd)"
LOG="${TMPDIR:-/tmp}/gate_runtime"; mkdir -p "$LOG"
PORT_PREVIEW=4173

# ⓪ 只清理本任务的历史无头实例（按 --remote-debugging-port 识别，绝不 taskkill 全部 chrome）
powershell.exe -NoProfile -Command "\$n=@(Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'chrome.exe' -and \$_.CommandLine -like '*--remote-debugging-port*' }); \$n | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }; 'killed=' + \$n.Count" 2>&1 | tail -1

# ① 构建
echo "=== ① build ==="
(cd "$APP" && npm run build > "$LOG/build.txt" 2>&1); B=$?
echo "build exit=$B  $(grep -E '^✓ built in|built in [0-9]' "$LOG/build.txt" | tail -1)"
if [ $B -ne 0 ]; then echo "★ build 失败，尾部："; tail -12 "$LOG/build.txt"; exit 1; fi

# ② 预览服务探活（不在就自己拉）
echo "=== ② preview 探活 :$PORT_PREVIEW ==="
PV=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:$PORT_PREVIEW/")
echo "preview=$PV"
if [ "$PV" != "200" ]; then
  (cd "$APP" && powershell.exe -NoProfile -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npx vite preview --port $PORT_PREVIEW --strictPort' -WorkingDirectory '$(cygpath -w "$APP" 2>/dev/null || echo "$APP")" -WindowStyle Hidden" >/dev/null 2>&1)
  for i in 1 2 3 4 5 6 7; do sleep 2; PV=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:$PORT_PREVIEW/"); [ "$PV" = "200" ] && break; done
  echo "preview(重试)=$PV"
fi

# ③ Chrome 探活（Start-Process 脱离式拉起；nohup & 会随脚本退出被杀）
echo "=== ③ Chrome 探活 :$PORT ==="
V=$(curl -s --max-time 4 "http://127.0.0.1:$PORT/json/version" | head -c 40)
if [ -z "$V" ]; then
  powershell.exe -NoProfile -Command "Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--headless=new','--disable-gpu','--no-sandbox','--remote-debugging-port=$PORT','--user-data-dir=$LOG/cdp$PORT','about:blank' -WindowStyle Hidden" >/dev/null 2>&1
  for i in 1 2 3 4 5 6 7; do sleep 2; V=$(curl -s --max-time 4 "http://127.0.0.1:$PORT/json/version" | head -c 40); [ -n "$V" ] && break; done
fi
echo "chrome=${V:-★无响应}"

# ④ 导航时间线：重载风暴计数（先于 DOM 读数 —— 风暴中 DOM/evaluate 读数全是噪声）
echo "=== ④ 导航时间线（重载风暴判定）==="
WS_PATH="${WS_PATH:-}" timeout 90 node "$J/navwatch_cdp.js" --port "$PORT" --nav "http://127.0.0.1:$PORT_PREVIEW$APPPATH" --wait 12000 > "$LOG/nav.txt" 2>&1
echo "重载请求(reason=reload)=$(grep -c 'reason= reload' "$LOG/nav.txt")  frameNavigated=$(grep -c 'frameNavigated' "$LOG/nav.txt")  loadEvent=$(grep -c 'loadEventFired' "$LOG/nav.txt")  崩溃=$(grep -c 'targetCrashed' "$LOG/nav.txt")  异常=$(grep -c '\[EXC\]' "$LOG/nav.txt")"
grep -E 'targetInfoChanged|frameNavigated|\[EXC\]|log\.error|★' "$LOG/nav.txt" | head -8 | sed 's/^/    /'
tail -6 "$LOG/nav.txt" | sed 's/^/    /'

# ⑤ DOM / 异常读数（可选：同目录有 evaluate_cdp.js 就跑）
echo "=== ⑤ DOM / 异常 ==="
if [ -f "$J/evaluate_cdp.js" ]; then
  WS_PATH="${WS_PATH:-}" timeout 60 node "$J/evaluate_cdp.js" "JSON.stringify({app:(document.querySelector('#app')||{}).innerHTML?.length||0,title:document.title,text:(document.body.innerText||'').replace(/\\s+/g,' ').slice(0,300),imgs:[...document.images].filter(i=>!i.currentSrc).length})" --port "$PORT" --ms 5000 2>&1 | tail -3 | sed 's/^/    /'
else
  echo "    （无 evaluate_cdp.js，跳过；骨架读数用 navwatch 的 frameNavigated/targetInfoChanged 判定）"
fi

echo
echo "=== 汇总 ==="
echo "build=$B  preview=$PV  重载=$(grep -c 'reason= reload' "$LOG/nav.txt")  日志=$LOG"
[ "$(grep -c 'reason= reload' "$LOG/nav.txt")" -ge 3 ] && echo "★★ 闸门不通过：启动期重载风暴，先修导航源再做其他验证"
