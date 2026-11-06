## 概述

SSRF（Server-Side Request Forgery）利用服务器发起恶意请求，可访问内网资源、扫描端口、读取本地文件、攻击内网服务，甚至通过特定协议实现RCE。现代防护通过URL白名单、DNS解析验证、IP黑名单、协议限制等多层防御。本技能覆盖全协议（http/https/file/gopher/dict/ftp/ldap/tftp）、全攻击面（云元数据/内网服务/本地文件）、绕过方法（DNS重绑定/IP编码/302跳转/短链接/IPV6），以及Redis/FastCGI/Memcached等服务的完整RCE利用链。

