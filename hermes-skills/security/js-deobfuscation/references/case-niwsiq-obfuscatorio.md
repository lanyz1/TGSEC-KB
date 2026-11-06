# 实战案例:niwsiq 企业签分发站 bundle 反混淆(2026-09-14)

## 目标
- `/static/xwMmZ0ATZmJDM4QW1789405200.js`(2,636,892 B;Vite 产物 + javascript-obfuscator 二次混淆)
- 顶层 IIFE 结束标记:`}(a0_0x2bc2,0xb1fb1));`
- 数组函数:`a0_0x2bc2`(10,404 元素);解码器:`a0_0x3656`(自定义字母表小写在前)

## 关键动作与数字(复现时对照)
1. Node eval(decFn+arrFn+IIFE) → 成功;IIFE 自旋转到正确顺序 → `arr_rotated.json`(10,404 元素)
2. 先手写 Python checksum 复刻 → **失败**(漏第一项负号,遍历全部旋转位置 0 命中);教训:跑真 IIFE
3. Python js_decode 与 Node 交叉验证:**200/200 一致**后才批量
4. acorn 找到 **3818** 个 `_0x`/`a0_0x` FunctionDeclaration;注入导出桩 → `node --check` 通过(2,999,602 B)
5. 全文 `vm.runInThisContext` 执行成功;`m5()` 第一次崩(charAt of undefined)、第二次 OK;F2 从 3 → **742** 个(惰性模块限制)
6. 两轮调用求值:第一轮纯字面量 **6410** 个;第二轮对象属性解析后合计 **22777** 个唯一调用(22774 string / 0 null / 3 other)
7. 右到左替换 **6427** 处 → deobfuscated.js;grep 直接得到 `/clientapi/app/getinfo|inhouse|webclip|checkdcode|ipa` 全接口 + 滑块验证码逻辑
8. 副产物:未解出的拼接碎片也可用上下文推断(`'5helpe'+'t'`、`'ded?ap'` 等)

## 环境要点
- Node 24:`global.navigator` 只读,需 defineProperty;`vm.runInThisContext` 顶层 var/function 进 global
- 装 acorn:`npm init -y && npm install acorn --no-audit --no-fund`
- 复杂引号命令先写脚本文件再跑

## 工作文件(留档)
/root/niwsiq/ 下:run_iife.js, run_iife2.js(加插桩), dec_test.py, find_rotation.py, cross_verify.py,
scan_calls.py, prep_inject5.py, make_bundle_dump2.py, acorn_find.js, try_full_eval.js, eval_final3.js,
apply_deobf.py, deobfuscated.js, arr_rotated.json, dec_map.json
