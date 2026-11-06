---
name: lmcache-zmq-pickle-rce
description: "Use when 打 LMCache/vLLM 缓存层：ZMQ pickle 预认证 RCE。"
---

# LMCache 多进程传输未认证 pickle 反序列化（CVE-2026-105192）

LMCache 是 vLLM 生态的 KV-cache 层，多进程间用 ZeroMQ 传消息。**单条 ZMQ 消息，在参数解码阶段就执行代码**——任何 handler 都没跑到，鉴权也就没机会跑。

- 影响 **0.5.5 及以下**；**0.5.6 修**
- 服务以 root 跑则直接 `uid=0`
- 依赖：`msgspec` + `pyzmq`
- 源：`basesixtythree/B63-POC-CVE-2026-105192`（VERIFIED，lab 内 5/5 可靠性，双回显）

## 为什么值得单独记

这是 **AI 推理基础设施**（不是 web 应用）上的预认证 RCE。vLLM / LMCache 部署经常为了多节点共享 KV cache 把 ZMQ 端口开到可路由网段，而且默认无认证。扫到 5555/5556/6xxx 的 zmq 端口且进程是 python/LMCache，就可以试。

## 判据

```
docker ps / ps aux | grep -i lmcache      # 目标侧（已有 shell 时）
nmap -p 5555,5556,6000-7000 --open <host>
pip show lmcache | grep Version          # <= 0.5.5 命中
```

ZMQ 不是 HTTP——`curl` 看不到任何东西，`nc` 也不会有 banner。要用 pyzmq 发一帧才知死活：连接成功即端口在，发 pickle 帧看进程是否执行（回连/写文件/耗时）。

## 上游可迁移原语

**「用 pyzmq + pickle/msgspec 的进程间通信 = 预认证 RCE」。** 这套结构在 AI 栈里到处都是：LMCache、vLLM 的 distributed executor、Ray 的 object store（部分）、自定义 model server。审计要点就三条：

1. ZMQ socket 是否 `bind` 到 `0.0.0.0`（而非 127.0.0.1）
2. 解码用 `pickle.loads` / `msgspec.msgpack` + `dec_hook` 自定类型 / `torch.load`
3. 解码是否发生在任何 auth 检查之前

三条全中 = 单包 RCE。

## 坑

- ZMQ 无协议 banner，扫描器容易报“端口开但无响应”。要真发帧。
- 有些部署用 CURVE 加密（`zmq.curve_keypair`）——那就需要密钥，不是未授权。先用 `NULL` 机制试。
- lab 用 compose 起双胞胎；在线变体需 pip（`compose.online.yml`），`KNOWN-GAPS.md` 里写了哪些没验。
- 跑之前确认目标是自己的 lab 还是在范围内——这类端口往往是共享基础设施，扫错就打到别人的推理集群。
