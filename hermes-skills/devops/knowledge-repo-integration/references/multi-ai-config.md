# 多AI工具配置分发模板

将安全知识仓库配置为多AI CLI工具可用的红队引擎。

## 支持的AI工具及配置方式

| AI工具 | 配置文件 | 安装方式 |
|--------|---------|----------|
| Hermes Agent | hermes/USER.md + MEMORY.md | `bash setup.sh`(提取代码块→写入~/.hermes/memories/) |
| Claude Code | claude/CLAUDE.md | `cp CLAUDE.md 项目根目录/`(自动加载) |
| OpenAI Codex | codex/instructions.md | `cp instructions.md .github/copilot/` |
| Grok CLI | grok/system.txt | `cp system.txt ~/.grok/` |
| Cursor | cursor/.cursorrules | `cp .cursorrules 项目根目录/`(自动加载) |
| Aider | aider/.aider.conf.yml | `cp .aider.conf.yml 项目根目录/` |

## Hermes setup.sh 关键逻辑

USER.md和MEMORY.md文件本身包含安装说明+代码块,不能直接cp。
setup.sh用python3 regex提取最后一个代码块内容写入:

```bash
python3 -c "
import re
with open('USER.md') as f:
    blocks = re.findall(r'\x60\x60\x60\n(.*?)\x60\x60\x60', f.read(), re.DOTALL)
if blocks:
    with open('$HOME/.hermes/memories/USER.md', 'w') as f:
        f.write(blocks[-1].strip())
"
```

脚本还需要:
- 检查 ~/.hermes 目录是否存在
- 备份原有配置(`.bak.时间戳`)
- 验证写入大小

## AGENTS.md 集成

AGENTS.md 需要告诉AI:
1. 检测自己是什么AI工具
2. 选对应的 ai-config/<tool>/ 目录
3. 按安装方式执行
4. 安装工具链(scripts/)
5. 验证安装

用户只需说「帮我安装 <仓库地址>」,AI读AGENTS.md后全自动完成。

## 配置内容通用化原则

- universal/ 是核心内容,各工具配置是格式适配
- 去掉用户个人信息(GitHub账号/TG handle/称呼偏好)
- 保留渗透方法论+攻击面优先级+工具链+知识库路径
- 风格设定(黑客风/粗口)保留但可选
