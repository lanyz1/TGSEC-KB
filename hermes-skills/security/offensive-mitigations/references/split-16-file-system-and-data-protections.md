## File System and Data Protections

### Filesystem Protections (fs-verity & fscrypt)

- Linux:
  - fs-verity: Provides integrity protection for read-only files.
  - fscrypt: Enables filesystem-level encryption for data at rest.

### BitLocker Drive Encryption

- Windows:
  - Full disk encryption to protect data at rest.
  - Uses TPM and user credentials for encryption keys.

### Integrity Measurement Architecture (IMA) / Extended Verification Module (EVM)

- Linux:
  - Provides runtime integrity checking for files and metadata based on stored hashes.
  - Ensures files haven't been tampered with post-boot.

