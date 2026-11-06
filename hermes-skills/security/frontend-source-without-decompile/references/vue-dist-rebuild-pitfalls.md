# Vue dist 重建工程：生产构建期的两类「静默改写」陷阱

从 dist 产物重建 Vue 原工程时，有两类缺陷**在源码文本里完全看不出来**（源码形态正确、静态 grep 零命中），
只在生产构建产物/运行期暴露。判据只能是**产物 chunk + 运行期实扫**，不是构建是否绿。

## 陷阱 1：模板 `$t('a.b.key')` 被生产构建编成 `X.value("a.b.key")`

- 症状：页面整页崩，`TypeError: X.value is not a function`，栈指向页面 chunk 的某偏移。
- 对证方法（决定性且廉价）：dev server 的转换产物是未压缩的，直接取同一文件比对：
  ```bash
  curl -s "http://127.0.0.1:5173/src/pages/x/y.vue" | grep -o '\\.\\{0,70\\}i18n\\.key\\.tail\\.\\.\\{0,50\\}'
  # dev  → label: $setup.$t('a.b.key')     ✅ 正确
  # dist → label: X.value("a.b.key")       ✗ 崩
  ```
  ⇒ 差别在**生产构建的模板编译阶段**，改模板文本里的 `$t` 形态无法规避。
- 修法：把模板里的 `$t(` 改成**脚本里真实存在的 i18n t 绑定**调用。编译器对该绑定产出 `unref(NAME)(...)`，
  `unref` 对函数是恒等 ⇒ 语义等同 `$t`。
  - 复用脚本已有的 `const { t: NAME } = ...useI18n()`；
  - 没有则用页面已有的 `import * as NS from "vue-i18n"` 注入 `const { t: __i18nT } = NS.useI18n();`；
  - 仅在 `<script setup>` 里注入（非 setup 会把 `useI18n()` 提到模块作用域 ✗）。
- 已验证：产物由 `X.value("key")` 变为 `unref(t)("key")`，构建绿，全站真缺陷 9→4 页。

## 陷阱 2：反编译器把「编译后形态」直译进模板（ref 双解包）

- 症状：`TypeError: Cannot read properties of undefined (reading 'info')`。
- 机理：原厂 `<script setup>` 用 inline 模式编译，render fn 里 ref 访问是**裸 ref**（`w.value.info.count`），
  而模板源码里写的是 `w.info.count`（Vue 自动解包）。反编译器照着 render fn 抄 ⇒ 模板里出现 `w.value.info.count`
  ⇒ 编译器再包一层 `unref(w).value.info` = `w.value.value.info` ⇒ undefined ⇒ 崩。
- 判据：模板出现 `NAME.value.` 且脚本里 `NAME` 是 `ref(...)`（或根本没有任何绑定、被错绑成图标等 import）。
- 修法（双向）：
  1. 模板回退到 Vue 源码形态：`NAME.value.X` → `NAME.X`；
  2. 脚本按**原厂 chunk** 的 setup 补上同名 ref（原厂实证：`w=H({info:{},xAxisList:[],chartsData:[…]})`，`H`=`ref`），
     并把错绑的 import 改名/删除。
- 陷阱中的陷阱：`.vue` 无 `lang="ts"` 时写 `ref<any>(...)` 会被当 JS 解析 ⇒ 运行期 `ReferenceError: any is not defined`。
  构建照样绿。**每次改完必须运行期复扫，不能只看 build_exit=0。**

## 纪律
- 定位「谁写的这个形态」必须先做**全 src ↔ 全 dist 双向比对**；只按假设写修复器会干跑 0 处（已两次证伪）。
- 修复器必须自证幂等（干跑 → `--write` → 再干跑 = 0 处）。
- 全量复扫要在**修复后**跑，并区分「真缺陷」与「AxiosError（mock 后端缺失）」两类。
