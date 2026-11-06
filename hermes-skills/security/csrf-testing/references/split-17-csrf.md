## 十五、CSRF测试检查清单

### 15.1 侦察与测绘
- [ ] 枚举全部状态改变接口（改密/改邮箱/转账/权限/删除/配置/Webhook）
- [ ] 确认认证载体：Cookie（受SameSite影响）/ Header / Web Storage
- [ ] 审计全部Set-Cookie：SameSite属性、Domain、Path、HttpOnly、Secure、__Host-前缀、Partitioned
- [ ] 判断浏览器默认行为下的Cookie携带边界（Lax/Strict/None）
- [ ] 识别CSRF防护类型：Synchronizer / Double Submit / HMAC / Referer-Origin / Header / Fetch-Metadata

### 15.2 Token测试
- [ ] 删除Token是否通过
- [ ] 空Token/等长任意值是否通过
- [ ] 其他用户/其他会话Token是否通过
- [ ] Token可预测性分析（采集样本统计熵）
- [ ] Token是否可重用（一次性验证）
- [ ] Token在Cookie/表单/Header/GET参数各位置的校验差异
- [ ] 把Token移到不同位置是否仍通过
- [ ] 多步流程各步的Token校验覆盖
- [ ] 方法条件校验绕过（_method/HEAD/OPTIONS/GET）
- [ ] Content-Type切换绕过（text/plain等）

### 15.3 SameSite与浏览器差异
- [ ] 无SameSite属性时各浏览器默认行为验证
- [ ] Lax下GET型接口（顶级导航）CSRF
- [ ] Chrome Lax+POST 2分钟窗口利用
- [ ] 方法覆盖绕过Lax（_method=GET）
- [ ] 同站Gadget（子域XSS/JSONP/DOM open redirect）
- [ ] 子域接管与父域Cookie注入
- [ ] 跨站WebSocket握手（CSWSH）
- [ ] Service Worker存在性及SameSite绕过验证
- [ ] Safari ITP / Chrome第三方Cookie淘汰对PoC的影响

### 15.4 校验绕过
- [ ] Referer缺失/空/包含匹配/正则缺陷/@符号绕过
- [ ] Origin null / 缺失 / 反射 / 多值绕过
- [ ] Open Redirect联动
- [ ] 双提交Cookie注入（子域/CRLF/Tossing/HTTP混写）
- [ ] HMAC双提交的长度扩展/算法混淆/时序
- [ ] CORS错误配置读取Token（反射Origin+credentials）
- [ ] JSONP接口泄露Token
- [ ] 自定义Header"存在即放行"缺陷

### 15.5 高级场景
- [ ] Login CSRF + 会话固定
- [ ] Logout CSRF（配合钓鱼）
- [ ] OAuth授权码CSRF（state缺失/静态/未绑定Session）
- [ ] OAuth redirect_uri校验绕过（前缀/后缀/正则/穿越/open redirect）
- [ ] 账户绑定CSRF（Account Linking）
- [ ] GraphQL mutation CSRF（text/plain/GET）
- [ ] REST PATCH/DELETE方法覆盖与批量接口
- [ ] 异步任务/Webhook/回调类接口
- [ ] 多步表单Token传递缺陷
- [ ] Service Worker劫持与缓存投毒
- [ ] CSPT2CSRF（前端路径穿越）
- [ ] AI-WAF语义混淆绕过

### 15.6 验证与报告
- [ ] 使用只读/无害参数验证（不真实删数据/转账）
- [ ] 多浏览器重复验证（Chrome/Firefox/Safari）
- [ ] 评估完整业务影响链（CSRF→接管→损失）
- [ ] 记录复现步骤与PoC（供开发修复验证）

