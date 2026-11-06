## Day 5: Introduction to `Syzkaller`

- **Goal**: Begin kernel fuzzing with `Syzkaller`.
- **Activities**:
  - _Tool_: Install `Syzkaller` on a Linux VM.
  - _Online Resource_: [`Syzkaller` Documentation](https://github.com/google/syzkaller/blob/master/docs/linux/setup_ubuntu-host_qemu-vm_x86-64-kernel.md)
  - _Real-World Impact_:
    - [Syzkaller Dashboard](https://syzkaller.appspot.com/) - Shows thousands of bugs found by syzkaller
    - [syzkaller: Finding Bugs in the Linux Kernel](https://lwn.net/Articles/677764/) - Overview of syzkaller's impact
    - Many CVEs discovered: Check [syzkaller bug reports](https://syzkaller.appspot.com/upstream) for real examples
  - _Exercise_: Start fuzzing the Linux kernel with `Syzkaller`.

```bash
# Install kernel build dependencies
sudo apt update
sudo apt install -y make gcc flex bison libncurses-dev libelf-dev libssl-dev

# Clone Linux kernel (use a recent stable version)
# Check available tags: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/refs/tags
cd ~/soft && git clone --branch v6.8 --depth 1 git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git kernel

# Verify kernel version
cd kernel && git describe --tags

# Configure kernel for syzkaller
make defconfig
make kvm_guest.config

# Edit .config to enable syzkaller requirements
# Use sed or manually edit .config
sed -i 's/# CONFIG_KCOV is not set/CONFIG_KCOV=y/' .config
sed -i 's/# CONFIG_DEBUG_INFO_DWARF4 is not set/CONFIG_DEBUG_INFO_DWARF4=y/' .config
sed -i 's/# CONFIG_KASAN is not set/CONFIG_KASAN=y/' .config
sed -i 's/# CONFIG_KASAN_INLINE is not set/CONFIG_KASAN_INLINE=y/' .config
sed -i 's/# CONFIG_CONFIGFS_FS is not set/CONFIG_CONFIGFS_FS=y/' .config
sed -i 's/# CONFIG_SECURITYFS is not set/CONFIG_SECURITYFS=y/' .config
echo 'CONFIG_CMDLINE_BOOL=y' >> .config
echo 'CONFIG_CMDLINE="net.ifnames=0"' >> .config

make olddefconfig
make -j$(nproc)

# Create VM image
sudo apt install -y debootstrap
mkdir -p ~/soft/image && cd ~/soft/image
wget https://raw.githubusercontent.com/google/syzkaller/master/tools/create-image.sh -O create-image.sh
chmod +x create-image.sh
./create-image.sh --distribution trixie --feature full

# Install QEMU
sudo apt install -y qemu-system-x86

# Test VM boot (optional - verify image works)
# NOTE: You might need to run this outside of the vm, you might need to change net to e1000
cd /tmp/
sudo qemu-system-x86_64 \
    -m 2G -smp 2 \
    -kernel ~/soft/kernel/arch/x86/boot/bzImage \
    -append "console=ttyS0 root=/dev/sda earlyprintk=serial net.ifnames=0" \
    -drive file=~/soft/image/trixie.img,format=raw \
    -net user,hostfwd=tcp:127.0.0.1:10021-:22 \
    -net nic,model=virtio -enable-kvm -nographic \
    -pidfile vm.pid 2>&1 | tee vm.log

# In another terminal, test SSH access
ssh -i ~/soft/image/trixie.id_rsa -p 10021 -o "StrictHostKeyChecking no" root@localhost

# Install Go
cd ~/soft
GO_VERSION="1.25.4"
wget "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz"
sudo tar -C /usr/local -xzf "go${GO_VERSION}.linux-amd64.tar.gz"
export PATH=$PATH:/usr/local/go/bin

# Add to ~/.bashrc for persistence
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc

# Verify Go installation
go version

# Clone and build syzkaller
cd ~/soft && git clone --branch master --depth 1 https://github.com/google/syzkaller.git
cd syzkaller && make -j$(nproc)

# Create syzkaller configuration
# NOTE: If you are in the vm with e1000 then you don't need network_device line
cat > my.cfg << 'EOT'
{
    "target": "linux/amd64",
    "http": "127.0.0.1:56741",
    "workdir": "/home/USER/soft/syzkaller/workdir",
    "kernel_src": "/home/USER/soft/kernel",
    "image": "/home/USER/soft/image/trixie.img",
    "sshkey": "/home/USER/soft/image/trixie.id_rsa",
    "ssh_user": "root",
    "syzkaller": "/home/USER/soft/syzkaller",
    "procs": 8,
    "type": "qemu",
    "vm": {
        "count": 3,
        "kernel": "/home/USER/soft/kernel/arch/x86/boot/bzImage",
        "cmdline": "net.ifnames=0",
        "cpu": 2,
        "mem": 2048,
        "network_device": "virtio-net-pci"
    }
}
EOT

# Replace $USER with actual username
sed -i "s/USER/$USER/g" my.cfg

# Create workdir and start syzkaller
mkdir -p workdir
# NOTE: this might take a while, run with -debug to to identify issues
sudo ./bin/syz-manager -config=my.cfg

# Access web interface
# Install text-based browser or use your regular browser
sudo apt install -y w3m w3m-img
w3m http://127.0.0.1:56741

# Or open in regular browser: http://127.0.0.1:56741
```

**Success Criteria**:

- Kernel compiles successfully with KASAN and KCOV enabled
- VM image creates without errors
- VM boots and is accessible via SSH
- Syzkaller manager starts and shows web interface
- Web interface displays fuzzing statistics

**Expected Outputs**:

- Web interface showing: exec total, crashes, coverage, etc.
- Crashes appearing in `workdir/crashes/` directory
- Kernel oops messages in VM logs

**Troubleshooting**:

- If kernel doesn't boot: Check QEMU/KVM is enabled (`lsmod | grep kvm`)
- If syzkaller can't connect: Verify SSH key permissions (`chmod 600 trixie.id_rsa`)
- If no crashes: Let run longer - kernel fuzzing takes time
- Memory issues: Reduce VM count in config if system runs out of RAM

### Real-World Impact: Syzkaller's Contribution to Kernel Security

**Case Study - CVE-2022-32250 (Linux Netfilter Use-After-Free)**:

From Week 1, you learned about this vulnerability. Here's how syzkaller discovered it:

- **Target**: `net/netfilter/nf_tables_api.c` - Linux firewall subsystem
- **Discovery Date**: May 2022
- **Fuzzing Duration**: ~72 hours from code introduction to crash
- **Root Cause**: Reference counting error in stateful expression handling

**The Discovery Process**:

```bash
# Syzkaller's approach (simplified)
# 1. System call description for netfilter operations
{
    "nfnetlink_create": {
        "protocol": "NETLINK_NETFILTER",
        "operations": ["NFT_MSG_NEWTABLE", "NFT_MSG_NEWCHAIN", "NFT_MSG_NEWRULE"]
    }
}

# 2. Syscall sequence that triggered the bug
socket(AF_NETLINK, SOCK_RAW, NETLINK_NETFILTER)
sendmsg(fd, {
    type: NFT_MSG_NEWTABLE,
    flags: NLM_F_CREATE | NLM_F_EXCL,
    data: [table_attrs]
})
sendmsg(fd, {
    type: NFT_MSG_NEWCHAIN,
    data: [chain_with_stateful_expr]
})
# Trigger: Modify stateful expression in specific sequence
sendmsg(fd, {
    type: NFT_MSG_NEWRULE,
    data: [rule_update_that_frees_expr]
})
# Use freed expression -> UAF crash

# 3. KASAN detected use-after-free
# BUG: KASAN: use-after-free in nf_tables_expr_destroy+0x12/0x20
# Read of size 8 at addr ffff888012345678 by task syz-executor/1234
```

**Why Syzkaller Found It**:

1. **Syscall coverage**: Tests all netfilter operations systematically
2. **Sequence exploration**: Tries millions of syscall orderings
3. **State tracking**: Maintains kernel state across operations
4. **KASAN integration**: Immediate detection of memory corruption
5. **Reproducibility**: Generates C reproducer for developers

**The Reproducer** (simplified):

```c
// Generated by syzkaller - minimal reproducer
#include <sys/socket.h>
#include <linux/netlink.h>
#include <linux/netfilter/nf_tables.h>

int main(void) {
    int fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_NETFILTER);

    // Create table
    send_nft_msg(fd, NFT_MSG_NEWTABLE, ...);

    // Create chain with stateful expression
    send_nft_msg(fd, NFT_MSG_NEWCHAIN, ...);

    // Trigger UAF through rule update
    send_nft_msg(fd, NFT_MSG_NEWRULE, ...);

    return 0;
}
```

**Impact**: Local privilege escalation from any user to root on systems with unprivileged user namespaces (default on Ubuntu, Debian). Public exploit available within weeks.

**Case Study - CVE-2023-32629 (Linux Netfilter Race Condition)**:

- **Target**: `net/netfilter/nf_tables_api.c` - Same subsystem, different bug
- **Bug Class**: Race condition in batch transaction handling
- **Discovery**: Syzkaller's multi-threaded syscall fuzzing
- **Impact**: Container escape + privilege escalation

**How Syzkaller Finds Race Conditions**:

```bash
# Syzkaller executes syscalls in parallel across multiple threads
# VM 1, Thread 1:
socket(AF_NETLINK, ...) → fd1
sendmsg(fd1, NFT_MSG_NEWTABLE, ...)

# VM 1, Thread 2 (simultaneous):
socket(AF_NETLINK, ...) → fd2
sendmsg(fd2, NFT_MSG_NEWTABLE, ...)  # Race on same table

# Result: Concurrent access to nf_tables objects without proper locking
# KASAN detects: use-after-free or memory corruption
```

**Syzkaller's Advantages for Kernel Fuzzing**:

1. **Syscall descriptions**: Domain-specific language for kernel APIs
2. **Coverage-guided**: Tracks code coverage to explore new paths
3. **Multi-threaded**: Finds race conditions naturally
4. **VM-based isolation**: Kernel crashes don't affect fuzzer
5. **Reproducers**: Automatic generation of minimal C reproducers
6. **Bisection**: Automatically finds introducing commit

**Analyzing a Syzkaller Bug**:

```bash
# Download reproducer from dashboard
mkdir -p ~/tuts/syz-repro && cd ~/tuts/syz-repro
wget "https://syzkaller.appspot.com/text?tag=ReproC&x=15ad9542580000" -O repro.c

# Compile and test on vulnerable kernel
gcc -pthread -o repro repro.c
./repro

# Expected: Segmentation Fault
# Kernel log shows UBSAN: array-index-out-of-bounds

# Analyze how it got identified:
https://syzkaller.appspot.com/bug?extid=77026564530dbc29b854
```

**Key Insight**: Kernel attack surface is massive. Syzkaller's systematic approach finds bugs that would take years of manual testing.

### Key Takeaways

1. **Syzkaller revolutionized kernel security**: Found 4,500+ bugs that manual testing missed
2. **Syscall fuzzing requires domain knowledge**: Must understand kernel APIs to fuzz effectively
3. **Race conditions need parallel execution**: Multi-threaded fuzzing essential
4. **VM isolation is critical**: Kernel crashes would kill the fuzzer otherwise
5. **Reproducers enable fixing**: Minimal C programs allow developers to debug quickly

### Discussion Questions

1. Why has syzkaller found thousands of kernel bugs that years of production use didn't reveal?
2. How does syzkaller's syscall description language enable effective kernel fuzzing?
3. What makes race condition detection particularly valuable in kernel fuzzing?
4. Why are networking subsystems (netfilter, inet) the most frequent sources of vulnerabilities?
5. How do user namespaces make kernel vulnerabilities more dangerous by increasing exploitability?

