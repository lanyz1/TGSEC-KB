### 22.7 Swift逆向挑战

Swift 的引入显著增加了逆向难度:
- **方法名 mangling**:Swift 编译后方法名经过 name mangling,如 `_TtC4App11ViewController`(App 模块的 ViewController 类)、`_TFC4App11ViewController5hellofS0_FT_T_`(实例方法 hello)。反汇编时需用 `swift-demangle` 还原:`swift-demangle _TtC4App11ViewController` 输出 `App.ViewController`。
- **Protocol Witness Table**:Swift 协议通过 witness table 实现动态分发,逆向时需解析 witness table 结构才能确定实际调用的方法,比 ObjC 的 `objc_msgSend` 更复杂。
- **Swift ABI 稳定性**:Swift 5 起 ABI 稳定,不同版本编译的库可互操作,但逆向工具需适配稳定的 ABI 调用约定(`swift::ABI`、`swift_retain`/`swift_release` 引用计数)。
- **2026 Swift 6.0 并发模型**:`actor` 类型的方法调度通过 `swift::runJob`、`swift_task_switch` 实现,异步方法被编译为状态机(`async/await` 展开为 `swift::AsyncContext`),逆向时需识别状态机结构才能还原控制流。`swift-demangle` 已支持 actor 与 concurrency 相关符号。

---



---
📖 本切片 2/2 结束。 本章节结束。