## 12i. 新建落地页 slug 自动生成(投手零门槛)⭐

- slug = 页面网址尾巴(`https://xeelee.top/<slug>`)。**投手不用理解 slug——留空自动生成**
- product_add: slug 为空 → `do { $slug = bin2hex(random_bytes(16)); 查重 } while(重复)`(32 位 hex 唯一); 必填校验只剩标题
- 前端: 字段改名「页面网址(选填, 留空自动生成)」+ placeholder「留空自动生成, 如 c7f39f8317」+ 🔄 随机按钮(清空输入)+ 说明行「网址尾巴, 如 xeelee.top/<这里>」

