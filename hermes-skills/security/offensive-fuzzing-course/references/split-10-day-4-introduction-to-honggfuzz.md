## Day 4: Introduction to `Honggfuzz`

- **Goal**: Understand different fuzzing methods and when to use Honggfuzz vs AFL++.
- **Activities**:
  - _Reading_: Continue with "Fuzzing for Software Security Testing and Quality Assurance" (From 5.1.2 to 5.3.7).
  - _Online Resource_: [Honggfuzz](https://github.com/google/honggfuzz.git)
  - _Real-World Context_:
    - Honggfuzz is used in Google's continuous fuzzing infrastructure
    - [OSS-Fuzz uses Honggfuzz for many projects](https://google.github.io/oss-fuzz/getting-started/new-project-guide/)
    - OpenSSL has extensive fuzzing coverage - [see their fuzzing documentation](https://docs.openssl.org/3.2/man7/ossl-guide-introduction/)
  - _Exercise_: Fuzz OpenSSL server and private key parsing

```bash
# Install Honggfuzz
cd ~/soft && git clone --branch master --depth 1 https://github.com/google/honggfuzz.git
#sudo apt-get install -y binutils-dev libunwind-dev libblocksruntime-dev clang libssl-dev
sudo apt-get install -y binutils-dev libunwind-dev libblocksruntime-dev libssl-dev
cd honggfuzz && make -j$(nproc) && sudo make install

# Verify installation
which honggfuzz
honggfuzz --version

# Clone OpenSSL source
cd ~/tuts && git clone --branch openssl-3.1.2 --depth=1 https://github.com/openssl/openssl.git
cd openssl

# Configure OpenSSL for fuzzing (with all legacy protocols enabled for broader attack surface)
CC=/usr/local/bin/hfuzz-clang CXX="$CC"++ ./config \
  -DPEDANTIC no-shared -DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION -O0 \
  -fno-sanitize=alignment -lm -ggdb -gdwarf-4 --debug -fno-omit-frame-pointer \
  enable-asan enable-tls1_3 enable-weak-ssl-ciphers enable-rc5 enable-md2 \
  enable-ssl3 enable-ssl3-method enable-nextprotoneg enable-heartbeats \
  enable-aria enable-zlib enable-egd

# Build OpenSSL
make -j$(nproc)

# Build Honggfuzz fuzzers for OpenSSL
# Note: This uses Honggfuzz's example OpenSSL fuzzers
cat > build_fuzzers.sh << 'EOT'
#!/bin/bash
set -x
set -e
echo "Building honggfuzz fuzzers for OpenSSL"
for x in x509 privkey client server; do
    hfuzz-clang \
        -DBORINGSSL_UNSAFE_DETERMINISTIC_MODE \
        -DBORINGSSL_UNSAFE_FUZZER_MODE \
        -DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION \
        -DBN_DEBUG \
        -DLIBRESSL_HAS_TLS1_3 \
        -O3 -g \
        -DFuzzerInitialize=LLVMFuzzerInitialize \
        -DFuzzerTestOneInput=LLVMFuzzerTestOneInput \
        -I$(pwd)/include \
        -I"$HOME"/soft/honggfuzz/examples/openssl \
        -I"$HOME"/soft/honggfuzz \
        -g "$HOME/soft/honggfuzz/examples/openssl/$x.c" \
        -o "libfuzzer.openssl-memory.$x" \
        ./libssl.a ./libcrypto.a -lpthread -lz -ldl -fsanitize=address
done
EOT

chmod +x build_fuzzers.sh
./build_fuzzers.sh

# Run Honggfuzz on OpenSSL server parser
honggfuzz --input ~/soft/honggfuzz/examples/openssl/corpus_server/ \
          -- ./libfuzzer.openssl-memory.server

# Run Honggfuzz on OpenSSL private key parser
honggfuzz --input ~/soft/honggfuzz/examples/openssl/corpus_privkey/ \
          -- ./libfuzzer.openssl-memory.privkey
```

**Success Criteria**:

- Honggfuzz compiles and installs successfully
- OpenSSL builds with fuzzing support
- Fuzzers compile without errors
- Honggfuzz starts and shows coverage statistics

**What to Look For**:

- Coverage metrics increasing over time
- Crashes in the working directory
- Different crash types (heap overflow, use-after-free, etc.)

**Note**: Real OpenSSL fuzzing often runs for days/weeks. For this exercise, run for at least 30 minutes to see initial results.

### Real-World Impact: Honggfuzz Finding TLS Vulnerabilities

**Case Study - Heartbleed-Class Bugs in TLS Implementations**:

While Heartbleed (CVE-2014-0160) predates modern fuzzing tools, similar vulnerabilities continue to be found through continuous fuzzing campaigns.

**Why TLS is Hard to Fuzz**:

- **Stateful protocol**: Must complete handshake before reaching deep logic
- **Cryptographic operations**: Random values, signatures, MACs
- **Multiple versions**: TLS 1.0, 1.1, 1.2, 1.3 with different code paths
- **Extensions**: ALPN, SNI, session tickets, early data, etc.

**Honggfuzz Advantages for Network Protocols**:

```bash
# Example: Fuzzing TLS 1.3 handshake
cat > fuzz_tls13_handshake.c << 'EOF'
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <stdint.h>
#include <stddef.h>

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    SSL_CTX *ctx = SSL_CTX_new(TLS_server_method());
    if (!ctx) return 0;

    SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);
    SSL_CTX_set_max_proto_version(ctx, TLS1_3_VERSION);

    BIO *in_bio = BIO_new(BIO_s_mem());
    BIO *out_bio = BIO_new(BIO_s_mem());

    SSL *ssl = SSL_new(ctx);
    SSL_set_bio(ssl, in_bio, out_bio);
    SSL_set_accept_state(ssl);

    BIO_write(in_bio, data, size);
    SSL_do_handshake(ssl);

    SSL_free(ssl);
    SSL_CTX_free(ctx);
    return 0;
}
EOF

# Compile with Honggfuzz
hfuzz-clang fuzz_tls13_handshake.c \
    -I"$HOME"/tuts/openssl/include \
    -L"$HOME"/tuts/openssl/lib \
    -lssl -lcrypto \
    -fsanitize=address,undefined \
    -o fuzz_tls13

# Run with Honggfuzz
# TODO: use a better corpus to actually find the vulnerabilities in that code
honggfuzz --input ~/soft/honggfuzz/examples/openssl/corpus_server/ \
          --threads 8 \
          --timeout 5 \
          -- ./fuzz_tls13
```

**Real Bugs Found by Protocol Fuzzing**:

From OpenSSL and other TLS implementations:

- **Buffer overflows in certificate parsing**: X.509 extension handling
- **Use-after-free in session resumption**: Ticket lifetime management
- **Integer overflows in record layer**: Length calculations
- **State confusion bugs**: Unexpected message ordering

**Example: CVE-2022-0778 (OpenSSL Infinite Loop)**:

```bash
# Bug: Infinite loop in BN_mod_sqrt() when parsing elliptic curve points
# Discovery: Fuzzing certificate parsing with malformed EC parameters
# Impact: DoS via crafted certificate
# Fixed: OpenSSL 3.0.2, 1.1.1n

# Fuzzing campaign that found similar bugs:
honggfuzz --input certs/ \
          --dict openssl.dict \
          --threads 16 \
          --timeout 10 \
          --rlimit_rss 2048 \
          -- ./openssl x509 -in ___FILE___ -text

# Result: Timeout on malformed EC point → DoS vulnerability
```

**Fuzzing vs Real-World Exposure**:

| Metric               | Production Use (10 years) | OSS-Fuzz (1 year) |
| -------------------- | ------------------------- | ----------------- |
| Total connections    | Billions                  | 0 (pure fuzzing)  |
| Unique inputs tested | ~1,000 (typical sites)    | Trillions         |
| Edge cases covered   | <1%                       | >90%              |
| Bugs found           | ~5 (via exploits)         | ~50               |

**Key Insight**: Fuzzing explores input space breadth that production traffic never reaches.

### Key Takeaways

1. **Honggfuzz excels at complex targets**: Multi-threaded, persistent mode, hardware-assisted coverage
2. **Protocol fuzzing requires stateful harnesses**: Must reach deep code paths beyond initial parsing
3. **Continuous fuzzing prevents regressions**: OSS-Fuzz runs 24/7, catches new bugs in code changes
4. **Cryptographic code is fragile**: Parsers for ASN.1, X.509, PEM frequently have bugs
5. **Timeout detection finds DoS bugs**: Infinite loops, algorithmic complexity issues

### Discussion Questions

1. Why does fuzzing find TLS bugs that years of production use don't reveal?
2. What makes protocol fuzzing (TLS, HTTP/2, DNS) more challenging than file format fuzzing?
3. How does hardware-assisted coverage (Intel PT) improve fuzzing effectiveness?
4. What are the limitations of fuzzing for finding cryptographic vulnerabilities vs implementation bugs?

