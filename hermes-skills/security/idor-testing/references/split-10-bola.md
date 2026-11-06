## 九、自动化BOLA检测方法论（新增·实战落地）

### 9.1 多账户会话对比法（核心）
```
# 原理：同一端点，高权限/用户A vs 低权限/用户B的响应差异
# 步骤：
# 1. 准备两个账户（userA拥有资源、userB无权限）
# 2. 用userA会话正常浏览全部API → Burp记录（Session Handling抓全）
# 3. 用userB会话重放相同请求（Autorize/BBAutoRepeater）
# 4. 对比：状态码、响应长度、body hash、关键字段
# 5. 判定：200且body含目标资源数据 = IDOR
# 关键：不能只看状态码（很多系统统一返回200/403），必须对比body

# 工具组合：
# - Autorize：低权Cookie自动重放+颜色标记
# - AuthMatrix：多角色矩阵
# - AutoRepeater：自动替换资源ID参数
# - BurpBounty/自定义：对比逻辑
# - 脚本化：Python+requests批量 + jq提取字段hash
```

### 9.2 响应差异分析技术
```
# 1. body哈希对比（排除噪声：时间戳/随机token）
# 2. 敏感字段存在性：email/phone/ssn/balance 是否出现
# 3. 资源量对比：数组长度>0 即泄露
# 4. 错误信息差异：404 vs 403 vs "not found" vs "forbidden" 语义
# 5. 时间差异：存在的数据响应更快（索引查询）
# 6. HTTP头差异：X-User-ID / Content-Length
# 工具：jq字段提取、响应归一化脚本（移除时间戳字段后hash）
```

### 9.3 ID替换模糊测试
```
# 对每个资源ID参数自动替换：
# - 邻近ID（±1、±100）
# - 其他用户已知ID
# - ID类型变体（int/string/uuid）
# - 数组/逗号/多参数
# 工具：AutoRepeater规则、自定义Python、Turbo Intruder
# 端点优先级：
# 1. GET/POST 读取型端点（低风险高价值）
# 2. 导出/下载端点（全量数据）
# 3. 更新/删除端点（破坏性，谨慎）
```

### 9.4 被动检测
```
# 用低权账号被动浏览，监听响应中是否包含高权数据
# 或：高权账号浏览时，对同端点用低权会话重放
# 蜜罐ID：请求不存在的ID观察错误差异
# 日志分析：SIEM/访问日志中跨用户对象访问模式
```

