#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
admin_cred_hunter.py — 管理端后台「凭据来源」系统化清道夫(纯 stdlib,零依赖)

定位:在跑弱口令 / 大字典 **之前**,先把「admin 账号密码可能藏在哪里」按证据面扫一遍。
     大字典是最后手段,不是第一手段。本工具负责把前面 90% 的面自动化。

它做什么
  1. 基线法(catch-all 判别)—— 先拿一个必然不存在的路径做基线,只有长度不同的 200 才算命中
  2. 后台指纹 + 登录端点定位(若依/芋道/GVA/FastAdmin/宝塔/Spring/Django/Laravel/自研)
  3. 凭据来源面清道夫: 配置/环境文件、VCS、备份包、Actuator/heapdump、Druid、日志、
     IDE 残留、云凭据、运维泄漏、未授权用户列表
  4. 前端 JS 逆向挖密: 硬编码口令 / 密钥 / 签名算法 / 内网地址 / 隐藏接口 / 注释里的测试账号
  5. 小样本默认口令探测(带锁定保护 + 差分判定,不是爆破)

用法
  python admin_cred_hunter.py -u https://target.com/admin -o D:/渗透/target_admin
  python admin_cred_hunter.py -u https://target.com --proxy http://127.0.0.1:8080 --js-max 60
  python admin_cred_hunter.py -u https://target.com --login https://target.com/api/login --probe-login
  python admin_cred_hunter.py -f urls.txt -o D:/渗透/batch --threads 6

输出
  <out>/report.md        人读报告(按价值分层)
  <out>/findings.json    机器可读
  <out>/js/*.js          抓到的前端包(供人工继续逆向)

纪律
  * 代理开关放最外:本机 v2rayN 会透明接管外联,打靶时先确认出口
  * 只打授权目标;空间测绘/全网扫不是本工具的职责
  * --probe-login 默认关闭;开启时锁定保护必生效,命中即停
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# ----------------------------------------------------------------------------- 基础

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

MAXBODY = 3 * 1024 * 1024          # 单响应最大读取 3MB
LOCK_HINTS = ["锁定", "已锁定", "禁止登录", "too many", "try again after", "locked",
              "429", "频繁", "稍后再试", "限流", "冻结", "captcha", "验证码不正确"]
CAPTCHA_HINTS = ["captcha", "verifycode", "verify_code", "checkcode", "vcode",
                 "geetest", "altcha", "aj-captcha", "滑块", "验证码", "recaptcha", "turnstile"]

PROXY = None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """禁止跟随跳转 —— 登录探测必须看到 302 本身(那常常就是成功信号)。"""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http(url, method="GET", data=None, headers=None, timeout=12, allow_redirect=True):
    """返回 (status, headers_dict, body_bytes, err)。status 0 = 网络层失败。"""
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data).encode()
            h.setdefault("Content-Type", "application/x-www-form-urlencoded")
        elif isinstance(data, str):
            body = data.encode()
        else:
            body = data
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    handlers = [urllib.request.HTTPSHandler(context=SSL_CTX)]
    if PROXY:
        handlers.append(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    else:
        handlers.append(urllib.request.ProxyHandler({}))  # 显式绕过环境代理,避免被系统代理吞掉
    if not allow_redirect:
        handlers.append(_NoRedirect())
    op = urllib.request.build_opener(*handlers)
    try:
        with op.open(req, timeout=timeout) as r:
            raw = r.read(MAXBODY)
            return r.status, dict(r.headers), raw, None
    except urllib.error.HTTPError as e:
        try:
            raw = e.read(MAXBODY)
        except Exception:
            raw = b""
        return e.code, dict(e.headers or {}), raw, None
    except Exception as e:  # 超时/DNS/TLS
        return 0, {}, b"", f"{type(e).__name__}: {e}"


def text(raw: bytes) -> str:
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(enc, errors="replace")
        except Exception:
            continue
    return ""


_UNESC = re.compile(r"\\u([0-9a-fA-F]{4})")


def unescape_u(s: str) -> str:
    """把 JSON 里的 \\uXXXX 还原成字符。
    国内后端(Spring/Jackson、PHP json_encode 默认)大量把中文转义成 \\uXXXX,
    不解开则「账号已锁定」这类关键词永远匹配不到 —— 锁定检测会静默失效。"""
    if "\\u" not in s:
        return s
    return _UNESC.sub(lambda m: chr(int(m.group(1), 16)), s)


# ----------------------------------------------------------------------------- 路径清单
# tier: 1=凭据直出(最高价值) 2=源码/结构 3=旁路与情报

PATHS = [
    # ---- tier1 配置 / 环境 / 密钥
    (1, "/.env", "环境变量:DB/JWT/云AK/APP_KEY"),
    (1, "/.env.local", "环境变量(本地覆盖,常忘删)"),
    (1, "/.env.production", "生产环境变量"),
    (1, "/.env.prod", "生产环境变量"),
    (1, "/.env.dev", "开发环境变量"),
    (1, "/.env.development", "开发环境变量"),
    (1, "/.env.test", "测试环境变量"),
    (1, "/.env.bak", "环境变量备份"),
    (1, "/.env.old", "环境变量历史"),
    (1, "/.env.example", "示例值 = 厂商默认口令候选"),
    (1, "/env", "裸环境文件"),
    (1, "/config.js", "前端运行时配置(常含 API 基址/密钥)"),
    (1, "/config.json", "配置文件"),
    (1, "/config.yaml", "配置文件"),
    (1, "/config.yml", "配置文件"),
    (1, "/application.yml", "Spring 主配置(DB/JWT 密钥)"),
    (1, "/application-dev.yml", "Spring dev 配置"),
    (1, "/application-prod.yml", "Spring prod 配置"),
    (1, "/bootstrap.yml", "Spring Cloud 配置"),
    (1, "/appsettings.json", ".NET 配置(连接串)"),
    (1, "/appsettings.Production.json", ".NET 生产配置"),
    (1, "/web.config", "IIS 配置"),
    (1, "/wp-config.php.bak", "WordPress 配置备份(DB 明文)"),
    (1, "/config.php.bak", "PHP 配置备份"),
    (1, "/database.php", "Laravel/CI DB 配置"),
    (1, "/settings.py", "Django 配置(SECRET_KEY)"),
    (1, "/local_settings.py", "Django 本地配置"),
    (1, "/config/global.php", "自研全局配置"),
    (1, "/include/config.php", "老式 PHP 配置"),
    (1, "/App/Conf/config.php", "ThinkPHP 配置"),
    (1, "/application/database.php", "TP5 DB 配置"),
    (1, "/api/config", "运行时配置接口"),
    (1, "/runtime/app-config.js", "TMA/运行时配置(PLATFORM_ID/API_LIST)"),
    (1, "/swagger-resources", "Swagger 资源列表"),
    (1, "/v2/api-docs", "Swagger 2 全量接口契约"),
    (1, "/v3/api-docs", "OpenAPI 3 全量接口契约"),
    (1, "/openapi.json", "FastAPI/OpenAPI 契约"),
    (1, "/api-docs", "接口文档"),
    (1, "/swagger-ui.html", "Swagger UI"),
    (1, "/doc.html", "Knife4j 文档"),
    # ---- tier1 云 / 运维凭据
    (1, "/.aws/credentials", "AWS 凭据"),
    (1, "/.aws/config", "AWS 配置"),
    (1, "/.ssh/id_rsa", "SSH 私钥"),
    (1, "/.ssh/authorized_keys", "SSH 授权键(可写点)"),
    (1, "/id_rsa", "SSH 私钥"),
    (1, "/.docker/config.json", "Registry 凭据"),
    (1, "/docker-compose.yml", "编排文件(含环境变量/口令)"),
    (1, "/docker-compose.yaml", "编排文件"),
    (1, "/Dockerfile", "构建文件(常泄露内网源/私仓地址)"),
    (1, "/kubeconfig", "K8s 凭据"),
    (1, "/.kube/config", "K8s 凭据"),
    (1, "/terraform.tfstate", "Terraform 状态(云凭据全量)"),
    (1, "/.gitlab-ci.yml", "CI 变量/部署命令"),
    (1, "/jenkins/config.xml", "Jenkins 配置"),
    (1, "/.npmrc", "私仓 token"),
    (1, "/.pypirc", "私仓 token"),
    (1, "/.bash_history", "历史命令(常含明文口令)"),
    (1, "/.zsh_history", "历史命令"),
    (1, "/.mysql_history", "SQL 历史"),
    # ---- tier1 Java 生态
    (1, "/actuator/env", "Spring Actuator 环境变量(全量含口令)"),
    (1, "/actuator", "Actuator 端点索引"),
    (1, "/actuator/heapdump", "堆转储(对象图抽凭据)"),
    (1, "/heapdump", "堆转储"),
    (1, "/actuator/configprops", "配置属性(含数据源)"),
    (1, "/actuator/httptrace", "近期请求(含 Authorization 头!)"),
    (1, "/actuator/mappings", "全部路由"),
    (1, "/actuator/beans", "Bean 图"),
    (1, "/actuator/threaddump", "线程栈"),
    (1, "/actuator/prometheus", "指标"),
    (1, "/jolokia/list", "Jolokia MBean(RCE 面)"),
    (1, "/druid/index.html", "Druid 监控台"),
    (1, "/druid/sql.json", "Druid 全量业务 SQL"),
    (1, "/druid/weburi.json", "Druid 端点使用频率(谁在线)"),
    (1, "/druid/datasource.json", "Druid 数据源拓扑"),
    (1, "/druid/websession.json", "Druid 会话(可能含 session id)"),
    (1, "/druid/spring.json", "Druid Spring 映射"),
    # ---- tier1 日志(Audit 活票 / 明文口令的头号产地)
    (1, "/storage/logs/laravel.log", "Laravel 日志"),
    (1, "/storage/logs/laravel-2.log", "Laravel 日志轮转"),
    (1, "/logs/error.log", "错误日志"),
    (1, "/logs/app.log", "应用日志"),
    (1, "/logs/spring.log", "Spring 日志"),
    (1, "/log/error.log", "错误日志"),
    (1, "/runtime/log/", "TP 日志目录"),
    (1, "/nohup.out", "nohup 输出"),
    (1, "/app.log", "应用日志"),
    (1, "/debug.log", "调试日志"),
    (1, "/error.log", "错误日志"),
    (1, "/access.log", "访问日志"),
    # ---- tier2 源码 / 结构
    (2, "/.git/HEAD", "Git 仓库暴露"),
    (2, "/.git/config", "Git 远端地址(枢纽)"),
    (2, "/.git/logs/HEAD", "Git 提交历史"),
    (2, "/.git/COMMIT_EDITMSG", "最后提交信息"),
    (2, "/.svn/entries", "SVN 暴露"),
    (2, "/.svn/wc.db", "SVN 工作副本库"),
    (2, "/.hg/store/00manifest.i", "Mercurial 暴露"),
    (2, "/package.json", "前端依赖(版本→CVE)"),
    (2, "/composer.json", "PHP 依赖"),
    (2, "/composer.lock", "PHP 依赖锁"),
    (2, "/requirements.txt", "Python 依赖"),
    (2, "/pom.xml", "Maven 依赖"),
    (2, "/build.gradle", "Gradle 依赖"),
    (2, "/.idea/workspace.xml", "IDE 残留(常含路径/部署信息)"),
    (2, "/.vscode/settings.json", "IDE 残留"),
    (2, "/.DS_Store", "目录清单"),
    (2, "/robots.txt", "后台路径线索"),
    (2, "/sitemap.xml", "路由线索"),
    (2, "/phpinfo.php", "phpinfo(env 全量)"),
    (2, "/info.php", "phpinfo"),
    (2, "/test.php", "遗留测试页"),
    (2, "/server-status", "Apache 状态"),
    (2, "/nginx_status", "Nginx 状态"),
    # ---- tier2 备份 / 归档
    (2, "/web.zip", "前端/整站包"),
    (2, "/www.zip", "整站包"),
    (2, "/admin.zip", "后台包"),
    (2, "/dist.zip", "构建产物"),
    (2, "/source.zip", "源码包"),
    (2, "/code.zip", "源码包"),
    (2, "/site.zip", "站点包"),
    (2, "/backup.zip", "备份包"),
    (2, "/backup.tar.gz", "备份包"),
    (2, "/www.tar.gz", "站点包"),
    (2, "/db.sql", "数据库导出"),
    (2, "/dump.sql", "数据库导出"),
    (2, "/backup.sql", "数据库导出"),
    (2, "/1.sql", "数据库导出"),
    (2, "/wwwroot.rar", "站点包"),
    (2, "/admin.rar", "后台包"),
    (2, "/backup/", "备份目录"),
    (2, "/bak/", "备份目录"),
    (2, "/old/", "历史目录"),
    (2, "/temp/", "临时目录"),
    (2, "/test/", "测试目录"),
    (2, "/upload/", "上传目录"),
    (2, "/download/", "下载目录"),
    (2, "/data/", "数据目录"),
    (2, "/.well-known/security.txt", "安全联系(运维画像)"),
    # ---- tier3 未授权数据面(可直接吐用户/口令哈希)
    (3, "/prod-api/system/user/list", "若依 未授权用户列表"),
    (3, "/prod-api/system/user/list?pageNum=1&pageSize=10", "若依 未授权用户列表(分页)"),
    (3, "/system/user/list", "用户列表"),
    (3, "/api/system/user/list", "用户列表"),
    (3, "/api/user/list", "用户列表"),
    (3, "/api/users", "用户列表"),
    (3, "/users", "用户列表"),
    (3, "/api/admin/list", "管理员列表"),
    (3, "/api/v1/users", "用户列表"),
    (3, "/api/getUserInfo", "用户信息"),
    (3, "/api/user/getInfo", "用户信息"),
    (3, "/api/sysUser/list", "用户列表"),
    (3, "/api/base/captcha", "GVA 验证码(POST)"),
    (3, "/api/base/login", "GVA 登录端点"),
    (3, "/metrics", "Prometheus 指标"),
    (3, "/debug/pprof/", "Go pprof(信息泄露/RCE 面)"),
    (3, "/api-docs/swagger.json", "接口契约"),
]

# 默认口令小样本(tier 由框架指纹决定)。这是"测默认值"不是爆破。
DEFAULT_CREDS = [
    ("admin", "admin"), ("admin", "123456"), ("admin", "admin123"),
    ("admin", "admin888"), ("admin", "12345678"), ("admin", "admin123456"),
    ("admin", "123qwe"), ("admin", "88888888"), ("admin", "111111"),
    ("admin", "1qaz2wsx"), ("admin", "password"), ("admin", "Admin@123"),
    ("admin", "admin@123"), ("admin", "Aa123456"), ("admin", "root123"),
    ("administrator", "admin123"), ("root", "root"), ("root", "123456"),
    ("test", "test"), ("test1", "test1"), ("demo", "demo"),
    ("ruoyi", "admin123"), ("admin", "ruoyi123"),
    ("superadmin", "admin123"), ("manage", "manage"),
]
DEFAULT_USERS = ["admin", "administrator", "root", "superadmin", "manage",
                 "manager", "system", "sa", "test1", "operator"]

# 框架指纹:名字 -> (正则, 附带默认口令/后续动作提示)
FINGERPRINTS = [
    ("若依 RuoYi",        r"(若依|ruoyi|RuoYi|/prod-api/|admin123)", "admin/admin123;先查 XFF 白名单绕过 + Druid 监控"),
    ("芋道 Yudao",        r"(yudao|/admin-api/|tenant-id|infra/file-config)", "admin/admin123;Mock 字典读超管 profile"),
    ("GIN-VUE-ADMIN",     r"(gin-vue-admin|/api/base/login|authorityId|x-token)", "admin/123456;注册接口→提 authorityId→伪造 JWT"),
    ("FastAdmin",         r"(fastadmin|/adminlogin/|\?ref=addtabs)", "admin/123456;AJ-Captcha 滑块,先破验证码"),
    ("ThinkPHP",          r"(ThinkPHP|thinkphp|/index\.php\?s=)", "老站常 extends Action 无鉴权;?s= 兼容路由可绕 403"),
    ("Laravel",           r"(laravel_session|XSRF-TOKEN|Whoops|Symfony)", ".env 泄漏→APP_KEY→反序列化 RCE"),
    ("Spring Boot",       r"(Whitelabel Error Page|/actuator|JSESSIONID)", "先打 /actuator/env + /actuator/heapdump"),
    ("Django",            r"(csrfmiddlewaretoken|Django|/admin/login/)", "SECRET_KEY 泄漏→会话伪造"),
    ("宝塔 BT Panel",      r"(BT-Panel|宝塔|安全入口校验失败)", "/www/server/panel/data/default.db 提 hash+安全入口"),
    ("1Panel",            r"(1Panel|1panel)", "CVE-2024-39911 SQLi 写 webshell;XFF 绕 IP 白名单"),
    ("Jenkins",           r"(Jenkins|X-Jenkins)", "CVE-2024-23897 任意文件读(EPSS 1.0)"),
    ("Grafana",           r"(grafana|Grafana)", "CVE-2021-39226 快照绕过;admin/admin"),
    ("phpMyAdmin",        r"(phpMyAdmin|pma_|/pma/)", "先测免认证(auth_type=config)→弱口令→CVE"),
    ("WordPress",         r"(wp-content|wp-includes|wordpress)", "插件即攻击面(grep 参数当凭证);xmlrpc 爆破"),
    ("Nacos",             r"(nacos|NACOS)", "3.x /v3/auth/user/list 未授权 → 列配置"),
    ("XXL-JOB",           r"(xxl-job|XXL_JOB)", "admin/123456 → GLUE_SHELL RCE"),
    ("Vben Admin",        r"(vben|vue-vben-admin)", "全 chunk 提 API + 找真实登录端点"),
    ("Vol.Core",          r"(Vol\.Core|Vue\.NetCore|volcore)", "JWT 弱密钥 + 表驱动 API"),
    ("Filament/Livewire", r"(livewire|filament)", "Livewire RPC 登录;CSRF 419 需带 X-XSRF-TOKEN"),
]

# ----------------------------------------------------------------------------- JS 挖密
SECRET_PATTERNS = [
    ("DB-URI", r"(?i)\b(?:jdbc:[a-z]+|mysql|postgres(?:ql)?|mongodb(?:\+srv)?|redis|amqp|mssql|oracle|clickhouse)://[^\s\"'<>\\]{6,260}"),
    ("私钥", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    ("公钥", r"-----BEGIN PUBLIC KEY-----"),
    ("云AK", r"\b(?:AKIA|ASIA|LTAI|AKID|AKLT)[0-9A-Za-z]{12,40}\b"),
    ("键值型密钥", r"(?i)\b(password|passwd|pwd|pass|secret|secretkey|secret_key|appsecret|app_secret|clientsecret|"
                  r"client_secret|apikey|api_key|accesskey|access_key|accesskeyid|access_key_id|secretaccesskey|"
                  r"token|authtoken|auth_token|accesstoken|access_token|privatekey|private_key|encryptkey|"
                  r"encryptioncipherkey|signkey|sign_key|jwt_secret|jwtsecret|signingkey|signing_key|"
                  r"aeskey|aes_key|sm4key|initkey|salt|商户密钥|密钥|口令|密码)\b\s*[:=]\s*[\"']([^\"'\n]{3,140})[\"']"),
    ("Bearer 令牌", r"(?i)\bbearer\s+[A-Za-z0-9\-_\.=]{16,}"),
    ("JWT 实例", r"\beyJ[A-Za-z0-9\-_]{8,}\.[A-Za-z0-9\-_]{8,}\.[A-Za-z0-9\-_]{4,}"),
    ("对称密钥候选", r"(?i)\b(?:aes|des|sm4|hmac)[_\-]?(?:key|iv|secret|salt)\b\s*[:=]\s*[\"']([A-Za-z0-9+/=]{12,80})[\"']"),
    ("内网地址", r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})(?::\d{2,5})?\b"),
    ("内网域名", r"\b[a-z0-9][a-z0-9\-\.]{2,60}\.(?:internal|local|corp|intra|lan|test|dev|uat|stage|staging|pre)\b"),
    ("URL内嵌凭据", r"(?i)(?:[?&;])(?:password|passwd|pwd|pass|token|apikey|api_key|accesskey|secret|auth)[=:]([^\s&;\"'<>]{3,120})"),
    ("配置行密钥", r"(?m)^\s*([A-Za-z0-9_.\-]*(?:PASSWORD|PASSWD|PWD|SECRET|TOKEN|DSN|CREDENTIAL|APP_?KEY|ACCESS_?KEY)[A-Za-z0-9_.\-]*)\s*=\s*([^\s#]{3,180})"),
    ("签名算法", r"(?i)(md5|sha1|sha256|hmac|signature|sign)\s*\(\s*[^)]{0,160}\)"),
    ("注释里的账号", r"(?://|/\*|<!--)[^\n]{0,140}(?:password|pwd|账号|密码|默认密码|初始密码|测试账号|admin)[^\n]{0,140}"),
    ("账号字面量", r"(?i)[\"'](admin|administrator|superadmin|root|manage|运营|测试账号)[\"']\s*[,:]"),
]
# 提取隐藏接口(只留有语义的,避免噪声)
API_RE = re.compile(r"[\"'`](/[A-Za-z0-9_\-/{}\.\[\]:]{3,140})[\"'`]")
API_KEEP = re.compile(r"(?i)admin|manage|sys|sysUser|user|login|logout|token|secret|config|auth|"
                      r"upload|export|import|list|role|permission|reset|backdoor|debug")
SCRIPT_RE = re.compile(r"""(?is)<script[^>]+src=["']([^"']+)["']""")
INLINE_RE = re.compile(r"(?is)<script[^>]*>(.*?)</script>")
INPUT_RE = re.compile(r"""(?is)<input[^>]*name=["']([^"']+)["']""")
FORM_RE = re.compile(r"""(?is)<form[^>]*action=["']([^"']+)["']""")


def mine_text(src: str, origin: str, store: dict):
    """在一段文本(JS/HTML/配置)里挖密钥、接口、注释线索。"""
    src = unescape_u(src)   # 先还义,否则被 \uXXXX 包住的凭据挖不出来
    for label, pat in SECRET_PATTERNS:
        for m in re.finditer(pat, src):
            val = (m.group(m.lastindex) if m.lastindex else m.group(0)) or ""
            val = val.strip()
            if len(val) < 3 or len(val) > 300:
                continue
            if val in ("undefined", "null", "true", "false", "{}", "[]"):
                continue
            store.setdefault(label, set()).add(val[:300])
    for m in API_RE.finditer(src):
        p = m.group(1)
        if API_KEEP.search(p) and not p.endswith((".js", ".css", ".png", ".jpg", ".svg", ".woff")):
            store.setdefault("接口", set()).add(p)


# ----------------------------------------------------------------------------- 主流程

def baseline(base: str):
    """取 catch-all 基线:一个必然不存在的随机路径。返回 (长度, 状态码, 体哈希片段)。"""
    probe = base.rstrip("/") + "/__no_such_path_%d__" % int(time.time())
    st, _, raw, err = http(probe)
    if err:
        return None
    return len(raw), st


def fingerprint(base: str, home_html: str, headers: dict, findings: dict):
    blob = home_html + " " + json.dumps(headers, ensure_ascii=False)
    hits = []
    for name, pat, tip in FINGERPRINTS:
        try:
            if re.search(pat, blob, re.I):
                hits.append({"name": name, "tip": tip})
        except re.error:
            continue  # 单个坏正则不能拖垮整轮
    return hits


def sweep(base: str, blen, threads: int, outdir: str, findings: dict):
    """并发扫路径清单,按基线差分分类。"""
    jobs = []
    for tier, path, why in PATHS:
        url = base.rstrip("/") + path
        jobs.append((tier, path, why, url))

    def one(job):
        tier, path, why, url = job
        st, hdr, raw, err = http(url)
        n = len(raw)
        if err:
            cls = "ERR"
        elif st in (401, 403):
            cls = "DENY"
        elif st == 404:
            cls = "404"
        elif st in (301, 302, 307, 308):
            cls = "REDIR"
        elif st == 405:
            cls = "EXISTS-405"
        elif st == 200:
            cls = "CATCHALL" if (blen is not None and n == blen[0]) else "HIT"
        elif st >= 500:
            cls = "500"
        else:
            cls = str(st)
        return {"tier": tier, "path": path, "why": why, "url": url, "status": st,
                "len": n, "cls": cls, "ctype": hdr.get("Content-Type", ""),
                "body": raw if cls in ("HIT", "EXISTS-405") else b""}

    results = []
    lock = __import__("threading").Lock()
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as ex:
        for r in ex.map(one, jobs):
            with lock:
                results.append(r)
                mark = {"HIT": "[HIT ]", "EXISTS-405": "[405 ]", "DENY": "[deny]",
                        "404": "[ 404]", "CATCHALL": "[c/a ]", "REDIR": "[3xx ]",
                        "ERR": "[err ]"}.get(r["cls"], "[ ?  ]")
                if r["cls"] not in ("404", "ERR"):
                    print(f"  {mark} {r['path']:52s} {r['status']:>3} {r['len']:>7}B  {r['why']}", flush=True)
    return results


def grab_js(base: str, home_html: str, outdir: str, max_js: int):
    js_dir = os.path.join(outdir, "js")
    os.makedirs(js_dir, exist_ok=True)
    srcs = []
    for m in SCRIPT_RE.finditer(home_html):
        srcs.append(m.group(1))
    # 常见 SPA 主包名兜底
    for guess in ("/js/app.js", "/static/js/main.js", "/assets/index.js", "/main.js"):
        srcs.append(guess)
    # 去重 + 绝对化,同源优先
    seen, urls = set(), []
    for s in srcs:
        if s.startswith("data:"):
            continue
        u = urllib.parse.urljoin(base, s)
        if u in seen:
            continue
        seen.add(u)
        urls.append(u)
    urls = urls[:max_js]

    corpus, files = {}, []
    for u in urls:
        st, hdr, raw, err = http(u, timeout=15)
        if err or st != 200 or len(raw) < 200:
            continue
        name = re.sub(r"[^A-Za-z0-9_\-\.]", "_", urllib.parse.urlparse(u).path.strip("/"))[-90:] or "chunk.js"
        p = os.path.join(js_dir, name)
        try:
            with open(p, "wb") as f:
                f.write(raw)
        except Exception:
            pass
        files.append({"url": u, "saved": p, "len": len(raw)})
        corpus[u] = text(raw)
    # 内联脚本
    inline = "\n".join(m.group(1) for m in INLINE_RE.finditer(home_html))
    if inline.strip():
        corpus[base + " [inline]"] = inline
    return corpus, files


def try_login(base: str, ep: str, findings: dict, max_attempts: int = 14):
    """小样本默认口令差分探测。返回结构化结论。"""
    rep = {"endpoint": ep, "form_fields": [], "captcha_like": False,
           "baseline": None, "result": "not_tried", "attempts": [], "notes": []}
    st, hdr, raw, err = http(ep)
    if err:
        rep["notes"].append(f"GET 失败: {err}")
        return rep
    body = unescape_u(text(raw))
    rep["form_fields"] = INPUT_RE.findall(body)
    rep["captcha_like"] = any(h in body.lower() for h in CAPTCHA_HINTS) if body else False
    if rep["captcha_like"]:
        rep["notes"].append("登录面疑似有验证码/人机验证 —— 先解决验证码,再谈口令(否则必假阴性)")

    # 基线:一个必然错误的凭据,拿到"失败响应"的形状
    u_field = next((f for f in rep["form_fields"] if re.search(r"(?i)user|name|account|login|email|phone", f)), "username")
    p_field = next((f for f in rep["form_fields"] if re.search(r"(?i)pass|pwd|secret", f)), "password")
    rep["usernames_field"], rep["password_field"] = u_field, p_field
    st0, h0, raw0, err0 = http(ep, "POST", {u_field: "zz_no_such_user_zz", p_field: "zz_no_such_pass_zz"},
                               allow_redirect=False)
    rep["baseline"] = {"status": st0, "len": len(raw0), "location": h0.get("Location", ""),
                       "snippet": unescape_u(text(raw0))[:200]}
    base_len = len(raw0)

    tried = 0
    for u, p in DEFAULT_CREDS:
        if tried >= max_attempts:
            rep["notes"].append(f"达到本地尝试上限 {max_attempts},停止(防止锁定)")
            break
        st, hd, raw, err = http(ep, "POST", {u_field: u, p_field: p}, allow_redirect=False)
        if err:
            rep["notes"].append(f"网络失败 {err},停止")
            break
        b = unescape_u(text(raw))
        low = b.lower()
        tried += 1
        rec = {"user": u, "pass": p, "status": st, "len": len(raw),
               "location": hd.get("Location", ""), "setcookie": hd.get("Set-Cookie", "")[:80],
               "snippet": b[:160]}
        # 差分判定(三重):状态码变了 / 出现跳转 / 响应体长度与"必然失败"基线不同
        diff = (st != st0) or (bool(hd.get("Location")) and hd.get("Location") != h0.get("Location")) \
               or (base_len and len(raw) != base_len and len(raw) > 0)
        if diff:
            rec["differs_from_baseline"] = True
            if not any(h in low for h in LOCK_HINTS):
                rec["verdict"] = "候选命中(需人工确认)"
                rep["attempts"].append(rec)
                rep["result"] = "candidate"
                break
        if any(h in low for h in LOCK_HINTS):
            rec["verdict"] = "疑似触发锁定/风控"
            rep["attempts"].append(rec)
            rep["result"] = "locked"
            rep["notes"].append("命中锁定语义,立即停止(锁定会计入失败次数并暴露自己)")
            break
        rep["attempts"].append(rec)
        time.sleep(1.2)  # 低频,不构成爆破
    else:
        rep["result"] = rep["result"] if rep["result"] != "not_tried" else "no_hit"
    return rep


def write_report(outdir: str, base: str, findings: dict, sweep_res, js_files, fp, login_rep):
    os.makedirs(outdir, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sweep_res = sorted(sweep_res, key=lambda r: (r["tier"], r["cls"] != "HIT"))

    # 分层
    hits_t1 = [r for r in sweep_res if r["cls"] in ("HIT", "EXISTS-405") and r["tier"] == 1]
    hits_t2 = [r for r in sweep_res if r["cls"] in ("HIT", "EXISTS-405") and r["tier"] == 2]
    hits_t3 = [r for r in sweep_res if r["cls"] in ("HIT", "EXISTS-405") and r["tier"] == 3]
    denied = [r for r in sweep_res if r["cls"] == "DENY"]

    md = [f"# 管理端凭据来源清道夫报告",
          f"",
          f"- 目标: `{base}`",
          f"- 时间: {ts}",
          f"- 命中的凭据来源面: **{len(hits_t1)}** 条(tier1) / {len(hits_t2)} 条(tier2) / {len(hits_t3)} 条(tier3)",
          f"- 被拒(deny)路径: {len(denied)} 条 → 反向说明**这些面存在且被刻意保护**,是下一步绕过的靶子",
          f""]

    if fp:
        md += ["## 0. 指纹与打法提示", ""]
        for f in fp:
            md += [f"- **{f['name']}** → {f['tip']}"]
        md += [""]

    md += ["## 1. tier1 凭据直出面(优先人工看这几个)", ""]
    if not hits_t1:
        md += ["_无命中。转向:前端 JS 挖密(#3)→ 未授权数据面(#4)→ 兄弟域同款后台。_", ""]
    for r in hits_t1:
        md += [f"### `{r['path']}` — {r['why']}",
               f"- 状态 {r['status']},长度 {r['len']}B,类型 `{r['ctype']}`",
               "```", text(r["body"])[:1200].strip() or "(空响应体)", "```", ""]

    if hits_t2:
        md += ["## 2. tier2 源码/结构/备份", ""]
        for r in hits_t2:
            md += [f"- `{r['path']}` [{r['status']}/{r['len']}B] {r['why']}"]
        md += [""]

    if hits_t3:
        md += ["## 3. tier3 未授权数据面", ""]
        for r in hits_t3:
            md += [f"- `{r['path']}` [{r['status']}/{r['len']}B] {r['why']}"]
        md += [""]

    md += ["## 4. 前端 JS 挖密", ""]
    md += [f"- 抓取脚本 {len(js_files)} 个,落盘 `{os.path.join(outdir, 'js')}`"]
    for label in ("键值型密钥", "配置行密钥", "URL内嵌凭据", "对称密钥候选", "签名算法", "DB-URI", "云AK", "私钥",
                  "Bearer 令牌", "JWT 实例", "内网地址", "内网域名", "注释里的账号", "账号字面量"):
        vals = sorted(findings.get(label, []))[:25]
        if vals:
            md += [f"- **{label}** ({len(findings[label])})"]
            for v in vals:
                md += [f"    - `{v[:200]}`"]
    eps = sorted(findings.get("接口", []))[:120]
    if eps:
        md += ["", f"- **隐藏接口 ({len(findings['接口'])},列前 120)**", "```"]
        md += eps
        md += ["```"]
    md += [""]

    md += ["## 5. 登录面默认口令探测(小样本,非爆破)", ""]
    if login_rep:
        md += [f"- 端点: `{login_rep['endpoint']}`",
               f"- 表单字段: `{login_rep['form_fields']}` (用户名用 `{login_rep.get('usernames_field')}`,口令用 `{login_rep.get('password_field')}`)",
               f"- 失败基线: status={login_rep['baseline']['status']} len={login_rep['baseline']['len']} 体=`{login_rep['baseline']['snippet'][:120]}`",
               f"- 结论: **{login_rep['result']}**"]
        for n in login_rep["notes"]:
            md += [f"- 提示: {n}"]
        for a in login_rep["attempts"]:
            if a.get("differs_from_baseline") or a.get("verdict"):
                md += [f"- ⚠️ `{a['user']}:{a['pass']}` status={a['status']} len={a['len']} → {a.get('verdict')} 体=`{a['snippet'][:140]}`"]
    else:
        md += ["_未开启(加 --probe-login 并给 --login)。_"]
    md += [""]

    md += ["## 6. 被拒路径(deny)= 下一步绕过靶子", ""]
    for r in denied:
        md += [f"- `{r['path']}` [{r['status']}] {r['why']}"]
    md += [""]

    md += ["## 7. 下一步(按性价比排序)", "",
           "1. tier1 命中文件里的密钥 → 直接连库 / 自签 JWT / 云接管(凭据链闭环)",
           "2. JS 里的 `appid/secret/签名算法` → 本地复现签名,网关层不再是障碍",
           "3. 低权端点拿任意有效 token → 测它能否驱动管理 API(只验 token 存在性 = 直接提权)",
           "4. deny 路径 → 编码/大小写/框架入口文件/`?s=` 兼容路由/XFF 白名单 逐个绕",
           "5. 兄弟域 CT 反查 + Host 头 vhost 枚举 → 找同款后台的弱部署实例",
           "6. 以上全空,才轮到定向小字典爆破(必须串行限速、先测锁定策略)"]

    rp = os.path.join(outdir, "report.md")
    with open(rp, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    jp = os.path.join(outdir, "findings.json")
    with open(jp, "w", encoding="utf-8") as f:
        json.dump({"base": base, "time": ts, "fingerprints": fp,
                   "secrets": {k: sorted(v) for k, v in findings.items()},
                   "sweep": [{k: v for k, v in r.items() if k != "body"} for r in sweep_res],
                   "js_files": js_files, "login": login_rep}, f, ensure_ascii=False, indent=2)
    return rp, jp


def main():
    global PROXY
    ap = argparse.ArgumentParser(description="管理端凭据来源清道夫(零依赖)")
    ap.add_argument("-u", "--url", help="管理端入口 URL,如 https://t.com/admin")
    ap.add_argument("-f", "--file", help="批量:每行一个 URL")
    ap.add_argument("-o", "--out", default="D:/渗透/_admin_cred_hunt", help="输出目录")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--js-max", type=int, default=40, help="最多抓几个前端脚本")
    ap.add_argument("--proxy", help="http://127.0.0.1:8080(本机 v2rayN 会透明接管,注意出口)")
    ap.add_argument("--login", help="登录端点(默认从指纹猜,不猜就不探)")
    ap.add_argument("--probe-login", action="store_true", help="启用小样本默认口令探测")
    ap.add_argument("--no-js", action="store_true", help="跳过前端 JS 挖密")
    a = ap.parse_args()

    if a.proxy:
        PROXY = a.proxy
    targets = []
    if a.url:
        targets.append(a.url)
    if a.file:
        with open(a.file, encoding="utf-8") as f:
            targets += [l.strip() for l in f if l.strip() and not l.startswith("#")]
    if not targets:
        ap.error("需要 -u 或 -f")

    for base in targets:
        # 入口常带路径(/admin、/prod-api/…),但凭据面在**站点根**,必须推导出 origin 根再扫
        pr = urllib.parse.urlsplit(base)
        root = f"{pr.scheme}://{pr.netloc}"
        print(f"\n=== [TARGET] 入口 {base}  站点根 {root} ===", flush=True)
        outdir = a.out if len(targets) == 1 else os.path.join(a.out, re.sub(r"\W+", "_", base)[:60])
        os.makedirs(outdir, exist_ok=True)

        blen = baseline(root)
        print(f"[*] catch-all 基线 (站根): {blen}", flush=True)

        st, hdr, raw, err = http(base)
        home = text(raw)
        print(f"[*] 入口: {st} {len(raw)}B {hdr.get('Server','')} {hdr.get('X-Powered-By','')}", flush=True)

        fp = fingerprint(base, home, hdr, {})
        print(f"[*] 指纹: {[f['name'] for f in fp] or '未识别(按自研处理)'}", flush=True)

        print("[*] 扫凭据来源面 ...", flush=True)
        res = sweep(root, blen, a.threads, outdir, {})

        findings, js_files = {}, []
        # 命中的文件内容本身也要挖(.env / actuator / 日志里全是凭据)
        for r in res:
            if r["cls"] in ("HIT", "EXISTS-405") and r["body"]:
                mine_text(text(r["body"]), root, findings)
        if not a.no_js:
            print("[*] 前端 JS 挖密 ...", flush=True)
            corpus, js_files = grab_js(root, home, outdir, a.js_max)
            for u, src in corpus.items():
                mine_text(src, root, findings)
            print(f"[*] 抓到脚本 {len(js_files)} 个,挖出线索类别 {len(findings)} 类", flush=True)
        else:
            print("[*] catch-all 基线未变,跳过 JS(手动 --no-js)", flush=True)
        mine_text(home, root, findings)

        login_rep = None
        if a.probe_login and a.login:
            print("[*] 登录面小样本探测 ...", flush=True)
            login_rep = try_login(base, a.login, findings)
            print(f"[*] 登录探测结论: {login_rep['result']}", flush=True)

        rp, jp = write_report(outdir, base, findings, res, js_files, fp, login_rep)
        hits = [r for r in res if r["cls"] in ("HIT", "EXISTS-405")]
        ca = len([r for r in res if r["cls"] == "CATCHALL"])
        print(f"\n[✓] 报告: {rp}\n[✓] 数据: {jp}\n[✓] 命中 {len(hits)} 条 / 被拒 {len([r for r in res if r['cls']=='DENY'])} 条 / "
              f"catch-all 识别(已剔除假阳性) {ca} 条", flush=True)


if __name__ == "__main__":
    main()
