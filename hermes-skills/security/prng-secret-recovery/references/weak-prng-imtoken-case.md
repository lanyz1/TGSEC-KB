# imToken 助记词漏洞爆料验证案例(2026-08)

## 爆料内容

「imToken Android 用 java.util.Random 生成助记词: 48 位种子 LCG,观测 2 个输出可反推全部种子;BIP39 12 词 128 位熵 + 16 位校验和,但熵实际只来自 48 位种子,2^48 GPU 数小时可爆;内部留后手,团队被搞走几百万 u。」

## 验证结论

| 项 | 判定 |
|----|------|
| java.util.Random 48 位 LCG 可爆(技术原理) | ✅ 真实,数学验证通过 |
| imToken 用了 java.util.Random | ❌ 被官方开源源码证伪 |
| imToken 实际随机源 | ✅ Rust `rand::thread_rng()` = ChaCha12 CSPRNG(OS 熵源) |
| 爆料 BIP39 细节(128+16 校验和) | ❌ 错,实际 128 熵 + 4 校验(CS = ENT/32) |
| 「留后手/被搞走几百万 u」 | ⚠️ 无任何公开证据(Google News 零相关报道) |
| 最终判定 | ❌ 针对 imToken 不成立,疑似谣言/钓鱼误归因 |

## 关键取证链(GitHub 免费 API,无需 token)

```bash
# 1. 官方组织仓库
curl "https://api.github.com/orgs/consenlabs/repos?per_page=30" | jq '.[].name'
# → token-core (Rust) → 已迁移 token-core-monorepo

# 2. 递归文件树搜助记词相关
curl "https://api.github.com/repos/consenlabs/token-core-monorepo/git/trees/main?recursive=1" | jq -r '.tree[].path' | grep -iE "mnemonic|bip39|hdwallet|rand"
# → token-core/tcx-primitive/src/rand.rs  ← 助记词生成入口

# 3. 抓助记词生成源码(决定性证据)
curl "https://raw.githubusercontent.com/consenlabs/token-core-monorepo/main/token-core/tcx-primitive/src/rand.rs"
# → use bip39::{Language, Mnemonic, MnemonicType};
#   pub fn generate_mnemonic() -> String {
#       Mnemonic::new(MnemonicType::Words12, Language::English).to_string()
#   }

# 4. 依赖确认
curl "https://raw.githubusercontent.com/consenlabs/token-core-monorepo/main/token-core/tcx-primitive/Cargo.toml"
# → tiny-bip39 = "=1.0.0"

# 5. crate 源码下载验证随机源
curl -L "https://crates.io/api/v1/crates/tiny-bip39/1.0.0/download" -o tb.crate
tar xzf tb.crate && grep -n "thread_rng\|OsRng\|fill_bytes" tiny-bip39-1.0.0/src/crypto.rs
# → use self::rand::{thread_rng, RngCore};
#   pub(crate) fn gen_random_bytes(...) { let mut rng = thread_rng(); rng.fill_bytes(&mut bytes); }
```

**结论逻辑**: Rust `rand::thread_rng()` 在 Android = ChaCha12 CSPRNG,种子来自 getrandom()/urandom,128 位全熵 → 攻击复杂度 2^128 不可行。技术原理(java.util.Random 可爆)只对真用它的钱包成立。

## 对「批量撞助记词」的最终判断

- 纯 CPU 全空间 2^48 = 千年(实测单进程 ~350-750 候选/秒)
- 爆料的「数小时」= GPU 集群/FPGA 量级(RTX4090 单卡 ~1e8-1e9/s ≈ 3 天)
- 真正实用: 补齐缺失词(缺 1 词 0.4s)/ 观测 Random 输出反推(毫秒)/ 种子部分已知(秒)
- 「被搞走几百万 u」受害者大概率是钓鱼(假 App/钓鱼站骗助记词),不是 PRNG 破解——PRNG 暴力破解是悄无声息批量扫号,不会有「一次性几百万被盗」特征
