# 项目概览与路线

## deerflow

来源：`df/deerflow.md`

> [图片已省略：屏幕截图 2026-11-09 182657.png]
先把**leader → 文档处理 → critic → 最终答案**跑通
第一步：把 leader 跑通（最小可用版）
第二步：把 critic 跑通

启动deerflow="$PWD" UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple docker compose -f docker/docker-compose-dev.yaml up



第三步：串成一个能演示的 demo
找一个真实例子走完全流程，比如“读这份文档，总结出 X，并自查一遍”。能录一段 demo、画一张三个 agent 怎么传数据的流程图，这就算是一个能写进简历的完整版本了。

最后做好测试改进配置了一个框架”升级到“做了一个有结论的小研究”。三件事

之后再做：召回率实验
等 critic 能稳定产出了，再建一个小的评测集：准备 20–30 个“故意有错的输出”，测 critic 能抓出几个（召回率），这就是你的基线。然后做一两次改进（比如把历史纠错经验当记忆喂给 critic、改进检查规则、检索增强），记录前后数字。**这个数字才是你面试里最硬的东西。**

后续可拓展思考一下 图片处理 遇到的问题以及解决方案

DeerFlow 的子 agent 分三类：内置的（general-purpose、bash）、config.yaml 里声明的 custom_agents、以及后台 UI 管理的 managed agents。解析顺序是内置 → config.yaml custom_agents → 后台管理。doc_processor和critic属于第二类，直接写进 config.yaml 最合适。

## 步骤

来源：`df/步骤.md`

> [图片已省略：Pasted image 20261114132018.png]
**基线的配置 = 固定 schema数据结构蓝图 + 固定 rubric评分标准 + 固定模型 + 只给笔记；改进组的配置 = 前面全部不变，只把输入换成原文+笔记。** 这样测出来的差异，才能归因到编排。

> [图片已省略：Pasted image 20261114133225.png]
> [图片已省略：Pasted image 20261114133156.png]


最后记得完善更新本地的文件 及github上面的

## 部署

来源：`df/部署.md`

subagents:

  Default timeout (seconds) for built-in subagents (default: 1800 = 30 min).

  Custom agents use their own timeout_seconds (default 900) unless overridden.

  timeout_seconds: 1800

  Optional global max-turn override for all subagents. One turn is one

  model call plus the tools it runs; the turn count is converted into

  LangGraph's step budget, so this is the number of turns you actually get.

  Built-in defaults: general-purpose=150, bash=60. Leave unset to keep them.

  max_turns: 120

## 三件事

来源：`df/三件事.md`
