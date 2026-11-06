## MSI Shenanigans

### Installation

- MSI installer can be built with [WiX toolset](https://wixtoolset.org/), which brings us several properties
- there is a `<CustomAction>` tag letting us run `.DLL, .EXE, .VBScript/Jscript`
- After installation we can safely uninstall MSI, leaving no trace on HDD
- Can run
  - inner `VBScript/JScript` in-memory
  - inner `.NET assembly` in-memory
  - inner `EXE` file by extracting it to `C:\Windows\Installer\MSIXXXX.tmp`
- when running `EXE`, parent-child relationship gets dechained into `wininit.exe -> services.exe -> msiexec.exe -> MSIxxxx.tmp`

### Types

- `.MSI` - compound storage file format comprising of a set of databases structured in `OLE` format
- `.MSP` - Windows installer patch file
- `.MSM` - Windows merge module installer's file (not usable)
- `.MST` - Windows installer transformation file
- Files are stored in `.CAB` archives, that are bundled into `MSI` media table
- To extract contents from `.MSI` we can use [lessmsi](https://github.com/activescott/lessmsi), [ORCA](https://github.com/MicrosoftDocs/win32/blob/docs/desktop-src/Msi/orca-exe.md) or [msidump](https://github.com/mgeeky/msidump)
- `ORCA` & `MSISnatcher` lets us backdoor existing MSI file

### Manual

- compile `WXS` into `WIXOBJ`
- links `WIXOBJ` into `MSI`

```bash
wix\candle.exe project.exs x64
light.exe -ext WixUIExtension -cultures:en-us -dc1:high -out evil.msi project.wixobj
```

- use `rogue-dot-net\generateRouteDotNet.py` to compile custom `.NET` DLL based off shellcode
- create self-exctractable, standalone `.NET` CustomAction DLL with WiX MakeSfxCa
- compile `WXS` into `WIXOBJ`
- link `WIXOBJ` into `MSI`

```bash
python generateRogueDotNet.py -M --dotnet-ver v2 -t plain -s CustomAction -n CustomActions -m MyMethod -r -c x64 -o CustomAction.dll beacon64.bin
MakeSfxCA.exe CustomAction.CA.dll x64\sfxca.dll CustomAction.dll wix\Microsoft.Deployment.WindowsInstaller.dll
candle.exe project.wxs -arch x64
light.exe -ext WixUIExtension -cultures:en-us -dc1:high -out evil.msi project.wixobj
```

- install, wait, uninstall

```bash
evil.msi /q && sleep 5 && msiexec /q /x evil.msi
```

### Backdoor Existing MSI

- we can add rows to existing MSI thus backdooring it
- Interesting Fields
  - Binary - table that holds binary data in-memory during MSI installation
  - CustomAction - actions to perform pre/post installation
  - InstallExecuteSequence - sequence-ordered list of actions that take place during installation
  - File - files to be extracted into system
  - Component - describes into which directory should file be extracted
  - Media - CAB files inside of MSI
  - Registry - Contains all registry keys & values to be created
  - Shortcut - scatters LNK all around the system
- Process
  - copy `putty-installer.msi` to `backdoored.msi`
  - open `orca.exe` and open `backdorred.msi` inside it
  - tables -> CustomAction -> right click -> add row -> `Action=whatever1, type=1250, source=INSTALLDIR, target=calc`
  - tables -> InstallExecuteSequence -> sort tables by `Sequence` column -> add row -> `Action=whatever1, condition= NOT REMOVE, sequence = 6599`
  - file -> save as -> `backdoored.msi`
  - test it
- we can automate the process using `MSISnatcher`

### Windows App Package Format

- `.MSIX` which supersedes `.MSI` by enforcing publisher authentication via code signing certificate
- installed `.APPX/.MSIX` goes into `%ProgramFiles%\WindowsApps\<PublisherName>.<AppName>_<AppVersion>_<Arch>_<Hash>`
- extensions
  - `MSIX` the zip of signed installation package
  - `APPX` a directory containing `EXECUTABLES/Program`, `.AppxManifest.xml`, `[Content_Types.xml]`, assets, icons, other files
  - `APPXBUNDLE`, `MSIBUNDLE` contains `.APPX/.MSIX` and other files
  - `APPINSTALLER` - XML file pointing towards `.APPXBUNDLE` or `.MSIX` installers
- deployment
  - double-click
  - windows store
  - browsing a website with `ms-appinstaller` link
  - via PowerShell `Add-Package -Path .\evil.appx`
  - via remote host through `DCOM` - checkout [ProvisionAppx](https://github.com/CCob/ProvisionAppx)
  - a static Azure blob storage website -> HTML with `ms-appinstaller` URL handler -> use a signed binary (179$)

