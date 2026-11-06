## Attacking EDR Infrastructure Directly

### Driver Attack Surface Analysis

A systematic approach to analyzing EDR drivers from a low-privileged user perspective:

#### 1. Driver Discovery

**Static Analysis:**

```powershell
# List loaded drivers
driverquery /v
Get-WindowsDriver -Online -All

# Using WMI
Get-WmiObject Win32_PnPSignedDriver | Select-String "EDR_Vendor"
```

**Dynamic Analysis:**

```powershell
# Using sc command
sc query type= driver state= all

# Process Monitor filtering
# Filter: Process and Thread Activity -> Show Image/DLL
```

#### 2. Interface Enumeration

**Device Driver Interfaces:**

- Listed in WinObj under "GLOBAL??" as Symbolic Links
- Accessible via `\\.\DEVICE_NAME` format
- Tools: WinObj (Sysinternals), DeviceTree (OSR - discontinued)

**Mini-Filter Driver Interfaces:**

- Listed in WinObj as "FilterConnectionPort" objects
- Communication via `FltCreateCommunicationPort` API
- Example paths: `\CyvrFsfd`, `\SophosPortName`

#### 3. Access Permission Analysis

**Device Driver ACL Checking:**

```cpp
// Using DeviceTree (preferred) or kernel debugger
// WinDbg example:
!object \Device\DeviceName
!sd <SecurityDescriptor_Address> 1
```

**FilterConnectionPort ACL Checking:**

```powershell
# Using NtObjectManager (James Forshaw)
Get-FilterConnectionPort -Path "\FilterPortName"
# Error indicates access denied

# In WinDbg:
!object \FilterPortName
dx (((nt!_OBJECT_HEADER*)0xAddress)->SecurityDescriptor & ~0xa)
!sd <SecurityDescriptor_Address> 1
```

#### 4. Interface Functionality Analysis

**Device Driver Communication:**

- Primary method: DeviceIoControl() → IRP_MJ_DEVICE_CONTROL
- IOCTL codes differentiate between functions
- May include process ID verification for authorization

**FilterConnectionPort Communication:**

- Uses callback functions: ConnectNotifyCallback, DisconnectNotifyCallback, MessageNotifyCallback
- Similar to IOCTL dispatch with different message types

#### 5. Common EDR Driver Interfaces

**Examples of accessible interfaces found in research:**

**Palo Alto Cortex XDR:**

- **Device Interfaces**:
  - `\\.\PaloEdrControlDevice` (tedrdrv.sys) - ~20 IOCTL handlers with various functionality
  - `\\.\CyvrMit` (cyvrmtgn.sys) - Legacy Cyvera interface
  - `\\.\PANWEdrPersistentDevice11343` (tedrpers-<version>.sys) - Persistent device interface
- **FilterConnectionPort**: Various ports with different ACLs
- **Research Findings**:
  - IOCTL 0x2260D8 returns 3088 bytes of statistics data (accessible to low-privileged users)
  - IOCTL 0x2260D0 provides initialization status information
  - Some interfaces accessible due to injected DLL architecture requiring broad permissions

**Sophos Intercept X:**

- **FilterConnectionPort**: `\SophosPortName`
- **Analysis Results**: Accessible interfaces for legitimate process communication but limited attack surface

#### 6. Why EDRs Have Open ACLs

EDRs often use an architecture where:

- Agent injects DLLs into processes (including low-privileged ones like `word.exe`)
- Injected DLLs communicate directly with drivers via IOCTLs
- Drivers cannot restrict based solely on process privilege level
- Results in more permissive ACLs to accommodate legitimate injected processes

