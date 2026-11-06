## Day 1: Memory Corruption Fundamentals

- **Goal**: Understand primary memory corruption vulnerability classes and their real-world impact.
- **Activities**:
  - _Reading_:
    - "The Art of Software Security Assessment" by Mark Dowd, John McDonald, Justin Schuh - Chapter 5: Memory Corruption
    - [Memory Corruption: Examples, Impact, and 4 Ways to Prevent It](https://sternumiot.com/iot-blog/memory-corruption-examples-impact-and-4-ways-to-prevent-it/)
  - _Online Resources_:
    - [Microsoft Security Research: Memory Safety](https://www.microsoft.com/en-us/research/project/checked-c/)
    - [Google Project Zero Blog](https://googleprojectzero.blogspot.com/) - Read recent memory corruption findings
  - _Concepts_:
    - What is memory corruption and why does it matter?
    - Understanding the stack, heap, and their differences
    - The lifecycle of memory: allocation → use → deallocation

### Stack Buffer Overflow

**What It Is**: A stack overflow occurs when a program writes more data to a buffer located on the stack than it can hold, causing adjacent memory to be overwritten. This can corrupt important data like return addresses, allowing attackers to redirect program execution.

**Case Study - CVE-2024-27130 (QNAP QTS/QuTS hero Stack Overflow)**:

- **The Bug**: QNAP's QTS and QuTS hero operating systems contained multiple buffer copy vulnerabilities where unsafe functions like `strcpy()` were used to copy user-supplied input into fixed-size stack buffers without proper size validation. The vulnerabilities affected the web administration interface and file handling components. [POC](https://github.com/watchtowrlabs/CVE-2024-27130)
- **The Attack**: An authenticated remote attacker could send specially crafted requests with oversized input to vulnerable endpoints. The unchecked data would overflow stack buffers, corrupting adjacent memory including return addresses and saved frame pointers.
- **The Impact**: Remote code execution with the privileges of the QNAP system service. The attacker could gain complete control over the NAS device, accessing stored data, pivoting to other network resources, or installing persistent backdoors.
- **The Fix**: QNAP released QTS 5.1.7.2770 build 20240520 and QuTS hero h5.1.7.2770 build 20240520 in May 2024, replacing unsafe string copy functions with bounds-checked alternatives and implementing additional input validation.
- **Why It Matters**: Stack overflows remain common in embedded devices and NAS systems running legacy C/C++ code. They're particularly dangerous in internet-facing administration interfaces and often provide the initial foothold for sophisticated attack chains against enterprise infrastructure.

### Use-After-Free (UAF)

**What It Is**: A use-after-free vulnerability occurs when a program continues to use a pointer after the memory it points to has been freed. This creates a "dangling pointer" that can be exploited by carefully controlling heap allocations to place attacker-controlled data where the freed object once lived.

**Case Study - CVE-2024-2883 (Chrome ANGLE Use-After-Free)**:

- **The Bug**: Google Chrome's ANGLE (Almost Native Graphics Layer Engine) component, which translates OpenGL ES API calls to DirectX, Vulkan, or native OpenGL, contained a use-after-free vulnerability. The bug occurred when WebGL contexts were destroyed while still referenced by pending graphics operations, leaving dangling pointers to freed graphics objects.
- **The Attack**: An attacker could create a malicious HTML page with specially crafted WebGL JavaScript code that triggered rapid creation and destruction of graphics contexts. By carefully timing these operations, the attacker could cause ANGLE to reference already-freed memory. Using heap spray and heap feng-shui techniques, the attacker could control the contents of the freed memory region.
- **The Impact**: Remote code execution via a crafted web page with no user interaction beyond visiting the page. By placing a fake object in the freed memory location, the attacker could hijack control flow and execute arbitrary code in the renderer process. This could be chained with sandbox escape exploits for full system compromise.
- **The Fix**: Google Chrome 123.0.6312.86 (released March 2024) fixed the vulnerability by implementing proper lifetime management for graphics objects and adding reference counting to prevent premature destruction of objects still in use.
- **Why It Matters**: UAF vulnerabilities are particularly dangerous in browsers and complex C++ applications where object lifetimes are difficult to track. Graphics subsystems like ANGLE are attractive targets because they handle untrusted content and have complex state management. They're a favorite target for advanced attackers because they offer fine-grained control over program execution.

### Heap Buffer Overflow

**What It Is**: Similar to stack overflows, heap overflows occur when a program writes beyond the boundaries of a dynamically allocated buffer on the heap. Instead of corrupting stack frames, heap overflows typically corrupt heap metadata or adjacent objects, leading to memory corruption when the heap allocator later processes the corrupted structures.

**Case Study - CVE-2023-4863 (libWebP Heap Buffer Overflow)**:

- **The Bug**: The libWebP library, used by Chrome, Firefox, Edge, and many other applications for processing WebP images, contained a heap buffer overflow in the `BuildHuffmanTable()` function. When parsing specially crafted WebP images with malformed Huffman coding data, the function would write beyond the allocated buffer boundaries. [POC](https://github.com/mistymntncop/CVE-2023-4863)
- **The Attack**: An attacker could embed a malicious WebP image in a web page or send it via messaging apps. When the victim's browser or application attempted to decode the image, the overflow would occur. The attacker could control the overflow data to corrupt heap metadata and adjacent objects.
- **The Impact**: Remote code execution with no user interaction beyond viewing a web page or opening an image. Exploited as a zero-day in the wild before public disclosure. The vulnerability affected billions of devices across multiple platforms (Windows, macOS, Linux, Android, iOS).
- **The Fix**: libWebP 1.3.2 (September 2023) fixed the bounds checking in `BuildHuffmanTable()`. Chrome 116.0.5845.187, Firefox 117.0.1, and other affected software released emergency patches.
- **Why It Matters**: Heap buffer overflows in image parsers are particularly dangerous because images are ubiquitous and processed automatically. This vulnerability demonstrated the supply chain risk of widely-used libraries - a single bug in libWebP affected dozens of major applications. Modern heap exploitation techniques can bypass ASLR and other protections when combined with information leaks.

### Out-of-Bounds Read (Info Leak)

**What It Is**: Reading past buffer bounds without modifying memory. Frequently used to leak pointers, object metadata, and kernel layout to defeat KASLR and build arbitrary read/write primitives.

**Case Study - CVE-2024-53108 (Linux AMDGPU Display Driver OOB Read)**:

- **The Bug**: In the AMD display driver’s EDID/VSDB parsing path, insufficient bounds checking allowed out-of-bounds reads when extracting identifiers, leading to slab-out-of-bounds access under KASAN.
- **The Attack**: A crafted display/EDID data stream could trigger an OOB read in kernel space. While not directly granting write primitives, the info leak can expose kernel memory contents and aid in bypassing KASLR.
- **The Impact**: Information disclosure and potential system instability.
- **The Fix**: Kernel updates tightened length validation within the AMD display capability parsing logic to ensure all reads stay within EDID buffer bounds. [DIFF](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/diff/?id=16dd2825c23530f2259fc671960a3a65d2af69bd)
- **Why It Matters**: Pure OOB reads are valuable for building reliable exploit chains (e.g., pairing with separate write primitives), especially in kernel contexts where defeating KASLR is pivotal.

### Uninitialized Memory Use

**What It Is**: Using stack/heap/pool memory before it is initialized. Contents may include stale pointers, capability flags, or structure fields.

**Case Study - CVE-2024-26581 (Linux Kernel Netfilter Uninitialized Variable)**:

- **The Bug**: The Linux kernel's netfilter subsystem contained an uninitialized variable vulnerability in the `nf_tables` component. When processing netlink messages to configure firewall rules, the `nft_pipapo_walk()` function failed to initialize a local variable before use. The uninitialized stack variable could contain residual data from previous function calls, including kernel pointers and sensitive memory addresses. [POC](https://sploitus.com/exploit?id=A4D521EE-225F-57D5-8C31-9F1C86D066B6)
- **The Attack**: An attacker with `CAP_NET_ADMIN` capability (obtainable via unprivileged user namespaces on many distributions) could trigger specific netfilter operations that caused the uninitialized variable to be read and copied back to userspace through netlink responses. By repeatedly triggering the vulnerable code path and analyzing returned data, an attacker could extract kernel memory contents including heap/stack addresses.
- **The Impact**: Information disclosure leading to KASLR (Kernel Address Space Layout Randomization) bypass. The leaked kernel addresses could then be used to reliably exploit other kernel vulnerabilities, turning potential denial-of-service bugs into privilege escalation or code execution. This vulnerability was particularly dangerous when combined with other netfilter bugs for full LPE chains.
- **The Fix**: Linux kernel 6.8-rc1 (February 2024) added proper initialization of the variable using designated initializers: `struct nft_pipapo_match *m = NULL;` and added explicit zero-initialization for stack structures. Additionally, the patch enabled stricter compiler warnings (`-Wuninitialized`) for the netfilter subsystem.
- **Why It Matters**: Uninitialized memory reads are frequently the first stage in exploit chains, providing the entropy reductions needed to bypass modern mitigations like KASLR. They're particularly valuable in kernel exploitation where defeating ASLR is essential for reliable exploitation. The combination of unprivileged user namespaces granting `CAP_NET_ADMIN` and uninitialized memory leaks in netfilter makes this class of vulnerability accessible to local attackers without requiring root privileges.

### Reference Counting Bugs

**What It Is**: Incorrect increments/decrements or overflows in reference counters controlling object lifetime (filesystems, networking, drivers).

**Case Study - CVE-2022-32250 (Linux Netfilter nf_tables Use-After-Free)**:

- **The Bug**: The Linux kernel's netfilter subsystem (`net/netfilter/nf_tables_api.c`) had a reference counting error in the nf_tables component. An incorrect `NFT_STATEFUL_EXPR` check failed to properly track expression object lifetimes during rule updates, leading to premature object destruction while references still existed.
- **The Attack**: A local attacker with the ability to create user/network namespaces (unprivileged on many distributions) could manipulate nf_tables firewall rules to trigger the reference counting bug. By creating and modifying stateful expressions in specific sequences, the attacker could cause the kernel to free an object while it was still being referenced, creating a use-after-free condition.
- **The Impact**: Local privilege escalation from any user to root on systems allowing unprivileged namespaces (default on Ubuntu, Debian, and others). The UAF primitive could be exploited for arbitrary kernel memory read/write, typically used to modify credentials or overwrite function pointers. Affected Linux kernels from 4.1 (2015) through 5.18.1 (2022). [Public exploit available](https://github.com/theori-io/CVE-2022-32250-exploit).
- **The Fix**: Linux kernel 5.18.2+ corrected the reference counting logic for stateful expressions, ensuring proper lifetime tracking during rule operations. The patch added explicit reference count increments/decrements at the appropriate points in the code path.
- **Why It Matters**: Reference counting bugs are subtle and can lead to premature free → use-after-free conditions, or refcount overflow → free while references remain. They're particularly dangerous in kernel code where object lifetime management is critical. The accessibility via unprivileged user namespaces made this vulnerability particularly impactful for local privilege escalation.

### NULL Pointer Dereference

**What It Is**: Dereferencing a NULL pointer in privileged code. While modern systems typically prevent user-space mapping of NULL pages, kernel NULL pointer dereferences remain a significant source of denial-of-service vulnerabilities and can occasionally enable privilege escalation in specific contexts.

**Case Study - CVE-2023-52434 (Linux SMB Client NULL Pointer Dereference)**:

- **The Bug**: The Linux kernel's SMB (CIFS) client implementation contained a NULL pointer dereference vulnerability in the `smb2_parse_contexts()` function. When parsing server responses during SMB2/SMB3 connection establishment, the code failed to properly validate offsets and lengths of create context structures before dereferencing pointers. Malformed create contexts with invalid offsets could cause the kernel to access unmapped memory addresses, triggering a NULL pointer dereference.
- **The Attack**: A malicious or compromised SMB server could send crafted SMB2_CREATE responses with invalid create context structures. When a Linux client attempted to mount the share or access files, the kernel would parse these malformed contexts without proper bounds checking. The vulnerability was triggered during the mount operation or file access, requiring only that a user attempt to connect to the malicious server.
- **The Impact**: Denial of service affecting Linux kernels from 5.3 through 6.7-rc5. The NULL pointer dereference caused an immediate kernel panic with the error "unable to handle page fault for address: ffff8881178d8cc3" in the `smb2_parse_contexts()` function. Any user with permission to mount SMB shares could trigger the vulnerability, making it exploitable in multi-user environments. CVSS Score: 8.0 (High) with attack vector: Adjacent Network, requiring low privileges and no user interaction.
- **The Fix**: Linux kernel patches (versions 5.4.277, 5.10.211, 5.15.150, 6.1.80, and 6.6.8+) added comprehensive validation of create context offsets and lengths before dereferencing. The patches ensure all pointer arithmetic stays within allocated buffer boundaries during SMB protocol parsing.
- **Why It Matters**: NULL pointer dereferences in network protocol parsers are particularly dangerous because they can be triggered remotely by malicious servers or through man-in-the-middle attacks. While modern kernel protections prevent NULL page mapping (mitigating historical privilege escalation techniques), the DoS impact remains critical for availability.

### Key Takeaways

1. **Memory corruption remains prevalent**: Despite decades of security research, memory corruption bugs continue to plague software, especially in C/C++ codebases.
2. **Defense-in-depth is essential**: Each real-world example shows attackers bypassing multiple protection mechanisms (DEP, ASLR, CET, XFG, safe-linking).
3. **Modern mitigations raise the bar but don't eliminate risk**: While technologies like CET shadow stack and safe-linking make exploitation harder, determined attackers continue to find bypasses.
4. **Root causes are similar, but contexts differ**: Stack, heap, and UAF bugs share common root causes (inadequate bounds checking, lifetime management) but require different exploitation techniques.
5. **Legacy components remain vulnerable**: Years-old vulnerabilities in office parsers and archive handlers continue to be exploited due to slow patching.

### Discussion Questions

1. What commonalities do you see across the memory corruption vulnerability classes covered today?
2. Why do memory corruption vulnerabilities persist despite decades of research into memory-safe languages?
3. How do the exploitation techniques differ between stack, heap, and UAF vulnerabilities?
4. What defense mechanisms were bypassed in each example, and what does that tell us about the current state of exploit mitigation?
5. How do reference counting bugs lead to use-after-free conditions, and why are they particularly difficult to detect?
6. What role do information leaks (like OOB reads and uninitialized memory) play in modern exploit chains?

