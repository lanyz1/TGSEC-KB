## 九、移动端存储与密钥安全

### 9.1 Android 存储攻击面
```bash
# 各存储位置速查（root设备直接读取）
/data/data/com.target/shared_prefs/*.xml     # SharedPreferences(明文!)
/data/data/com.target/databases/*.db         # SQLite(明文)
/data/data/com.target/files/                 # 内部文件
/data/data/com.target/cache/                 # 缓存(可能含响应体/图片含敏感信息)
/sdcard/Android/data/com.target/             # 外部存储(其他App可读,高风险)
# 备份提取（allowBackup=true时）
adb backup -f backup.ab com.target
abe unpack backup.ab backup.tar && tar xf backup.tar

# SQLite审查
sqlite3 /data/data/com.target/databases/app.db
.tables
SELECT * FROM users;  SELECT * FROM tokens;
```

**加密存储审计要点：**
- `EncryptedSharedPreferences`（密钥是否落在 Keystore 中、主密钥是否硬编码）
- 自实现加密是否用了**固定IV/ECB模式/硬编码密钥**（hook Cipher 验证）
- 密钥是否与用户口令可分离（如用常量而非用户密钥派生 → 提取即解密）
- 白盒密码学（White-box Crypto）：密钥混入查找表 → 静态不可提取，但**可被脚本化密钥提取攻击**（DCA/DFA 分析），仍非绝对安全

### 9.2 iOS 存储攻击面
```bash
# 越狱设备: 读取App沙箱
ls ~/Library/Application\ Support/     # 数据库/文件
ls ~/Library/Preferences/              # NSUserDefaults plist(明文)
ls ~/Documents/
# Keychain提取（kSecAttrAccessible是审计重点）
keychain_dumper 或 objection ios keychain dump

# kSecAttrAccessible安全等级（从高到低）
# kSecAttrAccessibleWhenUnlocked / AfterFirstUnlock / Always
# 数据保护等级(Data Protection): NSFileProtectionComplete 等
# 审计: 敏感token若用kSecAttrAccessibleAlways → 设备解锁前即可被读 → 高危
```
```bash
# 非越狱提取（iMazing备份解密/已登录设备）
# 重点: 检查 plist/SQLite 中是否明文存 refresh_token/密码
plutil -p ~/Library/Preferences/com.target.plist
```

### 9.3 硬编码密钥与云凭据（2026 高发）
**Quokka 2026 数据：47.8% Android / 17.6% iOS 应用硬编码密码学密钥；50+ 应用硬编码 AWS 凭据**——这是红队最高效的切入点：
```bash
# 静态扫描（jadx输出 + 二进制）
grep -rE "AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}" output_src -iR            # AWS
grep -rE "BEGIN (RSA |EC |)PRIVATE KEY|BEGIN CERTIFICATE" -R output_src # 私钥/证书
grep -rE "sk-[A-Za-z0-9]{20,}" output_src -R                            # OpenAI/LLM key
grep -rE "AIza[0-9A-Za-z_-]{35}" output_src -R                          # GCP/Firebase
grep -rE "-----BEGIN.*KEY-----" -R $(ls -d lib/*) 2>/dev/null
# 动态验证: 提取到的密钥立刻测试权限（不调用收费API前提下做最小验证）
```

