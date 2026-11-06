---
name: skill-creator
description: >-
 测绘引擎·Create new skills, modify and improve existing skills, and measure skill
 performance. Use when users want to create a skill from scratch, edit, or optimize an
 existing skill, run evals to test a skill, benchmark skill performance with variance
 analysis, or optimize a skill's description for better triggering accuracy.
owned: true
pack: survey-skill
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='skill-creator', file_path='references/full.md')`

# skill-creator（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/skill-creator/`

溯源（仅标记）：`anthropics/skills`

---

# Skill Creator

A skill for creating new skills and iteratively improving them.

At a high level, the process of creating a skill goes like this:

- Decide what you want the skill to do and roughly how it should do it
- Write a draft of the skill
- Create a few test prompts and run claude-with-access-to-the-skill on them
- Help the user evaluate the results both qualitatively and quantitatively
 - While the runs happen in the background, draft some quantitative evals if there aren't any (if there are some, you can either use as is or modify if you feel something needs to change about them). Then explain them to the user (or if they already existed, explain the ones that already exist)
 - Use the `eval-viewer/generate_review.py` script to show the user the results for them to look at, and also let them look at the quantitative metrics
- Rewrite the skill based on feedback from the user's evaluation of the results (and also if there are any glaring flaws that become apparent from the quantitative benchmarks)
- Repeat until you're satisfied
- Expand the test set and try again at larger scale

Your job when using this skill is to figure out where the user is in this process and then jump in and help them progress through these stages. So for instance, maybe they're like "I want to make a skill for X". You can help narrow down what they mean, write a draft, write the test cases, figure out how they want to evaluate, run all the prompts, and repeat.

On the other hand, maybe they already have a draft of the skill. In this case you can go straight to the eval/iterate part of the loop.

Of course, you should always be flexible and if the user is like "I don't need to run a bunch of evaluations, just vibe with me", you can do that instead.

Then after the skill is done (but again, the order is flexible), you can also run the skill description improver, which we have a whole separate script for, to optimize the triggering of the skill.

Cool? Cool.

<!-- split-index -->

## Section index

- [Communicating with the user](references/split-01-communicating-with-the-user.md)
- [Creating a skill](references/split-02-creating-a-skill.md)
- [Running and evaluating test cases](references/split-03-running-and-evaluating-test-cases.md)
- [Improving the skill](references/split-04-improving-the-skill.md)
- [Advanced: Blind comparison](references/split-05-advanced-blind-comparison.md)
- [Description Optimization](references/split-06-description-optimization.md)
- [Claude.ai-specific instructions](references/split-07-claude-ai-specific-instructions.md)
- [Cowork-Specific Instructions](references/split-08-cowork-specific-instructions.md)
- [Reference files](references/split-09-reference-files.md)
