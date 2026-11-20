# 架构说明

本项目在 DeerFlow 之上增加了一条文档分析 + Critic 审查链路 + 返工编辑输出结果，并把“输出结果”做成可评测的 JSON，而不是只停留在自然语言回复。

## 组件

| 组件 | 职责 | 实现 |
| --- | --- | --- |
| Lead Agent | 接收任务、路由、决定是否调用子 agent | DeerFlow `lead_agent` |
| doc-processor | 读取 docx/txt，产出结构化分析或笔记 | `subagents.custom_agents.doc-processor` |
| critic | 对照任务和原文，审查分析是否正确 | `subagents.custom_agents.critic` |
| validator | 检查 JSON 格式、anchor、去重计数 | `eval/checks/` |
| eval harness | 批量跑 baseline/v2，统计 TP/FP/FN | `eval/` |

doc-processor 和 critic 都通过 DeerFlow 的 `task` 工具调用，不需要改 Lead Agent 的调度代码。

## 主流程

```text
用户任务 + docx/txt
  -> doc-processor
       -> analysis JSON
            {
              "mode": "analyze",
              "units": [
                {"id": "u1", "locator": "...", "quote": "...", "note": "..."}
              ],
              "coverage": {"sections_total": 4, "sections_covered": 4}
            }
  -> critic
       baseline: 只拿 analysis
       v2:      拿原文 + analysis
            -> {
                 "verdict": "pass | revise",
                 "issues": [
                   {
                     "severity": "blocker | major | minor",
                     "anchor": "原文/分析中的逐字引用",
                     "problem": "...",
                     "suggest": "..."
                   }
                 ]
               }
  -> validator
       -> JSON 是否合法、字段是否齐全、anchor 是否可定位
  -> eval harness
       -> TP / FP / FN / precision / recall / F1
```

## 两种评测模式

### 文档错误召回

doc-processor 输出中性笔记，不写“正确/错误/合法/非法”。critic 负责从笔记（或原文+笔记）中找文档错误。

适合回答：“critic 能不能发现原始文档里的错误？”

### 分析审查

doc-processor 直接给出计算和结论，critic 审查这份分析是否站得住。当前项目主要采用这种模式。

适合回答：“critic 能不能发现 doc 分析里的错误或过度推断？”

两种模式的 ground truth 不同，不能混用。

## 返工闭环

```text
critic issues
  -> 筛出 blocker
       -> 无 blocker：直接交付
       -> 有 blocker：doc-editor
            -> changes:
                 anchor / before / after / reason_issue_id
            -> 应用 changes
            -> critic 复审
                 pass -> resolved
                 < 2 轮 -> 再来一轮
                 >= 2 轮 -> unresolved（附剩余 issues）
```

关键约束：

- `reason_issue_id` 必须来自 critic 的 issues，防止越权修改；
- 只对 blocker 强制返工；
- 两轮后仍有 blocker，返回 `unresolved`，不能静默交付；
- 当前 `run_rework` 仍是原型，还没有稳定的 `output_path`、落盘和统一 critic prompt，所以不计入主结果。

## 设计取舍

1. **先单元测试，再端到端**：先把 critic 单独测出来，避免 doc-processor 的抽取错误污染召回率。
2. **格式与语义分层**：`validate_review` 只检查 JSON 结构，语义判断交给 critic。
3. **anchor 逐字化**：anchor 必须是连续片段，不能写结构化摘要，否则无法定位。
4. **去重计数**：每条 expected 最多匹配一次 TP，重复 issue 记 FP，防止多报刷召回。
5. **hold-out 不调参**：困难用例只在最后跑一次，用来检查是否过拟合。

## 目录映射

```text
prompts/doc-processor.md   -> doc-processor.system_prompt
prompts/critic.md          -> critic.system_prompt
eval/tuning/               -> 20 条调参集
eval/holdout/              -> 5 条困难留出集
patches/deerflow.patch     -> 对 DeerFlow 的改动
```
