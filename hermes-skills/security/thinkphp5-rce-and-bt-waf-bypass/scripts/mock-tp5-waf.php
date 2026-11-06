<?php
/* mock-tp5-waf.php —— 本地 ThinkPHP5 invokefunction + 宝塔同款 WAF 模拟器(回归测试用,零外部目标)
 *
 * 用法(无需 webserver 配置,PHP >=7.0):
 *   1) 目录布局: <docroot>/index.php 拷贝为本文件; 再建 <docroot>/public/ 与 <docroot>/runtime/temp/
 *   2) cd <docroot> && php -S 127.0.0.1:8899 -t .          # 不要传 router 脚本,让 index.php 吃 PATH_INFO
 *   3) python tp5-gadget.py --url 'http://127.0.0.1:8899/index.php/index/think\app/invokefunction' forms
 *
 * 它复刻了四件事,用来验证 tp5-gadget.py 的请求形态是否真的能绕 WAF:
 *   1) TP5 路由 /index.php/index/think\app/invokefunction + param() 吃 JSON body
 *   2) 宝塔 WAF 实测行为:只查「查询串」关键词 ⇒ 查询串路由 403、PATH_INFO+body 放行
 *   3) 散落 .php(非 index.php) 404
 *   4) disable_functions 的报错语义(system/exec 等回 Warning)
 */
$qs  = $_SERVER['QUERY_STRING'] ?? '';
$ct  = $_SERVER['CONTENT_TYPE'] ?? '';
$raw = file_get_contents('php://input');

/* 1) 迷你 WAF:只看查询串 */
foreach (['invokefunction', 'function=', 'vars[', '_method=', 'select *'] as $bad) {
    if (stripos($qs, $bad) !== false) {
        http_response_code(403);
        header('Content-Type: text/html; charset=utf-8');
        echo "<html><head><title>拦截</title></head><body>您的请求带有不合法参数,已被网站管理员的防火墙拦截。</body></html>";
        exit;
    }
}
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if (preg_match('#\.php$#i', $path) && basename($path) !== 'index.php') {
    http_response_code(404);
    echo '404 Not Found(散落 .php 被拦)';
    exit;
}

/* 2) 参数合并:GET + POST + JSON body(TP5 param() 行为) */
$params = array_merge($_GET, $_POST);
if (stripos($ct, 'json') !== false && $raw) {
    $j = json_decode($raw, true);
    if (is_array($j)) { $params = array_merge($params, $j); }
}
if (!isset($params['function'])) {
    header('Content-Type: text/plain; charset=utf-8');
    echo "mock TP5: 未提供 function 参数 (URI=$path QS=$qs)";
    exit;
}
$f    = $params['function'];
$vars = isset($params['vars']) ? array_values($params['vars']) : [];
if (count($vars) === 1 && is_array($vars[0])) { $vars = $vars[0]; }

/* 3) disable_functions 语义 + gadget 派发 */
$disabled = ['system', 'exec', 'passthru', 'shell_exec', 'proc_open', 'popen'];
header('Content-Type: text/plain; charset=utf-8');
if (in_array($f, $disabled, true)) {
    echo "Warning: $f() has been disabled for security reasons";
    exit;
}
try {
    if ($f === 'think\\__include_file') {
        include $vars[0];          /* 与 think\__include_file 语义一致 */
        exit;
    }
    $r = @call_user_func_array($f, $vars);
} catch (Throwable $e) {
    echo 'Error: ' . $e->getMessage();
    exit;
}
if (is_string($r) || is_int($r) || is_float($r)) { echo $r; }
elseif (is_bool($r)) { var_export($r); }
elseif ($r !== null) { var_dump($r); }
