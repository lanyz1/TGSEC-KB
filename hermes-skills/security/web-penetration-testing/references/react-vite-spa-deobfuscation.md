# React + Vite SPA 反混淆与API提取

## 场景
SPA 使用 Vite 构建，代码经过 minify + mangling（变量名压缩为2-3字符）。

## 步骤

### 1. 下载主入口 JS
```bash
curl -s "https://target.com/assets/index-xxxxx.js" > bundle.js
```

### 2. 提取所有代码分割 chunk
```
__vite__mapDeps 数组中包含所有 lazy-loaded chunk 路径
```

### 3. 找到 API 分发函数
在重度混淆代码中，API 函数名通过 `export{}` 块暴露：
```javascript
export{... ,qy as W, ...}
# 这里 qy = W 函数（API 调用入口）
```

然后在 bundle 中搜索 `qy`：
```javascript
// 找到 qy 函数定义，了解 API URL 构造方式
```

### 4. 提取所有 API action
```bash
grep -oP 'W\("\[a-zA-Z0-9_-]+"' bundle.js
```

### 5. 处理多 chunk 场景
```python
chunks = ["chunk1.js", "chunk2.js", ...]
for chunk in chunks:
    actions = re.findall(r'W\("([a-zA-Z0-9_-]+)"', js)
    # 收集所有 action
```

## 常见陷阱

| 陷阱 | 现象 | 解决 |
|------|------|------|
| **Source Map 假阳性** | `.js.map` 返回 200 但内容 = index.html | 检查 Content-Type |
| **API 全路径健康检查** | `/api/` 所有路径返回同一 JSON | 用 query action 模式测试 |
| **SPA 登录注入失效** | localStorage 设 token 无效 | 直接用 curl POST 登录 API |
| **变量名完全混淆** | `W("action")` 模式不存在 | 查 `export{}` 找到映射关系 |
