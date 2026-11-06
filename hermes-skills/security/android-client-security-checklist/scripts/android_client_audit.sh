#!/usr/bin/env bash
# =============================================================================
# android_client_audit.sh -- Android 客户端安全评估 12 类一键粗筛
#
# 用法:
#   bash android_client_audit.sh <package>                  # 只跑设备端检查
#   bash android_client_audit.sh <package> /path/app.apk    # 额外跑静态检查
#   bash android_client_audit.sh --static /path/app.apk     # 只跑静态检查（无设备）
#
# 依赖: bash + adb(选) + unzip(选) + grep(必)。无 jadx/apktool 也能跑
#      （静态检查用 grep -a 直接扫 dex/资源的字符串池）。
# 输出: 终端报告 + ../audit_out/<pkg>_<时间戳>/report.txt
#
# 本脚本只做“发现”，不下高危结论：组件导出/内存明文等项的定级口径
# 见 references/06-risk-grading.md（需人工复核）。
# =============================================================================
set -u

RED=$'\033[31m'; YEL=$'\033[33m'; GRN=$'\033[32m'; CYA=$'\033[36m'; RST=$'\033[0m'
mode="full"; PKG=""; APK=""

case "${1:-}" in
  --static) mode=static; APK="${2:-}" ;;
  ''|-h|--help)
    sed -n '2,17p' "$0" | sed -E 's/^# ?//' ; exit 0 ;;
  *) PKG="$1"; APK="${2:-}" ;;
esac

[ "$mode" = static ] && [ -z "$APK" ] && { echo "用法: $0 --static /path/app.apk"; exit 2; }
[ "$mode" = full ] && [ -z "$PKG" ] && { echo "用法: $0 <package> [app.apk]"; exit 2; }

TS=$(date +%Y%m%d_%H%M%S)
OUT="$(cd "$(dirname "$0")" && pwd)/audit_out/${PKG:-static}_${TS}"
mkdir -p "$OUT"
REPORT="$OUT/report.txt"
HITS=0; HIGH=0

say()  { printf '%s\n' "$*" | tee -a "$REPORT"; }
hdr()  { say ""; say "${CYA}============================================================================${RST}"; say "${CYA} $*${RST}"; say "${CYA}============================================================================${RST}"; }
hit()  { # hit <LEVEL> <title> <detail>
  local lv="$1"; shift; HITS=$((HITS+1))
  case "$lv" in 高*) HIGH=$((HIGH+1)); local c="$RED";; 中*) local c="$YEL";; *) local c="$GRN";; esac
  say "${c}[$lv]${RST} $*"
}
ok()   { say "${GRN}[通过]${RST} $*"; }
na()   { say "${YEL}[未验]${RST} $*  （需人工/工具确认，不等于安全）"; }
need_cmd() { command -v "$1" >/dev/null 2>&1; }

say "Android 客户端安全评估 12 类粗筛"
say "时间: $(date '+%F %T')   包名: ${PKG:-<无>}   APK: ${APK:-<无>}   报告: $REPORT"

# =============================================================================
# 一、静态检查（有 APK 时）—— 直接 grep -a 扫 dex/资源的字符串池
# =============================================================================
if [ -n "$APK" ]; then
  hdr "1. 静态代码/资源扫描"
  if [ ! -f "$APK" ]; then
    say "APK 不存在: $APK"
  else
    RAW="$OUT/raw"; mkdir -p "$RAW"
    if need_cmd unzip; then
      unzip -o -q "$APK" -d "$RAW" >/dev/null 2>&1 || say "unzip 失败，回退为直接扫 APK"
    else
      say "无 unzip，直接扫 APK"
    fi
    # 扫描目标：dex + resources.arsc + manifest + assets + lib 名
    SCAN=$(find "$RAW" -maxdepth 2 -type f \( -name '*.dex' -o -name 'AndroidManifest.xml' \
             -o -name 'resources.arsc' -o -name '*.js' -o -name '*.json' \) 2>/dev/null)
    [ -z "$SCAN" ] && SCAN="$APK"

    grepall() { # grepall <ERE> -> 去重后的命中片段（不带路径，最多 8 个）
      local pat="$1"
      # shellcheck disable=SC2086
      grep -a -o -h -E "$pat" $SCAN 2>/dev/null | sort -u | head -8 | tr '\n' '|'
    }
    chk() { # chk <ERE> <等级|信息> <标题>
      local out; out=$(grepall "$1")
      if [ -z "$out" ]; then ok "$3"; return; fi
      if [ "$2" = 信息 ]; then say "${CYA}[登记]${RST} $3  » $out"
      else hit "$2" "$3" " » $out"; fi
    }

    say "[1.1 客户端保护]"
    chk 'android:debuggable="true"|debuggable' 高 "manifest 含 debuggable（需 aapt dump xmltree 确认取值）"
    chk 'allowBackup="true"|allowBackup' 中 "allowBackup 存在（未显式 false ⇒ 可 adb backup）"
    chk 'MODE_WORLD_READABLE|MODE_WORLD_WRITEABLE' 高 "使用全局可读写文件模式"
    chk 'getPackageInfo|GET_SIGNATURES|getSignature' 信息 "有签名/包信息读取调用（若为完整性自校验则属缓解，需读代码判定）"

    say "[1.2 组件与 IPC]"
    chk 'DexClassLoader' 高 "外部动态加载 DEX（核对 dexPath 是否在外部可写目录+有无 Hash 校验）"
    chk 'new ServerSocket|ServerSocket\(' 高 "应用内开 TCP 服务（核对调用者身份校验）"
    chk 'Runtime[.]getRuntime|loadLibrary\(|System[.]load\(|ProcessBuilder' 中 "运行其它可执行程序 / 加载 so（核对参数是否可控）"
    chk 'registerReceiver' 中 "动态注册 Receiver（drozer 查不到，必须读代码）"

    say "[1.3 WebView]"
    chk 'addJavascriptInterface' 高 "WebView JS 桥（targetSdk<19 ⇒ 可反射调 Java RCE）"
    chk 'setSavePassword' 高 "WebView 密码保存（未显式 false ⇒ webview.db 明文）"
    chk 'onReceivedSslError' 高 "重写了 SSL 错误处理（看是否 handler[.]proceed()）"
    chk 'setJavaScriptEnabled' 低 "启用 JS（配合文件域/桥面看风险）"

    say "[1.4 通信与证书]"
    chk 'setDefaultHostnameVerifier|HostnameVerifier|X509TrustManager|ALLOW_ALL_HOSTNAME_VERIFIER' 高 "自定义证书/域名校验（极大可能是恒 true 的空实现）"
    chk 'CertificatePinner|pinning|checkServerTrusted' 中 "证书固定相关（存在≠做对了）"
    chk 'http://' 中 "明文 HTTP 地址（逐个确认是否传敏感数据）"
    chk 'SslErrorHandler|proceed' 高 "SSL 错误继续（proceed 即不校验证书）"

    say "[1.5 弱加密]"
    chk 'DES/ECB|DES/CBC|DESede|DESKeySpec|RC4|getInstance[^)]*DES' 高 "弱对称算法（DES/3DES/RC4）——反编译确认具体用法"
    chk 'ECB' 高 "ECB 模式（同明文同密文）"
    chk 'NoPadding' 高 "RSA/AES 无 Padding"
    chk 'IvParameterSpec' 中 "使用 IV（核对是否硬编码/全零）"
    chk 'SecretKeySpec' 中 "对称密钥（核对是否硬编码常量）"
    chk 'initialize\(512\)|initialize\(1024\)' 高 "RSA 密钥长度不足"

    say "[1.6 存储与敏感信息]"
    chk 'MODE_PRIVATE' 低 "私有模式写文件（正常，仅登记）"
    chk 'getExternalStorageDirectory|/sdcard/|/storage/emulated' 中 "外部存储读写（敏感数据落外部存储即泄）"
    chk 'gesture|pattern_lock|gesturePassword' 中 "手势密码相关字符串（核对本地保存与锁定策略）"

    say "[1.7 第三方 SDK / 本地服务（虫洞类）]"
    chk '40310|6259|7777' 高 "百度 WormHole 虫洞端口常量（本地无鉴权服务，可远程读设备信息/装包）"
    chk 'NanoHTTPD|nanohttpd|ServerSocket' 高 "应用内嵌 HTTP 服务（核对绑定地址与鉴权）"
    chk 'com[.]baidu|com[.]tencent|com[.]umeng|com[.]alipay' 低 "常见第三方 SDK（逐个核版本 CVE）"

    say "[1.8 硬编码凭据/后台路径（接 apk-recon 深挖）]"
    chk 'api[_-]?key|appsecret|access[_-]?key|SecretKey' 中 "疑似硬编码密钥字符串"
    chk '/(admin|manage|operator|backend)/' 中 "疑似后台路径"
    chk '(test|dev|uat|pre|staging)[.]' 中 "疑似测试/预发域名（通常无 WAF，优先打）"

    say ""
    say "静态扫描完成。注：grep 命中 ≠ 漏洞，只看常量存在性；组件导出/取值类结论需 aapt + jadx 复核。"
  fi
fi

if [ "$mode" = static ]; then
  hdr "汇总"
  say "命中项: $HITS （其中标注高危可能的: $HIGH）→ 逐项人工复核后写入报告"
  exit 0
fi

# =============================================================================
# 二、设备端检查（adb）
# =============================================================================
hdr "2. 设备端检查（adb）"
if ! need_cmd adb; then
  na "未找到 adb —— 设备端检查全部跳过"
else
  adb start-server >/dev/null 2>&1 || true
  DEVS=$(adb devices | grep -c $'\tdevice$')
  if [ "$DEVS" -eq 0 ]; then
    na "无已连接设备（adb devices 为空）"
  else
    SU=""
    if adb shell "su -c id" 2>/dev/null | grep -q 'uid=0'; then SU="su -c"; say "${GRN}[info]${RST} 设备有 root，可查私有目录"
    elif adb shell "run-as $PKG id" 2>/dev/null | grep -q 'uid='; then SU="run-as $PKG"; say "${GRN}[info]${RST} 包可 run-as（debuggable）"
    else na "无 root 且不可 run-as —— 存储类检查需手工（拷出数据/备份/脱壳）"; fi

    say "[2.1 包信息与 debuggable/backup]"
    if adb shell pm path "$PKG" 2>/dev/null | grep -q package; then
      say "  路径: $(adb shell pm path "$PKG" | tr -d '\r')"
    else
      say "${YEL}包未安装${RST}: $PKG（先 adb install -r -g app.apk）"
    fi
    FLAGS=$(adb shell dumpsys package "$PKG" 2>/dev/null | grep -m1 -E 'flags=|pkgFlags=' | tr -d '\r')
    [ -n "$FLAGS" ] && say "  $FLAGS"
    if echo "$FLAGS" | grep -q 'DEBUGGABLE'; then hit 高 "debuggable=true（可 jdwp 附加、读写私有目录）"; else ok "未在 flags 中看到 DEBUGGABLE"; fi
    if echo "$FLAGS" | grep -q 'ALLOW_BACKUP'; then hit 中 "ALLOW_BACKUP（adb backup 可拉走数据）"; fi
    if adb shell "run-as $PKG id" 2>/dev/null | grep -q 'uid='; then hit 高 "run-as 成功 ⇒ 可调试，私有目录可读写"; fi

    say "[2.2 权限]"
    adb shell dumpsys package "$PKG" 2>/dev/null | sed -n '/requested permissions/,/install permissions/p' \
      | grep -E 'android[.]permission[.]' | tr -d '\r' | sed 's/^/  /' | tee -a "$REPORT" | head -30
    say "  → 人工比对：申请权限是否大于业务需要（相机/短信/通讯录/位置）"

    say "[2.3 组件导出（drozer 缺失时用 dumpsys 粗筛）]"
    if need_cmd drozer; then
      say "  检测到 drozer，建议手工跑: run app.package.attacksurface $PKG"
    else
      na "无 drozer。备用: adb shell dumpsys package $PKG | grep -A3 -E 'Activity|Service|Receiver|Provider'"
      adb shell dumpsys package "$PKG" 2>/dev/null | grep -cE 'android[.]intent[.]action[.]MAIN' | tr -d '\r' | sed 's/^/  MAIN action 计数: /'
    fi
    say "  逐类验证命令（拷走用）:"
    say "    adb shell am start -n $PKG/<Activity>                 # 免登录直达"
    say "    adb shell am startservice -n $PKG/<Service>"
    say "    adb shell am broadcast -a <ACT> -n $PKG/<Receiver>"
    say "    adb shell content query --uri content://<authority>/<path>"

    say "[2.4 私有目录与存储]"
    if [ -n "$SU" ]; then
      adb shell $SU 'ls -la /data/data/"$PKG"/' 2>/dev/null | tr -d '\r' | sed 's/^/  /' | tee -a "$REPORT" | head -40
      say "  -- 权限位判据: 文件应 -rw-rw---- ; 目录应 drwxrwx--x ; other 位有 r/w 即风险"
      adb shell $SU 'ls -la /data/data/"$PKG"/shared_prefs/ 2>/dev/null' | tr -d '\r' | sed 's/^/  /'
      adb shell $SU 'cat /data/data/"$PKG"/shared_prefs/*.xml 2>/dev/null' > "$OUT/shared_prefs.xml" 2>/dev/null
      if grep -qiE 'passw|pwd|token|session|idcard|phone|bank' "$OUT/shared_prefs.xml" 2>/dev/null; then
        hit 高 "SharedPreferences 出现敏感字段（详见 $OUT/shared_prefs.xml）"
        grep -inE 'passw|pwd|token|session|idcard|phone|bank' "$OUT/shared_prefs.xml" | head -10 | sed 's/^/  /' | tee -a "$REPORT"
      fi
      adb shell $SU 'ls -la /data/data/"$PKG"/databases/ 2>/dev/null' | tr -d '\r' | sed 's/^/  /'
      adb shell $SU 'find /data/data/"$PKG" -name "webview*.db" 2>/dev/null' | tr -d '\r' | sed 's/^/  webview db: /'
      adb shell $SU 'ls -la /sdcard/Android/data/"$PKG"/ 2>/dev/null' | tr -d '\r' | sed 's/^/  外部存储: /'
    fi

    say "[2.5 logcat 敏感信息]"
    adb logcat -d -t 3000 2>/dev/null | grep -iE 'passw|pwd|token|session|cookie|idcard|bankcard' \
      | sort -u | head -15 | tee -a "$REPORT" | sed 's/^/  /' \
      && hit 中 "logcat 出现敏感关键词（确认是否目标 App 打印）" \
      || ok "近 3000 行 logcat 未见敏感关键词"

    say "[2.6 本地监听端口 / 本地服务]"
    PORTS=$(adb shell "netstat -tuanp 2>/dev/null || busybox netstat -tuanp 2>/dev/null" | grep -Ei 'LISTEN|udp' | tr -d '\r')
    if [ -n "$PORTS" ]; then
      say "$PORTS" | sed 's/^/  /' | tee -a "$REPORT" | head -20
      say "  → 若有本应用相关端口，试 adb forward tcp:P tcp:P 后用 curl 打（虫洞类未鉴权服务）"
      hit 中 "设备存在本地监听端口（逐项归属与鉴权）"
    else
      na "netstat 不可用（厂商机常删）——换模拟器复测"
    fi
    if [ -n "$SU" ]; then
      adb shell $SU 'lsof 2>/dev/null | grep -i sock' | tr -d '\r' | sed 's/^/  /' | head -15
    fi

    say "[2.7 输入侧信道]"
    say "  getevent 设备（找带 KEY_ 能力的节点）:"
    adb shell getevent -pl 2>/dev/null | grep -E 'add device|name:|KEY_' | head -20 | tr -d '\r' | sed 's/^/  /'
    say "  键盘劫持/截屏/FLAG_SECURE 无法自动判定 → 手工: 装 IME 记击键 / 连拍 screencap / grep FLAG_SECURE"
    say "  手工连拍:  while true; do adb exec-out screencap -p > shot_$(date +%s).png; sleep 1; done"

    say "[2.8 抓包环境]"
    say "  当前代理: $(adb shell settings get global http_proxy 2>/dev/null | tr -d '\r')"
    say "  设代理:   adb shell settings put global http_proxy <PC_IP>:8080   （清: put global http_proxy :0）"
    say "  非标端口透明代理: adb shell su -c 'iptables -t nat -A OUTPUT -p tcp --dport P -j REDIRECT --to-ports 8123'"
    say "  实时抓包: adb shell \"tcpdump -s 0 -w - | nc -l -p 4444\" + adb forward tcp:4444 tcp:4444 + nc localhost 4444 | wireshark -k -S -i -"
  fi
fi

hdr "汇总"
say "命中项: $HITS （其中标注高危可能: $HIGH）"
say "报告: $REPORT"
say "下一步: 命中项逐项人工复核 → 按 references/06-risk-grading.md 定级 → 填写 6.3 漏项自检清单"
