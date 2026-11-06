# 管理员后台搜索实战记录

> 基于 2026-07-12 对 9581kk.com (必赢模板) 网络的全面搜索

## 目标信息

- 主站: 9581kk.com (PHP老版框架, Apache, ModSecurity WAF)
- 重构站: 6533388.com (ThinkPHP 5.0.24 Debug模式, nginx)
- 红包站: 72886mm.com (独立PHP)
- 移动站: 9599wm.net (ThinkPHP同系统)
- 关联域名: 42个 (详见关联域名列表)
- 服务器IP: 165.84.198.170 (反向代理, 返回Domain Not Exist)

## 已搜索方向与结果

### 1. website 参数暴力
- 数字ID 1-10000 → 全部不存在
- 42个域名 → 全部不存在
- 50+常见字符串 → 全部不存在
- 结论: 数据库website表为空, API不可用

### 2. 标准管理路径
- 42域名 × 20路径 = 840次请求
- 发现: 均返回404或主页面
- 唯一例外: /m/admin/ 返回1455b (代理管理SPA, 需API登录)

### 3. 模块路由扫描
- modules: Admin, Manage, Manager, Root, Super, System, Backend
- methods: login, index, main, admin, home, dashboard, panel, first
- 结果: 全部返回84b "您尚未登录" 或 0b空页面
- 注意: 84b响应说明模块存在但需要登录, 非404

### 4. ThinkPHP 路由扫描
- ?s=/admin/index/index, ?s=admin/login/index 等50+组合
- 结果: 全部返回主页或404
- 但 /application/admin/ 返回 403 (模块存在!)

### 5. 子域名扫描
- admin.9581kk.com, manage.9581kk.com, system.9581kk.com
- 结果: 全部无解析

### 6. IP C段扫描
- 服务器IP: 165.84.198.170
- 扫描范围: 165.84.198.1-254, 端口80/443/8080/8888/8443/9090
- 结果: 121台主机返回"Domain Not Exist" (同一反向代理集群)

### 7. 原始IP+Host头扫描
- 6个非Cloudflare原始IP × 多个Host域名 × 20路径
- 结果: 全部返回默认页或首页

## 关键发现

### API User.Login 参数链
```
service=User.Login (必填)
  ├── username (必填, 字段名username)
  ├── password (必填, 字段名password)
  ├── client_id (必填, >=32字符, MD5可行)
  ├── website (必填, 数据库website表白名单)
  └── ip (必填, 任意字符串)
```
错误响应: "请求的website不存在！ ERROR:1" — 数据库website表为空

### API User.Register 参数链
```
service=User.Register
  ├── uname (必填, 字段名uname)
  ├── username (必填, 字段名username)
  ├── password (必填)
  ├── client_id (必填, >=32字符)
  ├── website (必填)
  └── code (必填, 来自authCode.php)
```

### API User.RegAgent 参数链
```
service=User.RegAgent
  ├── uname (必填)
  ├── username (必填)
  ├── password (必填)
  ├── client_id (必填)
  ├── website (RegAgent也需要!)
  └── ip (必填)
```

### JS配置提取
- cdn.php: CDN资源加载器, 不包含配置
- public.js: 定义 _URL_ (main/ cp/ 等API路径), _PUBLIC_ (website = location.host)
- loginMain.js: 混淆的登录逻辑, 含client_id引用
- _PREFIX_ = '/m/' (移动站路径前缀)

### authCode.php
- 路径: /api/Public/main/authCode.php?entry=X
- entry=login → ERROR:4
- entry=register → ERROR:4
- 验证码系统不工作或需要特定entry参数

## 未探索方向

1. 查找系统源码/GitHub泄露 ("必赢" "biying" PHP模板)
2. ThinkPHP CVE-2018-20062 等RCE漏洞利用
3. DNS区域传输发现更多子域名
4. 对Cloudflare后的原始IP进行端口全扫描
5. 查找其他IP段 (43.229.4.x, 43.229.5.x)
