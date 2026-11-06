// 翻译键语言区错位验证/扫描脚本（Qavlixor translations.ts）
// 用法（项目根目录）：
//   npx --yes tsx <本脚本路径>                 # 扫描 zh 区非中文键（污染检测）
//   npx --yes tsx <本脚本路径> ui.cn.103       # 打印指定键的 7 语言值（错位检测）
//   npx --yes tsx <本脚本路径> ui.cn.102 ui.cn.103 ui.cn.97   # 多键
// 背景：2026-08-09 实锤 ui.cn.89~105 共 17 键在 7 语言区整体错位（zh 区=英文、en 区=西语…），
// grep 行号判断语言区会骗人（对象边界不是 zh→en→es 直觉顺序），必须用 getTranslation 实际调用验证。
import { getTranslation, translations } from "./lib/translations.ts";

const LANGS = ["zh-CN", "en", "es", "fr", "pt", "ru", "ar"] as const;
const cjk = /[\u4e00-\u9fff]/;
// 标点/占位键（zh 区允许非中文的合法值）
const punctOnly = /^[\s，。；、（）：""''!?·\-—…0-9A-Za-z.$%]+$/;
const placeholderKey = /^ui\.fix\.\d+$/;

const keys = process.argv.slice(2);

if (keys.length) {
  // 指定键：打印 7 语言值，检测错位
  for (const key of keys) {
    const vals = LANGS.map((l) => getTranslation(l, key));
    console.log(key, "|", vals.map((v) => v.slice(0, 20)).join(" / "));
    // 错位启发：zh 区含非中文（非标点）= 污染
    const zh = vals[0];
    if (!cjk.test(zh) && !punctOnly.test(zh) && !placeholderKey.test(key)) {
      console.log("  ⚠️ zh 区非中文（疑似错位，正确中文应为：", getTranslation("zh-CN", key), "）");
    }
  }
} else {
  // 全量扫描：zh 区非中文键（污染检测）
  let wrong = 0;
  for (const key of Object.keys(translations["zh-CN"])) {
    const v = translations["zh-CN"][key] ?? "";
    if (!cjk.test(v) && !punctOnly.test(v) && !placeholderKey.test(key)) {
      console.log("ZH非中文", key, "=", v.slice(0, 40));
      wrong++;
      if (wrong > 50) {
        console.log("...(截断，更多请去掉限制)");
        break;
      }
    }
  }
  console.log("total:", wrong);
}
