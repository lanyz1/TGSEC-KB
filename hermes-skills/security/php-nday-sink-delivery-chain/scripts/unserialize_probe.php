<?php
/**
 * unserialize 探针 —— 白盒证实“哪一行代码在反序列化”
 *
 * 原理：PHP 不能在用户态 hook 内建 unserialize()，但 `unserialize_callback_func`
 * 会在遇到**未定义类**时被回调，回调内取 debug_backtrace 即得到 sink 调用栈。
 * ⇒ 伪造载荷里用一个不存在的类名（如 O:14:"ZzzProbePOC123":0:{}）就能强制命中。
 *
 * 部署位置：框架钩子目录（WHMCS: includes/hooks/ ；其它: plugin/addon/middleware）
 * 适用：PHP 5.x~8.x，ini 项 unserialize_callback_func = PHP_INI_ALL，可运行时 ini_set。
 *
 * 产出日志示例：
 *   [2026-09-19T12:00:00+08:00] uri=/modules/gateways/callback/tco.php class=ZzzProbePOC123
 *   #1 unserialize() at /app/vendor/whmcs/whmcs-foundation/lib/Invoice.php:302
 *   #2 WHMCS\Invoice->getGatewayInvoiceParams() at includes/gatewayfunctions.php:1234
 *   #3 getGatewayVariables() at .../CallbackRequestHelper.php:5
 *   #4 CallbackRequestHelper->__construct() at modules/gateways/callback/tco.php:9
 *   incomplete_class_usage uri=...: Cannot use object of type __PHP_Incomplete_Class as array
 *
 * 注意：只对“未定义类”回调 ⇒ 对纯数组（a:N:{...}）载荷不会命中，
 *       这是好事：命中即证明攻击者可控的对象真的被实例化了。
 */
$GLOBALS['__UP_LOG'] = getenv('UP_LOG') ?: '/tmp/unserialize_probe.log';

function __up_log_write($line) {
    @file_put_contents($GLOBALS['__UP_LOG'], $line . PHP_EOL, FILE_APPEND | LOCK_EX);
}

function __up_cb($classname) {
    // 跳过帧#0(探针自身回调), 让 #1 就是真的 sink 调用行
    $bt  = array_slice((new Exception('hit'))->getTrace(), 1);
    $out = [];
    foreach ($bt as $i => $f) {
        $fn  = ($f['class'] ?? '') . ($f['type'] ?? '') . ($f['function'] ?? '?');
        $loc = ($f['file'] ?? '?') . ':' . ($f['line'] ?? '?');
        $out[] = '#' . ($i + 1) . ' ' . $fn . '() at ' . $loc;
    }
    __up_log_write(sprintf('[%s] uri=%s class=%s', date('c'), $_SERVER['REQUEST_URI'] ?? '-', $classname));
    __up_log_write(implode(PHP_EOL, $out));
    // 不抛异常：让上层继续执行并自己报错（如 “Cannot use object ... as array”），
    // 该报错本身就是 sink 被触发的第二个独立证据。
    return false;
}

ini_set('unserialize_callback_func', '__up_cb');
__up_log_write(sprintf('[%s] probe_loaded uri=%s ini=%s',
    date('c'), $_SERVER['REQUEST_URI'] ?? '-', ini_get('unserialize_callback_func')));

// 未命中也要留痕 ⇒ 后续才能区分“没跑到”和“跑了没写”
register_shutdown_function(function () {
    $e = error_get_last();
    if ($e && stripos((string) $e['message'], '__PHP_Incomplete_Class') !== false) {
        __up_log_write(sprintf('[%s] incomplete_class_usage uri=%s: %s',
            date('c'), $_SERVER['REQUEST_URI'] ?? '-', $e['message']));
    }
});
