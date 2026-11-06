<?php
/**
 * session 写入探针 —— 穷举“哪个 URI 写了哪个 session 键”
 *
 * 用法：
 *   SD_LOG=/tmp/session_diff.log  SD_WATCH=cartccdetail  php-fpm ...   (环境变量经 fpm pool env[] 传入)
 *   或直接改下面两个常量。
 *
 * 部署：框架钩子目录（WHMCS: includes/hooks/），在请求早期加载 ⇒ 快照早于业务写入。
 * 输出：每个请求一行 diff；目标键变化标 ★，一眼看出“唯一写入点”。
 *
 * ★ 灵敏度自校验（必做，否则“零写入”是假阴性）：
 *   先跑一次验证码/登录/加购物车，确认日志里能看到 captchaData / flash /
 *   loginPostRedirectUri 这类小变更；看不到就修好探针再报负结论。
 */
$GLOBALS['__SD_LOG']   = getenv('SD_LOG') ?: '/tmp/session_diff.log';
$GLOBALS['__SD_WATCH'] = getenv('SD_WATCH') ?: '';   // 逗号分隔，如 cartccdetail,gatewayid

function __sd_hash() {
    try { return md5(serialize($_SESSION ?? [])); }
    catch (Throwable $e) { return md5(implode(',', array_keys($_SESSION ?? []))); }
}
function __sd_keys() {
    $s = [];
    foreach ((array) ($_SESSION ?? []) as $k => $v) {
        $s[(string) $k] = is_scalar($v) ? (string) $v : (is_array($v) ? 'array(' . count($v) . ')' : gettype($v));
    }
    return $s;
}
function __sd_write($line) {
    @file_put_contents($GLOBALS['__SD_LOG'], $line . PHP_EOL, FILE_APPEND | LOCK_EX);
}

$GLOBALS['__SD_SNAP'] = __sd_keys();      // 请求早期快照
$GLOBALS['__SD_HASH'] = __sd_hash();

register_shutdown_function(function () {
    $uri   = ($_SERVER['REQUEST_METHOD'] ?? '-') . ' ' . ($_SERVER['REQUEST_URI'] ?? '-');
    $after = __sd_keys();
    $watch = array_filter(array_map('trim', explode(',', (string) $GLOBALS['__SD_WATCH'])));
    $changes = [];
    foreach ($after as $k => $v) {
        $pre = $GLOBALS['__SD_SNAP'][$k] ?? null;
        if ($pre === null) {
            $changes[] = '+' . $k . ' len=' . strlen($v) . (in_array($k, $watch, true) ? ' ★TARGET' : '');
        } elseif ($pre !== $v) {
            $changes[] = '~' . $k . ' ' . strlen((string) $pre) . '->' . strlen($v) . (in_array($k, $watch, true) ? ' ★TARGET' : '');
        }
    }
    foreach ($GLOBALS['__SD_SNAP'] as $k => $v) {
        if (!array_key_exists($k, $after)) {
            $changes[] = '-' . $k . (in_array($k, $watch, true) ? ' ★TARGET' : '');
        }
    }
    // 无变更也写一行：日志连续性 = 后续能证明“这条路径确实跑到过”
    __sd_write(sprintf('[%s] %s | %s', date('c'), $uri, $changes ? implode(', ', $changes) : '(no session change)'));
});
