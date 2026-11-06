# 案例课：FastAdmin 落地后的 phpstudy / Workerman 提权链

> 来源：报告包 zygjb（2026-10）· 域：web-attack / 国产集成环境

## 一句话

FastAdmin 拿到后台只是应用层；同机 phpstudy 面板绑 `127.0.0.1:9080`、Workerman 以 root 跑 `:8090` 无鉴权——任一跳板/SSRF 打通本地口，就能从站点列表拿 MySQL 账密，再经 Workerman 内部命令 `setuid bash` 到 root。

## 链

1. **UEditor catchimage + phar**：`/assets/plugins/ueditor/php/controller.php?action=catchimage` 拉远程图；`phar.readonly=0` + 可写文件 → 构造 phar 触发反序列化
2. **install.result 挖账密**：`/install/install.result`、`/application/database.php`、`/runtime/install.lock` → 常见 `root/root`
3. **phpstudy 9080**：只绑本地；用 SSRF/跳板访问 → 站点列表 → MySQL 账密
4. **Workerman 8090**：root 进程、无鉴权握手 → 发内部命令 → `setuid bash`
5. **伪装马**：`assets_cache_waf.php`、`cache_<md5>.php` 放 `public/assets/`，避开 `*.php` 规则扫描

## 判据

- `5900/8090` 监听 + 进程属主 root + 握手无鉴权
- `install.result` 200 且含 db 配置
- phpstudy 9080 只对 127.0.0.1 开放 → 必须有本地访问原语

## 边界

- 无反序列化链/无可写点，catchimage 只是 SSRF
- Workerman 版本差异，先看握手与命令格式
- phpstudy 新版可能改端口/加鉴权

## 检查清单

- [ ] FastAdmin 版本与 UEditor 可达
- [ ] install.result/database.php
- [ ] 本地 9080/8090
- [ ] Workerman 进程属主
- [ ] 伪装马命名

---
@TGSEC社区 · @TGSEC-Qtzuu 整理
