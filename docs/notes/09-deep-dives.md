# Critic 深度设计与 v2/v3

## v2基于编排

来源：`df/critic机制/深/v2基于编排.md`

第一，在 doc-processor 内部切一刀，不在 agent 之间加节点。 让它先产出纯抽取层的结构化笔记——每条形如「段号/页码 + 原文引用（逐字）+ 该段主题标签」。这一层可以用代码校验：引文是否真的出现在原文对应位置，字符串匹配即可。这是白捡的召回率，零模型成本。 抽错了当场暴露，不用等 critic。

第二，critic 的审查对象要换，不是审文笔，是审锚点。 它的任务从“这份笔记写得对不对”变成“对每一条结论，它引的原文是否真的支撑这个结论”。这是个比对任务，边界清晰得多，错误也可归因。而且它必须拿到原文——只给笔记，它永远只能审内部自洽，这是我上一轮说过的死穴。

第三，我手上那个“判定权”该收走。 现在是我看完 critic 的意见，决定要不要返工。这是整条链最弱的一环：任务是我拆的，我对着自己拆的框架看意见，天然倾向于“这个不重要”。应该让 verdict 变成机械规则——critic 每条发现标 `阻断/建议`，`阻断` ≥1 就返工，我无权推翻，只能补一条“我认为误报”的记录留档。这样返工不再是主观决定。


增加一个格式审查工具  进入反工之前调用的```
validate_review 用于判定任务文件格式等死规则 ，无需让大模型思考 节省token critic输出的文本传给leader进行审查格式



1. 调 critic → review_json
2. 调 validate_review(review_json)
   ├─ ok=false → 重试 critic 一次；仍失败 → 标 invalid，结束
   └─ ok=true  → 进入下一步
3. 如果 review 有 blocker → 调 run_rework
4. 没有 blocker → 直接交付

增加一个机械返工的工具**判断要不要返工 + 执行 edit + 复审 + 落盘**，**不负责写自己的叙述文本**
critic审查完输出文本之后

- **升级输入**：critic 不再只看 doc-processor 的笔记，而是拿到“原文片段 + 笔记”，逐条判断引用是否支撑结论。这是输入编排，单元测试就能测 A/B。
- **确定性锚点校验**：每条笔记必须带段号 + 原文引用，用代码检查引用是否真的出现在原文对应位置。这是零模型成本的“白捡召回”，抽错了当场暴露。
- **两段式审查**：doc-processor 只产出带锚点的笔记，critic 只做“结论 vs 原文”的比对。职责分开，出错能归因。
- **机械返工**：critic 每条发现标 `阻断/建议`，阻断 ≥ 1 就强制返工，最多两轮。leader 没有否决权，只能补一条“我认为误报”的记录。

反工时leader不参与

**目前进度**
> [图片已省略：Pasted image 20261113205606.png]
**测试**
> [图片已省略：Pasted image 20261113210112.png]
测试线路
A: critic 基线召回率 X%，误报率 Y%
B: 原文+笔记后召回率 X'%，误报率 Y'%
C: 端到端检出率 Z%，平均返工 1.x 轮，unresolved 占比 W%
C 线还需要：

- `run_rework` 工具注册好；
- leader overlay 里写“有 blocker 时调用 run_rework”；
- `apply_changes` 能真正改草稿/文档；
- 失败路径有 `invalid` / `unresolved` 兜底。

## v3基于critic判断能力与机制

来源：`df/critic机制/深/v3基于critic判断能力与机制.md`

**改进critic agent的判断机制 
去做前后对比 体现召回率的提升**

**1. Rubric-first（先出检查清单，再逐条核对）**  
接到任务后，先根据用户需求生成一份验收清单，比如“是否统计了签到人数 / 是否列出缺勤名单 / 数字是否与原始数据一致”，然后让 critic 逐条判定。相比直接问“有没有问题”，这种结构化的检查更不容易漏项。实现简单，提升通常明显，适合做第一个改进。

**2. 工具级验证（用测试/lint 代替模型猜）**  
对代码任务，不要只让 critic 读代码，而是真的跑测试、类型检查、lint，把结果作为证据喂给它。模型只负责解释“这个失败是否违反用户需求”。这能显著降低幻觉，也更容易讲清楚“为什么可信”。

**3. 记忆增强（检索历史失败案例）**  
把过去 critic 漏掉或误判的案例存起来，下次遇到相似需求时检索出来，作为“已知失败模式”放进上下文。这正好接上你想做的多 agent 记忆编排，而且能做消融：只加记忆、只改 rubric、两者都加，各提升多少。

**4. 多轮/多评审聚合**  
生成 → critic → 修改 → 再 critic，最多 N 轮；或者用两个不同侧重点的 critic（一个查需求覆盖，一个查事实/代码正确性）投票。成本高，但能讲“收敛策略”和“何时停止”。

router（有附件→doc，代码→code，其他→direct）
  → generate（产出草稿）
  → critic：
      1. 根据需求生成 checklist
      2. 逐条核对草稿，输出结构化 verdict
      3. 可选：检索历史失败案例 / 跑测试
  → 不通过则 revise，最多 2 轮
  → final（附 verdict 和证据）

## 基线改进为v2

来源：`df/critic机制/深/基线改进为v2.md`

**用例5**增加范围约束 （apple是苹果）解决召回率偏高 模型误报
> [图片已省略：Pasted image 20261117140239.png]

**用例14**收紧锚点契约    解决因为anchor不规范 ，导致漏计
> [图片已省略：Pasted image 20261117135942.png]
- **升级输入**：critic 不再只看 doc-processor 的笔记，而是拿到“原文片段 + 笔记”，逐条判断引用是否支撑结论。这是输入编排，单元测试就能测 A/B。
- **确定性锚点校验**：每条笔记必须带段号 + 原文引用，用代码检查引用是否真的出现在原文对应位置。这是零模型成本的“白捡召回”，抽错了当场暴露。
- **两段式审查**：doc-processor 只产出带锚点的笔记，critic 只做“结论 vs 原文”的比对。职责分开，出错能归因。
- **机械返工**：critic 每条发现标 `阻断/建议`，阻断 ≥ 1 就强制返工，最多两轮。leader 没有否决权，只能补一条“我认为误报”的记录。


**用例16**：添加原文之后，直接推翻前面结论，未加原文误报2；加了原文审查通过，误报0
**用例19**：笔记把错误数值“洗掉”
**用例20**：笔记忽略了跨段矛盾     critic 找到了正确位置，但 notes-only 让它只能做内部一致性推断，推断理由不成立；加原文后它才能指出 Q2 -10% 这个真正原因。
**用例22**：这是在说笔记的编号错了，**不是在报 3.6km=360m 的换算错误**。

## 对比试验

来源：`df/critic机制/深/对比试验.md`

- **v1**：需求符合性 prompt（就是你截图里的“修改后”）
- **v2a**：v1 + rubric-first（先生成验收清单再逐条核对）
- **v2b**：v1 + 历史失败案例记忆
- **v2c**：v1 + 工具级验证（跑测试/lint）
- **v2x**：v1 + rubric-first（先生成验收清单再逐条核对）+ 历史失败案例记忆 +工具级验证（跑测试/lint）
- **结论**：对比v1——v2xs的提升

## 读取config.yaml的代码

来源：`df/critic机制/深/读取config.yaml的代码.md`

- [registry.py](D:/deer-flow-reflexion-code-review/backend/packages/harness/deerflow/subagents/registry.py) 的 `_build_custom_subagent_config` 和 `get_subagent_names`，负责把 config 读成可用的子 agent。
- [subagents_config.py](D:/deer-flow-reflexion-code-review/backend/packages/harness/deerflow/config/subagents_config.py) 里的 `CustomSubagentConfig`，定义了每个字段。
- [builtins/__init__.py](D:/deer-flow-reflexion-code-review/backend/packages/harness/deerflow/subagents/builtins/__init__.py) 是内置 agent 的注册表，注意项目规范明确说**不要改 `BUILTIN_SUBAGENTS`**，所以自定义 agent 一律走 config.yaml。
