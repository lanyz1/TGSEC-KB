## 2. 逐参喂参配方(报错即下一个参数名)
一个参数一次,读报错里的 `名称：X，类型：Y` 再补 X,直到进业务层。类型是 `long/String/枚举` 时按报错里的类型给真值。
```bash
for q in '' '?timestamp=1790000000000' '?timestamp=1790000000000&nonce=1'; do
  curl -sk --path-as-is -o /tmp/b -w "%{http_code}|%{size_download} " "https://<host><path>$q"; cat /tmp/b; echo
done
# 枚举型参数穷举合法字面量:?type=1..8 / ?channel=<平台代号> / ?fundCode=<大写代号>
```
- **参数命名风格会互相泄漏**:同一厂商混用 `orderNo` / `order-no` / `order_no`,报错给的才是真的。
- 报错里的**顺序就是校验顺序**,也是服务端 DTO 字段顺序 → 据此推断还有哪些未暴露参数。

