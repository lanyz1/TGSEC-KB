## 六、可预测标识符深度分析（新增·高端）

### 6.1 自增ID与业务规则分析
```
# 不止1,2,3…：分析ID生成规则
# - 日期+序号：202401010001 → 枚举日期区间×序号
# - 前缀+随机：随机段是否真随机（种子/长度）
# - 计数器+Hash：先解码再枚举
# - 多表复用序列（全局ID）：相邻ID属不同资源
# 工具：Python脚本提取ID规律、hashcat自定义规则

# 高价值目标：可枚举性 = 数据泄露面
# 评估：ID空间大小（位数/进制）vs 已用ID密度
```

### 6.2 UUIDv1时间戳预测（重点）
```
# UUIDv1 = 60位时间戳(100ns粒度) + 14位时钟序列 + 48位节点MAC
# 格式：xxxxxxxx-xxxx-1xxx-yxxx-xxxxxxxxxxxx（版本位=1）
# 攻击价值：
# 1. 泄露创建时间（精确到100ns）→ 推断对象创建/业务事件时间
# 2. 若MAC固定且可获取 → 预测后续UUID（需同时控制时钟序列）
# 3. 时间戳可回溯 → 还原ID生成时序，还原创建顺序

# 识别UUIDv1：version位=1 → 第13个字符为"1"
python3 -c "import uuid; print(uuid.uuid1())"   # 生成本地对比
# 在线/离线解码：
uuid -d <uuid>    # 或 python uuid.UUID(u).time → 时间戳
# 检测工具：nuclei/uuid tools、Burp扩展UUIDv1 decoder

# 绕过策略：若系统用UUIDv1做对象ID且未做授权检查 → 直接枚举时间窗口
# 防御观察：应使用uuid.uuid4()（密码学随机）
```

### 6.3 顺序UUID/雪花ID/ULID
```
# 雪花ID（Twitter Snowflake）：41位时间戳+10位机器+12位序列
# → 反推机器ID/生成时间/同毫秒序列
# → 相邻ID可枚举（若已知一个）

# 顺序UUID（UUIDv7草案/自定义排序UUID）：时间戳前缀+随机后缀
# → 时间可预测，空间需分析

# ULID：48位时间戳(Crockford Base32)+80位随机
# → 前10字符=毫秒时间戳（Base32可解码）

# 通用手法：
# 1. 收集一批ID → 位级分解（python bin()/bit操作）
# 2. 识别时间戳段/随机段/序列段
# 3. 若时间戳+序列占主导 → 可预测枚举
# 4. 若随机段<64位或非密码学随机 → 暴力可行性评估
# 工具：Python位运算分析脚本、在线雪花ID解码
```

### 6.4 熵分析与随机性检测
```
# 判断"不可预测ID"是否真的不可预测：
# 1. 收集N个ID（100+），做熵估计（NIST STS/ent工具）
# 2. 检查字符分布/位分布是否均匀
# 3. 测试时间相关性（相邻ID时间戳段相同）
# 4. 测试种子可复现性（java.util.Random/php rand/Math.random非安全）
# 工具：ent、NIST STS、dieharder

# 密码学弱随机案例：
# - java.util.Random：可预测，48位种子
# - PHP mt_rand()：需观察输出推断状态
# - Math.random()（旧V8）：非安全
# - 时间戳作种子
# 攻击：给定ID序列 → 反推RNG状态 → 预测下一ID
```

### 6.5 Hashids/编码ID逆向
```
# Hashids：数字→短字符串可逆哈希
# - 算法公开（github hashids/hashids-java等）
# - 默认salt："" → 直接解码所有ID
# - 自定义salt：可在本地爆破（若salt短/可猜测）
# 工具：hashids官方库、Python hashids包
# python3 -c "import hashids; h=hashids.Hashids(salt=''); print(h.decode('abc123'))"

# 其他编码：Base62/Base58（bitcoin地址风格）/自定义字母表
# 识别：字符集不含易混淆字符（0O1lI）→ Base58；大小写数字全 → Base62
# 枚举：Base62(1000000)=6字符 → 字典可爆破空间评估
```

