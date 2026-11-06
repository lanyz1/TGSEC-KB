# ThinkPHP 3.2 源码审计要点（2026-09 实战验证）

对着拿到手的老 ThinkPHP 3.2 源码做审计时，下面几条是**已经实测过的判断**，可以省掉大量来回试探。

---

## 1. 鉴权模型：找 `extends Action`

ThinkPHP 3.2 项目通常写一个 `CommonAction` 做鉴权基类：

```php
class CommonAction extends Action{
    function _initialize(){
        $not_auth_array = array('login');                 // 只有 login 免鉴权
        if(!in_array(strtolower(ACTION_NAME), $not_auth_array)){
            $this->uid = $this->_check_login();
            if(!$this->uid){ $this->redirect('<module>/login/login'); }
        }
    }
}
```

**审计动作**：全文搜 `extends Action`。任何**直接继承框架 `Action`** 的 Controller 都绕过了鉴权基类 = 整个控制器免鉴权。

实测产出：
- 一个业务模块（`Kw`）**整个没有 `CommonAction`** → 该模块所有 action 全免鉴权
- 另外两个 Action 直接 `extends Action` → 是无意留下的**调试残留**（一个把 POST 原文追加写进 web 根 `.txt`，一个直接 `var_dump` 回显）

**注意**：`not_auth_array` 只加了 `login`，但 PHP 方法名大小写不敏感，所以走 URL 大小写变形绕不过去（`strtolower(ACTION_NAME)` 处理了）。真正的口子是「整个控制器没有基类」。

---

## 2. `DEFAULT_FILTER` 会把字符串注入全部干掉

ThinkPHP 3.2 的 `I()` 会套用全局 `DEFAULT_FILTER`（这些老项目基本都配了 `htmlspecialchars`）。

结果：

| 写法 | 是否可注入 | 原因 |
|---|---|---|
| `where("sign='{$x}'")`（字符串拼接） | ❌ | `'` 被转成 `&#039;`，SQL 退化成纯字符串 |
| `where(array('username'=>array('exp',$x)))` | ✅ | 数组结构不受标量过滤器影响，`exp` 直接拼进 SQL |

**推论**：源码里看到 `where("...'{$var}'...")` 这种拼接，**不要直接宣布 SQL 注入**，先确认 `DEFAULT_FILTER`。

实测验证方式（响应恒空 = 被过滤，而不是表为空）：
- `' OR 1=1#` / `' AND 1=2#` 布尔
- `' OR SLEEP(4)#` / `' OR SLEEP(0)#` 时间盲注
- `' UNION SELECT 'x','x'#` 定列数（1~21 列全试）
- 注释符 `#`、`-- -`、`/**/`、`/*!50000UNION*/` 各试一遍

**全部无差异 → 输入层被过滤，立刻停手，别继续换 payload。**

仍然值得打的是**数组型 `exp` 注入**，但它通常落在需要登录的后台列表页。

---

## 3. 登录逻辑里的哈希直通分支

这是老项目里反复出现的写法：

```php
$data = array_map('trim', I('post.'));
$info = D('User')->where(array('username'=>$data['username'], 'id'=>1, 'status'=>1))->find();
$pwd  = $data['password'];
if(strlen($pwd) != 32){                       // ← 关键
    $pwd = md5(md5($data['password']) . $info['salt']);
}
$isId = D('User')->is_in_user(array('where'=>array(
    'username'=>$data['username'], 'password'=>$pwd, 'id'=>1, 'status'=>1)));
```

**含义**：口令长度等于 32 时，**提交值被当作最终哈希直接比对**，`salt` 完全不参与。

**利用**：把常见口令的 md5 也当作口令投递（不需要知道 salt）。例如
`e10adc3949ba59abbe56e057f20f883e`(123456)、`21232f297a57a5a743894a0e4a801fc3`(admin)、
`0192023a7bbd73250516f069df18b500`(admin123)、`21218cca77804d2ba1922c33e0151105`(888888)、
`14e1b600b1fd579f47433b88e8d85291`(md5(md5(123456)))。

**同时注意**：`id` 被硬编码成 `1` —— **只有 1 号用户能登录后台**。所以爆破的用户名必须是主管理员那一个，猜再多别的用户名也只是白跑。

另一个副作用：`array_map('trim', I('post.'))` 会把数组型参数 `trim()` 成 `NULL`，顺带堵死了这个入口的数组注入。

---

## 4. 验证码：源码写的不算，必须实测

同一份源码里写 `if(I('vertify','','md5') != session('verify'))`，看起来必须提交 md5。**实测该站提交原文才通过**：

```
[md5] 提交 md5(ocr) -> 验证码错误    通过率 0/4
[raw] 提交 ocr 原文 -> 登录失败      通过率 4/4   ← 正确姿势
```

**方法**：用 ddddocr 识别验证码后，**「原文」和「md5」两种各提交一次**，看返回的错误文案从「验证码错误」变成「账号或密码错误」的那一种就是对的。

验证码图本身：`Image::buildImageVerify(4,1,'png',50,27)` → **4 位纯数字、50x27**，ddddocr 直接搞定。

登录接口路径要**从登录页的 HTML 里抠**（`url:"/admin/login/login.html"`），别照源码推 —— 带不带 `.html` 后缀在某些配置下行为不同。

---

## 5. 老 ThinkPHP 里其他值得一看的点

- `require_once '/vendor/xxx.php'` 这种**以 `/` 开头的绝对路径**是常见笔误（本意是相对路径），一般不可利用，但说明部署不严谨。
- `$upload->savePath = C('UPLOAD_PATH')` + `allowExts` 白名单：老版本 `Upload` 类白名单外的后缀通常真的过不去，别在 `.php.jpg` 上耗时间。
- `assert(is_array($data))`：参数是表达式不是用户串，不可利用。
- `extract($data, EXTR_OVERWRITE)`（如 `xml2array` 之类）：变量覆盖，但要先找到调用它的入口。
- 数据表前缀可从残留 SQL 里反推，例如 `INSERT INTO bd_log (...)` 说明日志表前缀是 `bd_`（与其它表可能不同前缀，因 `D()`/`M()` 可指定表名）。
