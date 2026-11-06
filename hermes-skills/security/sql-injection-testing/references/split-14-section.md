## 真源

- 作业手法：`docs/playbooks/测绘引擎SQL注入作业手法.md`
- Tamper：`docs/playbooks/sqlmap与Tamper绕过手册.md`
- 工具：`python3 tools/ops/sqlmap_kit.py ladder --url 'https://授权/?id=1' -p id --case <案>`
- MSSQL 堆叠查询打穿链：`mssql-stacked-query-takeover` Skill（sa→CREATE LOGIN→1433直连全速外带）
- 额外注入类型参考：`EXTRA_INJECTION_TYPES.md`（LDAP/XPath/HQL/ORM/NoSQL/Header/Second-order 等非标注入）
