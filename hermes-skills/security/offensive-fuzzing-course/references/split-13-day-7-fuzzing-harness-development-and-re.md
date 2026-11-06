## Day 7: Fuzzing Harness Development and Real-World Campaigns

- **Goal**: Learn to write effective fuzzing harnesses and understand real-world fuzzing campaigns.
- **Activities**:
  - _Reading_:
    - [libFuzzer Tutorial](https://github.com/google/fuzzing/blob/master/tutorial/libFuzzerTutorial.md)
    - [OSS-Fuzz Integration Guide](https://google.github.io/oss-fuzz/getting-started/new-project-guide/)
  - _Online Resources_:
    - [Fuzzing Harness Examples](https://github.com/google/fuzzing/tree/master/tutorial)
    - [ClusterFuzz](https://google.github.io/clusterfuzz/) - Continuous fuzzing infrastructure
  - _Concepts_:
    - Harness design principles
    - In-process vs out-of-process fuzzing
    - Persistent mode optimization
    - Seed corpus curation
    - Continuous fuzzing integration

### What is a Fuzzing Harness?

A fuzzing harness is the code that:

1. Receives fuzzer-generated input
2. Prepares that input for the target API
3. Calls the target functionality
4. Handles errors/cleanup

**Example - Bad Harness vs Good Harness**:

```cpp
// BAD HARNESS: Slow, inefficient
int main(int argc, char **argv) {
    FILE *f = fopen(argv[1], "rb");  // File I/O every iteration!
    // ... read file ...
    // ... call target API ...
    fclose(f);
    return 0;
}

// GOOD HARNESS: Fast, in-process
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // Direct memory buffer, no I/O
    // Called thousands of times per second in same process
    target_api(data, size);
    return 0;
}
```

### Case Study: Writing Harness for JSON Parser

**Target**: json-c library (real-world JSON parser)

```bash
mkdir -p ~/harness_dev && cd ~/harness_dev && mkdir json_harness && cd json_harness

# Clone json-c
git clone --depth 1 https://github.com/json-c/json-c.git

cd ~/harness_dev/json_harness/json-c
export CC=clang-19
export CXX=clang++-19
export CFLAGS="-fno-sanitize-coverage=trace-cmp -fsanitize=fuzzer-no-link,address -g -O1"
export CXXFLAGS="-fno-sanitize-coverage=trace-cmp -fsanitize=fuzzer-no-link,address -g -O1"
cmake -DBUILD_SHARED_LIBS=OFF ./
make -j$(nproc)

cd ~/harness_dev/json_harness

# Create fuzzing harness
cat > fuzz_parse.c << 'EOF'
#include <json-c/json.h>
#include <stdint.h>
#include <stddef.h>

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    const char *data1 = (const char *)data;
    json_tokener *tok = json_tokener_new();
    json_object *obj = json_tokener_parse_ex(tok, data1, size);

    if (obj) {
        // Exercise different API functions to increase coverage
        json_object_to_json_string_ext(obj, JSON_C_TO_STRING_PRETTY | JSON_C_TO_STRING_SPACED);

        if (json_object_is_type(obj, json_type_object)) {
            json_object_object_foreach(obj, key, val) {
                (void)json_object_get_type(val);
                (void)json_object_get_string(val);
            }
        }

        if (json_object_is_type(obj, json_type_array)) {
            size_t len = json_object_array_length(obj);
            for (size_t i = 0; i < len; i++) {
                json_object_array_get_idx(obj, i);
            }
        }

        json_object_put(obj);
    }

    json_tokener_free(tok);
    return 0;
}
EOF

# Compile with libFuzzer
clang-19 -g -fsanitize=address,fuzzer \
    -fno-sanitize-coverage=trace-cmp \
    -I. -Ijson-c \
    fuzz_parse.c \
    json-c/libjson-c.a \
    -o fuzz_json

# Create seed corpus
mkdir -p corpus
cat > corpus/valid1.json << 'EOF'
{"name": "test", "value": 42}
EOF

cat > corpus/valid2.json << 'EOF'
[1, 2, 3, {"nested": "object"}]
EOF

cat > corpus/valid3.json << 'EOF'
{
    "string": "value",
    "number": 123,
    "boolean": true,
    "null": null,
    "array": [1, 2, 3],
    "object": {"key": "value"}
}
EOF

# Run libFuzzer, it might take a while to actually crash
./fuzz_json corpus/ -max_total_time=300 -print_final_stats=1 -max_len=10000
```

#### Harness Design Principles Applied

1. **In-process execution**: `LLVMFuzzerTestOneInput` - no fork/exec overhead
2. **Direct API targeting**: Calls `json_tokener_parse_ex` directly
3. **Coverage maximization**: Exercises multiple code paths (objects, arrays, serialization)
4. **Proper cleanup**: Frees allocated memory to avoid OOM
5. **Sanitizer-friendly**: Works with ASAN/UBSAN for bug detection

### Case Study: Fuzzing Archive Extractors

While CVE-2023-38831 was in closed-source WinRAR, let's fuzz open-source alternatives with similar architectures.

```bash
cd ~/harness_dev && mkdir archive_campaign && cd archive_campaign

# Target: libarchive (used by many archive tools)
git clone --depth 1 --branch v3.5.1 https://github.com/libarchive/libarchive.git
cd ~/harness_dev/archive_campaign/libarchive

export CC=clang-19
export CXX=clang++-19
export CFLAGS="-fno-sanitize-coverage=trace-cmp -fsanitize=fuzzer-no-link,undefined,address -g -O1"
export CXXFLAGS="-fno-sanitize-coverage=trace-cmp -fsanitize=fuzzer-no-link,undefined,address -g -O1"

cmake -DENABLE_TEST=OFF .
make -j$(nproc)

cd ~/harness_dev/archive_campaign/

cat > fuzz_archive_read.c << 'EOF'
#include "archive.h"
#include "archive_entry.h"
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    struct archive *a;
    struct archive_entry *entry;
    int r;

    a = archive_read_new();
    if (!a) return 0;

    archive_read_support_filter_all(a);
    archive_read_support_format_all(a);

    r = archive_read_open_memory(a, data, size);
    if (r != ARCHIVE_OK) {
        archive_read_free(a);
        return 0;
    }

    while (archive_read_next_header(a, &entry) == ARCHIVE_OK) {
        const char *name = archive_entry_pathname(entry);
        int64_t size = archive_entry_size(entry);
        mode_t mode = archive_entry_mode(entry);
        time_t mtime = archive_entry_mtime(entry);

        const char *linkname = archive_entry_symlink(entry);
        const char *hardlink = archive_entry_hardlink(entry);

        const void *buff;
        size_t read_size;
        int64_t offset;
        while (archive_read_data_block(a, &buff, &read_size, &offset) == ARCHIVE_OK) {
            // Just consume data, no processing needed
        }
    }

    archive_read_free(a);
    return 0;
}
EOF

# Compile harness
clang-19 -g -O1 -fsanitize=address,undefined,fuzzer \
    -fno-sanitize-coverage=trace-cmp \
    -I./libarchive/libarchive \
    fuzz_archive_read.c -o fuzz_archive \
    libarchive/libarchive/libarchive.a \
    -lz -llzma -lzstd -lxml2 -lcrypto -ldl -lpthread

# Build diverse seed corpus
mkdir -p corpus_archive

# Valid archives of different formats
# ZIP
echo "Test file" > /tmp/test.txt
zip corpus_archive/sample.zip /tmp/test.txt

# TAR.GZ
tar czf corpus_archive/sample.tar.gz /tmp/test.txt

# 7z (if available)
7z a corpus_archive/sample.7z /tmp/test.txt 2>/dev/null || true

# RAR (if available)
rar a corpus_archive/sample.rar /tmp/test.txt 2>/dev/null || true

# Archive with symlink (common bug location)
ln -sf /etc/passwd /tmp/symlink_test
tar czf corpus_archive/with_symlink.tar.gz /tmp/symlink_test 2>/dev/null || true

# Run fuzzing campaign
./fuzz_archive corpus_archive/ \
    -max_total_time=3600 \
    -timeout=30 \
    -rss_limit_mb=2048 \
    -print_final_stats=1
```

**What This Campaign Targets**:

1. **Format parsing bugs**: TAR, ZIP, RAR, 7z, etc.
2. **Compression algorithms**: gzip, bzip2, lzma, zstd
3. **Path traversal**: Symlink/hardlink handling (like CVE-2023-38831)
4. **Metadata parsing**: Timestamps, permissions, extended attributes
5. **Memory corruption**: Buffer overflows in decompression routines

**Expected Findings** (based on real OSS-Fuzz results):

- Integer overflows in size calculations
- Path traversal via symlinks
- Buffer overflows in compression codecs
- Use-after-free in error handling paths

### Key Takeaways

1. **Harness Design is Critical**: Efficient harnesses (in-process, persistent) significantly outperform naive `fork()/exec()` wrappers.
2. **Target Logic, Not Just I/O**: Good harnesses bypass CLI parsing to exercise core API logic directly (e.g., `json_tokener_parse_ex`).
3. **Seed Corpus Quality**: A diverse, minimized corpus of valid inputs accelerates code coverage discovery.
4. **Sanitizers Enable Detection**: Memory bugs (ASAN) and undefined behavior (UBSAN) are only found if the harness is compiled with them.
5. **Continuous Integration**: Tools like OSS-Fuzz automate the "find → fix → verify" loop, preventing regressions in evolved code.

### Discussion Questions

1. Why is an in-process harness (like `LLVMFuzzerTestOneInput`) orders of magnitude faster than a file-based CLI wrapper?
2. How does defining a proper seed corpus (e.g., valid JSON/ZIP files) help the fuzzer penetrate deeper into the target's logic?
3. What are the risks of "over-mocking" in a harness (e.g., bypassing too much initialization) versus "under-mocking" (doing too much I/O)?
4. How do you handle state cleanup in a persistent-mode harness to prevent false positives from memory leaks or global state pollution?
5. Why is it important to fuzz different layers of an application (e.g., the compression layer vs. the archive parsing layer) separately?

