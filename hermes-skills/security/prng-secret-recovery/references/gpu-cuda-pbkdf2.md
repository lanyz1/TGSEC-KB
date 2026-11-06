# GPU CUDA PBKDF2-HMAC-SHA512 批量加速 —— 实现与调试实录

目标: BIP39 seed 派生 (PBKDF2-HMAC-SHA512, 2048 轮) 上 GPU 批量加速。
最终结果 (RTX 5080 + CUDA 12.8.2 + sm_120): **535,596/s, 64/64 与 hashlib 逐字节一致, 536× vs CPU 单核**。
2^32 时间戳种子全空间: CPU 16核 144h → GPU 2.2h (PBKDF2) / 26.5h (混合流水线)。

## 最终版本架构 (正确 + 快的组合)

```
预计算版 (hmac_init 一次 + hmac_run 2048 次, 每 HMAC 2 次 compress)
  + w[80] 工作数组用局部数组 (全局内存版只有 27k/s, 局部版 535k/s)
  + blk/h_in/h_out 等大缓冲用全局 scratch (每线程 448B, 防止编译器局部数组优化 bug)
  + 字节序全部显式大端 (见下)
```

scratch 布局: blk(128) + h_in(64) + h_out(64) + h(64) + u(64) + t(64) = 448B/线程。

## 5 个自身 bug (全部是字节序/填充, 不是编译器 bug — 诚实结论)

1. **SHA512 消息词必须大端加载**: `load_be64` 逐字节组装, 不能 memcpy 字节到 u64 (x86/GPU 小端)。
2. **长度字段指针**: `(u8*)&blk[15]` 是第 15 字节! 要 `blk + 120` (128 字节块的最后 8 字节)。
3. **HMAC key 补零填充**: key < 128B 时先补 0 到 128 再 XOR ipad/opad → 后 35 字节 = 0x00^0x36 = **0x36** (不是 0!)。漏了 = inner/outer 首块后段全错。
4. **u64 → 字节序列化必须大端** (最隐蔽): inner digest (u64 状态) 作为 outer 消息写入 blk 时, `memcpy(blk, hstate, 64)` 给小端字节序! 必须 `u64_to_be8()` 逐个大端写。同理最终 out 也要大端。**症状: inner 全对 (手工字节构造), outer 全错 (digest memcpy) — 这类"一半对一半错"先查序列化字节序。**
5. **0x80 填充 u64 小端写错位**: `bp[8] = 0x8000000000000000ULL` 小端内存 = blk[64]=0x00, blk[71]=0x80 (反了!)。要 `0x0000000000000080ULL` (低字节在 blk[64]) 或直接 `blk[64] = 0x80` 字节写。

## 调试方法论 (对任何"结果错但看不出为什么"的 CUDA kernel)

1. **逐层 dump 中间值**: 在 kernel 里把每一步的输入块和压缩后状态写进全局 debug buffer (u64 数组), host 端读回对比。布局要规划好, 每线程固定槽位。
2. **隔离单调用**: 写一个 test kernel 硬编码输入 (状态 + 块), 单独 launch 一次 compress, 排除调用序列干扰。测 4 组合交叉: (h3,b4)/(IV,b4)/(h3,zeros)/(IV,zeros) — 定位是状态还是块。
3. **字节序反转检查**: GPU 输出 (memcpy u64 数组) 是**小端字节序**, Python 打印 hex 是大端。对比前先反转字节! 教训: "case3 输出 e8cb4a77 但期望 cf7881d5" — 反转后完全一致, 差点误判成 bug。
4. **怀疑自己 > 甩锅编译器**: 会话中 3 次归因"nvcc 优化 bug" (局部数组、noinline、全局内存), 全是自己代码的字节序/填充错。先写 Python 参考实现逐步模拟验证逻辑, 再查实现细节。
5. **cudaMemset 诊断 kernel 是否真写**: 用 0xAA 预填充输出缓冲, 若结果还是旧值 = kernel 没写 (launch 失败/写错位置)。

## 性能优化路径 (实测)

| 版本 | 速率 | 说明 |
|------|------|------|
| 完整版 + 全全局缓冲 | 11-15k/s | 每 HMAC 4 次 compress + 全局内存访问慢 |
| 预计算版 + 全全局 | 27k/s | 每 HMAC 2 次 compress, 但缓冲全全局 |
| **预计算版 + w 局部 + blk 全局** | **535k/s** | w[80] 回局部数组是关键 (~20×) |

- 预计算 (ipad/opad 状态只算一次): 每 HMAC 从 4 块 → 2 块压缩, ~2×
- w[80] 局部 vs 全局: ~20× (全局内存访问是主要开销)
- 之前怀疑的"局部数组 bug" (hmac_init h_out 全 0) 实际是字节序/填充 bug 的连锁表现

## 环境要点

- Windows: nvcc 需要 MSVC cl.exe (VS Build Tools), 用 vcvars64.bat 设置环境
- git-bash 调 cmd: `MSYS_NO_PATHCONV=1 cmd /c build.bat` (否则 //c 被 MSYS 转义吞掉)
- cmd 中文路径乱码: 编译放 ASCII 路径 (D:\cuda_work), build.bat 内部 cd
- CUDA 12.8.2 安装器 `--installpath` 参数无效 (NSIS 装 C 盘), zip 版 404
- build.bat 要检查 nvcc 退出码 (旧 dll 残留会误报 BUILD_OK)
- Python 调用: `os.add_dll_directory(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin')` 先加载 cudart
- 混合流水线: CPU 助记词 194k/s → GPU PBKDF2 386k/s → CPU 16核点乘 69k/s (瓶颈) → 总 45k/s

## 相关文件

- `D:\cuda_work\pbkdf2_batch.cu` + `pbkdf2_batch.dll` — 最终 kernel
- `D:\渗透\wallet_research\gpu\gpu_bench.py` — 正确性 (64/64) + 速率测试
- `C:\Users\Administrator\Documents\gpu_pipeline_bench.py` — 混合流水线 (45k 地址/s)
- `D:\渗透\wallet_research\gpu_acceleration_plan.md` — 完整方案文档
