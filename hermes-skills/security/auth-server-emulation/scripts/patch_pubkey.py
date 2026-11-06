import re, sys

SRC = r'C:\Users\Administrator\AppData\Local\Temp\onefile_1098872_134303721545267734\main.dll'
MY_PUB = open(r'C:\Users\Administrator\AppData\Local\Temp\my_pub.pem', 'rb').read()

data = open(SRC, 'rb').read()

# Find all PUBLIC KEY blocks and replace each with our key
pubs = list(re.finditer(rb'-----BEGIN PUBLIC KEY-----.+?-----END PUBLIC KEY-----', data, re.DOTALL))
print(f'found {len(pubs)} public keys')

new_data = data
# Replace from last to first to keep offsets valid
for m in reversed(list(pubs)):
    old = m.group(0)
    print(f'  replacing key at {hex(m.start())}, old_len={len(old)}, new_len={len(MY_PUB)}')
    if len(old) != len(MY_PUB):
        print(f'  !! LENGTH MISMATCH, aborting')
        sys.exit(1)
    new_data = new_data[:m.start()] + MY_PUB + new_data[m.end():]

# Backup original
bak = SRC + '.bak'
open(bak, 'wb').write(data)
print(f'backup saved to {bak}')

# Write patched
open(SRC, 'wb').write(new_data)
print('patched main.dll with our RSA public key (x3)')

# Verify
v = open(SRC, 'rb').read()
vpubs = list(re.finditer(rb'-----BEGIN PUBLIC KEY-----.+?-----END PUBLIC KEY-----', v, re.DOTALL))
print(f'verify: {len(vpubs)} keys now, first body starts: {vpubs[0].group(0)[27:60]}')
