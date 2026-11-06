## 7. 分号/后缀通道对非 Spring 栈是读取通道

Servlet/JFinal/Struts 栈无 Spring 的 StrictHttpFirewall：`/index.jsp;x=.js` 会真落到 JspServlet 并**执行 JSP**（实测 200 + 渲染内容）；`/;x=.js` 可直出欢迎页并泄漏 `<base href>` 真实 context path。
⇒ 用途：① 文件存在性 oracle；② 目录/欢迎页泄漏；③ **RCE 前置面**（一旦拿到任意写原语，落 JSP 即执行）。

