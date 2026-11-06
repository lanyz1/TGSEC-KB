# PRNG/助记词漏洞爆料验证工作流(imToken 案例)

2026-08-08 实战:验证「imToken 用 java.util.Random(48 位 LCG)生成助记词,数小时可爆」的群内爆料。
结论: 技术原理成立,但针对 imToken 的指控被官方开源源码证伪。

## 验证五步法(通用,适合任何「XX 软件/钱包用弱随机数」爆料)

1. **数学验证原理**(写 POC 复现,别信爆料描述):
   - java.util.Random = 48 位种子 LCG: `seed = (seed*0x5DEECE66D+0xB) & (2^48-1)`, `next(32)=seed>>16`
   - 从 2 个连续 next(32) 输出反推种子: 枚举 newseed 低 16 位(2^16),反解 oldseed,验证下一输出 → **O(2^16) 毫秒级**
   - 见 `scripts/java_random_break.py`(可复现,10/10 轮成功)
2. **源码取证**(找官方仓库,追到生成入口):
   - GitHub org 搜索(imToken=consenlabs)→ 找钱包核心 repo
   - 递归 trees API 找 mnemonic/bip39/hdwallet/rand 相关文件
   - 看生成入口 → 依赖链 → RNG 实现
3. **核对规范细节**(爆料者常记错基础规范 = 可信度信号):
   - BIP39: 12 词 = **128 位熵 + 4 位校验和**(CS=ENT/32,不是 16);24 词 = 256+8
   - 爆料说「128+16」→ 技术错误,专业性存疑
4. **公开证据检索**: Google News RSS 搜「目标+漏洞关键词」→ 零报道/CVE/公告 = 高度可疑
5. **结论分级**: 原理成立 ≠ 目标中招;无证据传闻(「被搞走几百万u」)→ 更可能是钓鱼/假钱包,非算法破解

## imToken 案例关键证据

- 官方 repo: `consenlabs/token-core-monorepo`(Rust 编写,"This library totally wrote in Rust")
- 助记词入口 `token-core/tcx-primitive/src/rand.rs`:
  ```rust
  pub fn generate_mnemonic() -> String {
      Mnemonic::new(MnemonicType::Words12, Language::English).to_string()
  }
  ```
- 依赖 `tcx-primitive/Cargo.toml` → `tiny-bip39 = "=1.0.0"`
- tiny-bip39 `src/crypto.rs`:
  ```rust
  use self::rand::{thread_rng, RngCore};
  pub(crate) fn gen_random_bytes(byte_length: usize) -> Vec<u8> {
      let mut rng = thread_rng();  // rand 0.8.5 = ChaCha12 CSPRNG, 种子来自 OS 熵源
      rng.fill_bytes(&mut bytes);
      bytes
  }
  ```
- 结论: 熵 = 128 位 ChaCha12 CSPRNG(Android getrandom),非 48 位 LCG,攻击复杂度仍 2^128

## 技术要点

- **LCG 反推**: 2 个连续输出 → O(2^16) 秒解;仅知最终地址(看不到中间输出)→ 2^48 暴力(派生速度 ~1e6/s 时 ~3258 天,多卡/FPGA 数小时~数天)
- **判定任何钱包 RNG 强弱**: 找 mnemonic 生成入口 → 看随机源是 `SecureRandom`/`OsRng`/`thread_rng`(好)还是 `java.util.Random`/`rand()`/`Math.random()`(坏)
- 好的 Rust 生态: bip39/tiny-bip39 crate + rand(ChaCha);坏示例: java.util.Random(48 位 LCG)

## Pitfalls

- 群内传闻 + 零公开报道 = 大概率谣言/误传,先查官方源码再下结论
- 钱包资产损失最常见根因是**钓鱼/假 App/假扩展**(imToken 公开报道全是这类),不是 PRNG 破解
- 别把「原理成立」误报为「目标中招」—— 原理和归因是两回事
- 旧版本(1.x)实现未开源时,无法完全排除,诚实说明证据边界
