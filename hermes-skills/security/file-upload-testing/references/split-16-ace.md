## 解析器 ACE 弹药清单（目标替我方文件做解析时用）

当目标处理链会把**攻击者的文件**喂进下列解析器（上传、工单附件、AV 扫描、CI 工具链、逆向分析服务、转码、缩略图），这批就是现成弹药（研究 PoC，本机未复现，**先核版本**）：

| 解析器 | 触发面 | 索引目录（`poc-db/exploitarium/`） |
|---|---|---|
| PHP 8.5.7 | SOAP + StreamBucket | `php857-streambucket-soap-rce-rpoc` |
| libssh2 ×2 | 连我方 SSH 服务端时的协议解析（含 CVE-2026-55200） | `libssh2-cve-2026-55200-poc` / `libssh2-publickey-list-calc-poc` |
| FFmpeg | 视频 RASC/DLTA 解码 | `ffmpeg-rasc-dlta-calc-poc` |
| VLC | VP9 分辨率切换 | `vlc-vp9-reschange-crash-poc` |
| Pillow | ImageCms OOB | `pillow-imagecms-output-mode-oob-poc` |
| objdump | DLX 架构反汇编 OOB | `objdump-dlx-calc-poc` |
| Ghidra 12.1.2 | 分析器/脚本 → RCE | `ghidra-12.1.2-rce-ace-calc-poc` |
| libarchive | zip/debuginfod 大小边界 | `libarchive-zip-debuginfod-size-boundary` |
| nmap | IPv6 extlen 整数回绕 | `nmap-ipv6-extlen-wrap-poc` |
| ImageMagick | Ghostscript 委派用**裸 exe 名** → cwd 搜索路径劫持（Windows） | `imagemagick-gs-delegate-hijack-poc` |

**定性红线**：这些都是「喂文件者触发」的本地 ACE；只有目标把**攻击者的文件**自动喂进解析器时才升级为远程影响，否则不得报成未授权 RCE。
全 39 条与前置条件 → `1day-nuclei-kit` 的 `references/exploitarium-pattern-index.md`。
