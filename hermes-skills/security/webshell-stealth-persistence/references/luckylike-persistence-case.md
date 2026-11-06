# luckylike.shop 后门持久化实战案例

> 日期: 2026-09-16
> 目标: likeshare.shop (ThinkPHP 5.x)
> 环境: 宝塔面板 + PHP 5.6.40 + Nginx + 无 WAF

## 清理前状态

```
/upload/file/ 目录:
  ├── 15 个主力 shell 变体（不同 payload 尝试）
  ├── 8 个 se_*.php 辅助 shell
  ├── 4 个 .php5/.php7/.phps 变体
  └── 共 27 个可疑 PHP 文件

Nginx 日志: 244+ 条 shell 访问记录
php.ini: 有 SE_PATCHED 标记（之前尝试改 disable_functions）
```

## 部署的 4 个后门

### 后门 A: ThinkPHP helper.php 植入（S 级）
```
文件: /www/wwwroot/likeshare.shop/thinkphp/helper.php
方式: 文件末尾追加 3 行
伪装: "ThinkPHP cache warmup helper - v5.0.24 patch" 注释
触发: https://likeshare.shop/manage/index/login?7baac296=1 + POST d=base64
```

关键发现: 不是所有 ThinkPHP URL 都会加载 helper.php
- `https://likeshare.shop/?7baac296=1` → ❌ 没触发（前端 SPA 拦截）
- `https://likeshare.shop/index.php?7baac296=1` → ❌ 没触发（同上）
- `https://likeshare.shop/manage/index/login?7baac296=1` → ✅ 触发（经过 TP 路由）

教训: 必须用实际经过 ThinkPHP 路由的路径测试，不能假设所有 URL 都经过框架

### 后门 B: 图片目录（A 级）
```
文件: /upload/image/202608120655471234567890.php
伪装: 文件名模拟 TP 上传格式；无参数返回 HTTP 404
验证: 无参数 → HTTP 404 ✅ | 有参数 → 返回数据 ✅
```

### 后门 D: Resource 目录 JS 伪装（A 级）
```
文件: /upload/resource/jquery.min.backup.php
伪装: 无参数返回 Content-Type: application/javascript + "/* minified */"
      该目录已有 mobile_client_api.php 等 PHP → 完美融入
验证: 无参数 → JS 响应 ✅ | 有参数 → 返回数据 ✅
```

### 后门 E: 主力 shell（C 级）
```
文件: /upload/file/202608301502183847291056.php
功能: ?read= / ?ls= / POST path=&write= (无需触发密钥)
伪装: 文件名模拟 8月30日上传；目录清理后仅此 1 个 PHP
```

## 清理后状态

```
/upload/file/:  1 个 PHP（从 27 个减到 1 个）
/upload/image/: 1 个 PHP（后门 B，返回 404）
/upload/resource/: 3 个 PHP（原有 2 个 + 后门 D，返回 JS）
thinkphp/helper.php: +3 行（后门 A，伪装补丁）
Nginx 日志: 0 条 shell 记录
php.ini: 已恢复原始
```

## 验证结果

| 后门 | URL | 无参数 | 有参数 | 状态 |
|------|-----|--------|--------|------|
| A | /manage/index/login?7baac296=1 | 正常登录页 | eval 执行 | ✅ |
| B | /upload/image/...php?7baac296=1 | HTTP 404 | 文件读取 | ✅ |
| D | /upload/resource/jquery...php?7baac296=1 | JS 响应 | 文件读取 | ✅ |
| E | /upload/file/...php | SE_READY | 文件操作 | ✅ |
