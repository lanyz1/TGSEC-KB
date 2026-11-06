## 四件套（全量扫）

1. **全量清点**：`find <技能树> -name SKILL.md` 计数 + 按分类计数。
2. **★撞名扫描**：收集各 SKILL.md 父目录基名做 Counter；count>1 = 裸名 `skill_view(name)` 报 **Ambiguous 拒载**（实测铁证）。
   - 修：不动官方件；测绘/自铸件加 `-processing-pro` 后缀（先例 `pdf`→`pdf-processing-pro`；同批 `docx`/`xlsx` 消歧）。
   - **dir 名 + frontmatter `name:` 双改**；改完两个名字各实弹一发（裸名→官方件、新名→测绘件）。
3. **污染扫描**：树内不得有 `*.bak*`；同步脚本备份必须落树外。
4. **frontmatter 体检**：头 2KB 内须有 `name:`+`description:`，缺则补。
5. **名实不符**（dir 基名≠frontmatter name，如 mobile-reverse=移动端逆向）**不用修**：英文名与中文显示名双通道都能直调。

