## 三条容器/虚拟化逃逸面（研究 PoC，本机未复现）

| 组件 | 面 | 前置 | 要点 |
|---|---|---|---|
| Docker | `docker cp` copy-out 目的地解析逃逸 | **能执行 `docker cp`**（哪怕只是被授了 docker 命令） | 目的地路径解析缺陷 → 容器外文件系统任意写。「能跑 docker 命令」就往上一步想：**宿主任意写 ≈ 持久化/提权**。`poc-db/exploitarium/docker-cp-copyout-destination-escape` |
| QEMU CXL Type-3 | 客户机 → 宿主 VM 逃逸 | 客户机 root + CXL 设备暴露 | BAR2 mailbox 泄宿主指针 → 伪造 QEMU 内存 API 对象 → 宿主执行 `id>/tmp/...`。完整样本（BIOS 软盘 + 16 位 loader + 32 位 stage）`poc-db/exploitarium/qemu-cxl-type3-mailbox-escape-poc` |
| Gitea act_runner | CI runner 命名空间逃逸（**无 CVE 也常能打**） | 能往仓库推 workflow | `container.options` 加 `--pid=host --ipc=host` + 宽 capabilities + `seccomp/apparmor=unconfined`，**`Privileged` 保持 false** → 宿主命名空间 root。详见 `gitea-diffpatch-rce` 路 B |

分类规律：容器面逃逸优先看「我能不能让宿主替我执行一个动作」（docker 命令、CI runner、挂载卷、socket），而不是只找内核 CVE。
全 39 条 → `1day-nuclei-kit` 的 `references/exploitarium-pattern-index.md`。
