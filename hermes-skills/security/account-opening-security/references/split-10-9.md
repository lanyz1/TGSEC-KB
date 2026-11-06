## 9. 风险测评与适当性管理绕过

### 9.1 风险测评自动化

```python
# === 投资者风险测评绕过 ===

# 场景: 开户需要完成风险测评问卷
# 攻击: 自动选择答案以获取特定风险等级

# 1. 风险测评答案自动化
risk_assessment_answers = {
    # 激进型投资者答案（可开通所有业务）
    "aggressive": {
        "income_source": "A",        # 金融资产收入
        "annual_income": "E",        # 100万以上
        "investment_experience": "E", # 10年以上
        "investment_knowledge": "E",  # 非常了解
        "risk_tolerance": "E",       # 高收益高风险
        "max_loss_tolerance": "E",   # 可以承受较大亏损
        "investment_horizon": "E",   # 长期投资
        "investment_purpose": "E",   # 资产大幅增长
    },
    # 保守型（避免开通高风险业务）
    "conservative": {
        "income_source": "A",
        "annual_income": "C",
        "investment_experience": "A",
        "investment_knowledge": "A",
        "risk_tolerance": "A",
        "max_loss_tolerance": "A",
        "investment_horizon": "A",
        "investment_purpose": "A",
    }
}

# 2. 使用Selenium/Playwright自动化答题
# 3. 测试: 风险测评是否可重复提交
# 4. 测试: 风险测评结果是否可篡改（API直传）
# 5. 测试: 适当性管理是否与风险等级匹配
```

---

