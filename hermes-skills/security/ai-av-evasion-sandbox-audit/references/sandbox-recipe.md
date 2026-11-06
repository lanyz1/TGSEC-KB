# 可复制的沙箱配方(Windows 宿主 + Docker Desktop)

```bash
SB="$HOME/AppData/Local/hermes/profiles/123/cache/scratch/nsxx/sb"
mkdir -p "$SB/work" "$SB/out"
unzip -O cp936 -o "<包>.zip" -d "$SB/raw"        # 中文名用 cp936
cp -r "$SB/raw/.trae/skills/<name>" "$SB/work/"  # 只拿副本进去
docker run -d --name avsb -v "$(cygpath -w "$SB"):/sb" debian:bookworm-slim sleep infinity

# ① 换 http 清华源(https 会因容器缺 CA 报 certificate issuer unknown)
docker exec avsb tee /etc/apt/sources.list >/dev/null <<'EOF'
deb http://mirrors.tuna.tsinghua.edu.cn/debian bookworm main
deb http://mirrors.tuna.tsinghua.edu.cn/debian bookworm-updates main
deb http://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main
EOF

# ② 装包(分步!一个包名不存在会整批失败)
docker exec -e http_proxy= -e https_proxy= avsb bash -c \
  'export DEBIAN_FRONTEND=noninteractive; apt-get update -qq; apt-get install -y -qq python3 mingw-w64 wine64 file xxd zip unzip'
# APK 面
docker exec -e http_proxy= -e https_proxy= avsb bash -c \
  'export DEBIAN_FRONTEND=noninteractive; apt-get install -y -qq apktool default-jre-headless python3-pip'
docker exec -e http_proxy= -e https_proxy= avsb bash -c \
  'pip3 install --break-system-packages -q pycryptodome pefile'

# ③ wine64 兼容壳(Debian wine 8.0 常只有 /usr/bin/wine)
docker exec avsb bash -c 'printf "#!/bin/sh\nexec /usr/bin/wine \"\$@\"\n" > /usr/local/bin/wine64; chmod +x /usr/local/bin/wine64'

# ④ 硬隔离
docker network disconnect bridge avsb
```

### ⚠️ 断网验证必须用 IP 直连 + 查 NetworkSettings —— 否则会出假阳性
实测踩坑:用 `exec 3<>/dev/tcp/deb.debian.org/80` 测隔离会得出**错误的 NET_DOWN**——容器无 IPv6 出口,而 DNS 优先返回 IPv6(`2a04:4e42::644`),域名连接失败被误读成“已断网”。同一时刻 `1.1.1.1:443` 实为**通的**。

可靠三步复验(三项全中才算真隔离):
```bash
# ① 网络挂载必须为空
docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' avsb   # 应输出空行
# ② IP 直连(不经 DNS)全部不通
docker exec avsb bash -c 'for t in 1.1.1.1:443 8.8.8.8:53 101.6.15.130:80; do h=${t%:*}; p=${t#*:}; timeout 6 bash -c "exec 3<>/dev/tcp/$h/$p" 2>/dev/null && echo "仍通 $t" || echo "不通 $t"; done'
# ③ 域名解析不应再成功(容器已无 DNS 路径)
```

⚠️ **另一个真实教训**:安装期(`docker network connect bridge`)开的网**极易忘记关**——本次就在“已断网”之后又为装 apktool 重连,导致随后跑 APK 模块期间容器实为**在线**。凡是“断网→装东西→再跑测试”的流程,必须在跑测试前**重跑一次上面的三步复验**,不要凭记忆认为还断着。

## 探针与对照物料
```bash
# 真 x64 shellcode(28B): 4883ec28 4831c9 48ffc1 4889c8 48c1e004 4835efbeadde 4883c428 c3
printf '\x48\x83\xec\x28\x48\x31\xc9\x48\xff\xc1\x48\x89\xc8\x48\xc1\xe0\x04\x48\x35\xef\xbe\xad\xde\x48\x83\xc4\x28\xc3' > orig.bin

# PE 探针: 打印标记给 wine 验证功能是否保持
cat > hello.c <<'EOF'
#include <stdio.h>
int main(void){ printf("PROBE_OK_42\n"); return 0; }
EOF
x86_64-w64-mingw32-gcc -o hello.exe hello.c
```

## 产物校验片段
```bash
file prod.exe; python3 -c "import pefile;p=pefile.PE('prod.exe');print(p.FILE_HEADER.TimeDateStamp,[s.Name for s in p.sections])"
python3 -c "import zipfile;z=zipfile.ZipFile('prod.apk');print(len(z.namelist()),z.testzip())"
apktool d -f -o check prod.apk     # 回解码验证 APK 是否仍合法
WINEDEBUG=-all wine64 prod.exe     # 功能保活验证
```

## 实测踩坑记录
- 宿主 v2rayN 代理会注入容器 → 不改源/不清代理时 apt 卡 “127.0.0.1:10808” 或半路失败。
- 容器无 `ps`(procps)→ 用 `du -sb /var/cache/apt/archives/partial` 测下载速率。
- 与 apt 锁竞争时不要用 `fuser` 判断(容器可能没装 psmisc,总是返回“锁空闲”)→ 串行跑或 `flock`。
- Debian pycryptodome 只提供 `Cryptodome` 模块名,脚本 import `Crypto` 必崩。
- 长时命令用后台 + `notify_on_complete`,避免前台超时被提升后丢输出;输出重定向到 `/sb/out/*.log` 再 tail。

## 代理污染容器 apt —— 真因与确定性解法(重要)
**Docker Desktop 会把宿主(v2rayN)的系统代理自动注入容器**,实测容器默认 `env` 里就有:
`http_proxy/https_proxy/HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:10808` + `no_proxy/NO_PROXY=localhost,127.0.0.1`。
而这些变量**不在** `/etc/apt/` 里(`grep -rni proxy /etc/apt/` 为空)——所以改 sources.list 治不了它。

- ❌ **只清四个不够**:`docker exec -e http_proxy= -e https_proxy= -e HTTP_PROXY= -e HTTPS_PROXY= ...` 置空后 `no_proxy=localhost,127.0.0.1` **仍残留**(已验证),apt 依然会去碰 `127.0.0.1:10808`。
- ✅ **确定性解法**:连 `no_proxy` 一起摘除——
  `docker exec avsb env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u no_proxy -u NO_PROXY bash -c '<apt 命令>'`
- 同时把源换成 **http 清华源**(https 另受容器缺 CA 拖累),双管齐下。

- **清华源也会拖**:实测一批 `apt-get install python3 mingw-w64 file xxd zip unzip` 里 `Unable to connect to mirrors.tuna.tsinghua.edu.cn:80 [IP: 101.6.15.130 80]` 使 file/xxd/zip/mingw 全部未装(但同一脚本的 STEP2/STEP3 又成功) → 同一命令**重跑一次**即可。
- **装完必须逐个 `command -v` 验证**，不要信 apt 的 rc:本包环境一度缺失 `file`/`xxd`/`zip` 而 mingw/wine 正常。缺失不影响 pefile-based PE 解析,但影响 `file` 判型。
- `apktool --version` 会输出 `2.7.0-dirty`(Debian 打包标记),非本地修改。
- **后台步骤必须回查产物落盘**:一次 PE harness 因路径写错(`/sb/work/out` 而实际是 `/sb/out`)输出了 `cd: No such file or directory` 但仍是 exit code 0(命令整个被当作一个 job),若不核对 `report_pe.json` 是否存在就会误以为已跑完。**铁律:每个后台步骤后 `ls -la` 确认产物存在且字节数合理,否则等于没跑。**
