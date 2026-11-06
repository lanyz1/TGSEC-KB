## Executables

### Basics

#### Static Detection

- Static Detection is simplest to evade, simply use packers
  - `PE Protector` - encrypt & anti-debug/anti-x
  - `PE Compressor` - reduce the file size
  - `.NET Obfuscators` - protect IP, symbol names, strings
  - `Script Obfuscators` - VBA/VBScript, PowerShell, `BAT`
  - `Virtualizers` - translate input PE executable machine code into custom VM
  - `Executable Signers` - steal genuine `EXE` certificate + properties and apply on implant
  - `Resource Editors` - remove Icon, version information
  - `Shellcode Loaders` - load shellcode in a stealthily
  - `Shellcode Encoders` - `Shikata Ga Nai`
- you can use [ProtectMyTooling](https://github.com/mgeeky/ProtectMyTooling) for various packers
- **Note on Online Scanners:** While services like AntiScan.Me can give an initial idea of detection rates, they don't replace testing against a local, isolated machine representative of the target environment. Defenses like Windows Defender may behave differently in a real system compared to online sandboxes.
- **Targeted Evasion:** Aiming for a universal "0 detection rate" can be time-consuming. It's often more effective to gather intelligence on the target's specific security solutions and focus evasion efforts accordingly.

#### Offensive CI/CD Pipeline

- RedTeam Malware Development
- Test Stability, Reliability, Security
- Artifact Obfuscation
- Test Against Offline EDR
- Watermarking & IOC Collection
- Operational Use
- Implant Tracking in Threat Intelligence Feeds

#### PE Backdoor

- Inject Shellcode Into Legitimate Executable
  - middle of current code section
  - into separate section
- Redirect Execution
  - change `AdressOfEntryPoint`
  - Hijack branching call `JMP, CALL`
  - TLS Callback
- Sign it With Self-signed/Custom Authentication
  - `LimeLighter`
  - `Mangle`
  - `ScareCrow`
  - `osslsigncode.exe`
- **Spoofed Certificates:** Signing an implant, even with a spoofed or invalid certificate, can sometimes reduce detection by AVs that don't thoroughly validate the certificate chain. However, be aware of potential legal consequences.
- **Timestamping:** The choice of Time Stamp Authority (TSA) server when signing can also unexpectedly influence detection rates by different AV products.

#### PE Watermarking

- Keep Track of implant/malware/IOC
- Inject Custom Watermark to Payloads and Poll VirusTotal
- Where to Inject
  - DOS Stub
  - PE Header Properties: TimeStamp, Checksum
  - Overlay
  - Additional PE Section
  - Resources: Version Information, Manifest
- What Should it Look Like
  - Random SHA256 might be enough
  - Encrypted engagement metadata

#### PE Attribute Cloning and Code Signing Considerations

- **Cloning Attributes:** Copying file attributes (version information, icons, product names, original filenames, etc.) from legitimate binaries can help an implant blend in.
  - When cloning, choose binaries that are legitimately present and commonly used on the target system. For instance, cloning an iTunes binary for a Windows Server target would be suspicious.
  - Consider cloning attributes from _unsigned_ legitimate Windows binaries (e.g., `at.exe`) and not signing the implant. This may be more effective than cloning a _signed_ binary (like `RuntimeBroker.exe`) and then signing the implant with a spoofed certificate, especially if the EDR/AV can easily verify signatures of its own system's binaries.
- **Testing is Crucial:** Always test cloned and/or signed implants on a system mimicking the target environment, as behavior can differ significantly from online scanning services.

### Shellcode

For detailed information on shellcode loaders, techniques, and implementation, including:

- Allocation, write, and execution phases
- Local vs remote injection
- Methods to hide shellcode
- Storage solutions (including Certificate Table approach)

See the [Shellcode documentation](exploit/shellcode.md).

### Formats

- `EXE`
  - use `EV Cert` code signing if you can afford it
  - otherwise self-signed `LimeLighter,ScareCrow,osslsigncode`
- `DLL`
  - typical no subject for prevalence/reputation score
  - offer delayed & de-chained execution primitives
  - not visible in process list
  - facilitate DLL hijacking attacks
  - can be used by `LOLBIN`
  - cleanup is hard, to remove first need to exit threads and then free that library
  - call `kernel32!FreeLibraryAndExitThread` when your evil DLL execution is done
  - keep `DLLMain` as simple as possible, or better don't used it at all, use the bullet point below
  - DLL hijacking/proxying/side-loading/planting/search-order hijacking to evade detection
  - use [Spartacus](https://github.com/sadreck/Spartacus) or [Crassus](https://github.com/vu-ls/Crassus) for DLL Hijacking automation
  - for DLL Side-Loading use `Frida+WFH`,`Koppeling`, `Siofra` or `Spartacus` and `Crassus`
  - Beware MS Defender might trigger on DLL Side-Loading/Hijacking
- `CPL`
  - control panel applet
  - double-clickable
- `WLL`
  - word add-in
  - not double-clickable
- `XLL`
  - excel add-in
  - double-clickable
  - if has `MOTW` gets blocked

### Additional Evasion Techniques

For detailed information on EDR evasion techniques, including:

- String obfuscation
- Entropy manipulation and file bloating
- Time-delayed execution
- Sandbox detection and environmental keying
- AMSI and ETW evasion
- Call stack obfuscation
- DripLoader technique

See the [EDR Evasion documentation](exploit/edr.md).

