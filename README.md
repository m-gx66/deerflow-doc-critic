# deerflow-doc-critic

基于 DeerFlow 的文档分析 + Critic 审查链路，以及一套可复现的评测方法。

> 本项目是对 [bytedance/deer-flow](https://github.com/bytedance/deer-flow) 的二次开发，不是 DeerFlow 上游贡献者。仓库只包含本项目的 prompt、评测集、校验脚本和 patch，不包含完整 DeerFlow 源码。

## 项目简介

这条链路解决两个问题：

1. 文档处理 agent 先把 docx/txt 转成结构化分析；
2. critic 再审查分析是否忠实于原文、计算是否正确、是否存在遗漏或矛盾。

评测重点是 critic 的判断能力，而不是“再做一个聊天机器人”。

```text
docx/txt
  -> doc-processor
       -> analysis JSON / notes
            -> critic
                 -> verdict + issues(anchor, severity, problem, suggest)
                      -> format check
                           -> TP / FP / FN / precision / recall / F1
```

### 返工闭环

上面的主流程图只到“critic 输出 issues”，因为当前评测结果只统计 critic 的审查能力，不包含返工带来的端到端变化。完整的返工设计：

```text
critic 输出 issues
  -> 筛出 severity=blocker
       -> 没有 blocker：直接交付
       -> 有 blocker：进入 doc-editor
            -> 生成 changes
                 anchor / before / after / reason_issue_id
            -> 应用 changes 到分析/文档
            -> critic 复审
                 pass -> resolved
                 仍有 blocker 且 < 2 轮 -> 再来一轮
                 >= 2 轮 -> unresolved（附剩余 issues）
```

关键约定：

- critic 的 `issues` 不只是“意见”，它就是返工指令；
- 每条 change 用 `reason_issue_id` 绑定到 critic 的一条 issue，防止越权修改；
- 只对 `blocker` 强制返工，`major/minor` 可以留到后续或由人决定；
- 两轮后仍不通过，必须返回 `unresolved`，不能静默交付；
- 返工原型已存在，但还缺稳定的 `output_path`、落盘、统一 critic prompt，所以暂不计入主结果。

## 当前状态

已完成：

- doc-processor 与 critic 的 prompt、输出契约；
- 20 条调参集（15 条带 expected，5 条 clean）；
- 5 条困难 hold-out（doc_021–doc_025，docx）；
- baseline / v2 的 TP/FP/FN 统计与 F1 汇总；
- 最小格式校验工具 `validate_review`；
- 返工状态工具`rework_guard`。

进行中：

- 兜底机制 如若遇到评审死循环或者工具反复调用失败等问题，预计token消耗到max_tokens的大半时，开始输出最终值，最终输出值应当从过往版本里找到最优一版，而不是最后一版，保证项目中至少有保底。

未来研究方向

这些是计划，不是当前结果。每条都对应一个可测指标：

1. **动态 rubric**：根据任务和原文生成 5–8 条原子检查项，对比固定 rubric 的 critic recall / precision，验证“任务条件化清单”是否比通用清单更少漏报。
2. **多 agent 记忆编排**：把历史误报、已修复问题和对应 anchor 存成可检索记忆，在相似用例上复用；指标是 hold-out 上的重复 FP 比例和 critic precision。
3. **异构 critic**：用不同模型家族做第二意见，比较同构/异构审查的 recall、precision 和误报相关性，验证“换模型”是否比“加轮数”更有效。
4. **分析错误分类**：构造“doc 分析写错”的专门数据集，区分事实错误、计算错误、遗漏、过度推断，分别测 critic 的召回率，避免只测文档错误。


## 评测设计

### 两组数据

| 数据集 | 数量 | 用途 | 是否参与调参 |
| --- | --- | --- | --- |
| `eval/tuning/` | 20 | 开发 prompt、rubric、锚点契约 | 是 |
| `eval/holdout/` | 5 | 验证泛化，只跑一次 | 否 |

调参集包含数字排序、日期、时间、温度、单位、百分比、加法、单位换算、前后矛盾、数量不一致、笔记失真等类型。hold-out 则要求跨句计算、单位换算和日期推理。

### 基线与 v2

| 组别 | 输入 |
| --- | --- |
| baseline | critic 只拿 doc-processor 的笔记/分析 |
| v2 | critic 拿“原文 + 笔记”，并启用范围约束和锚点契约 |

除输入和 prompt 约束外，模型、JSON schema、`max_turns`、timeout 保持一致。

### 匹配规则

匹配前做 NFKC、折叠连续空白、去首尾空格。然后：

- 每条 expected 最多匹配一条 critic issue；
- 同一 expected 被多条 issue 命中时，只算 1 个 TP，其余记 FP/duplicate；
- 多报且没对上 expected 的 issue 记 FP；
- 没被命中的 expected 记 FN；
- JSON 不合法、缺字段、anchor 找不到，记 `invalid`，不能算 `pass`。

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 * precision * recall / (precision + recall)
```

## 结果

### 调参集（去重后）

| 组别 | TP | FP | FN | expected | precision | recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 只给笔记（baseline） | 12 | 16 | 3 | 15 | 42.9% | 80.0% | 55.8% |
| 原文+笔记（v2） | 15 | 6 | 0 | 15 | 71.4% | 100.0% | 83.3% |

### Hold-out（原表口径）

| 组别 | TP | FP | FN | expected | precision | recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 只给笔记 | 1 | 5 | 3 | 4 | 16.7% | 25.0% | 20.0% |
| 原文+笔记（v2） | 4 | 1 | 1 | 5 | 80.0% | 80.0% | 80.0% |


## 目录结构

```text
deerflow-doc-critic/
  README.md
  .gitignore
  config.example.yaml
  prompts/
    doc-processor.md
    critic.md
    leader.md
  eval/
    README.md
    tuning/
      cases.jsonl
      fixtures/
      results_summary.json
    holdout/
      cases.jsonl
      fixtures/
      results.xlsx
  tools/
    validate_review/
    README.md
    validate_review_tool.py
    rework_guard/
    README.md
    rework_guard_tool.py
  docs/
    architecture.md
    eval-method.md
```

## 快速开始

1. 克隆 DeerFlow：

```bash
git clone https://github.com/bytedance/deer-flow.git
cd deer-flow
```

2. 复制配置并设置模型密钥：

```bash
cp config.example.yaml config.yaml
export DEEPSEEK_API_KEY=...
```

3. 把 `prompts/doc-processor.md` 和 `prompts/critic.md` 的内容填入 `subagents.custom_agents` 的 `system_prompt`。

4. 启动 DeerFlow：

```bash
docker compose -f docker/docker-compose-dev.yaml up -d
```

5. 按 `eval/README.md` 跑 tuning 和 holdout，结果写入各自的 `results_*` 文件。

## 设计取舍

- **先做 critic 单测，再做端到端**：避免 doc-processor 的抽取错误污染 critic 的召回率。
- **格式与语义分层**：`validate_review` 只检查 JSON 结构；“分析是否正确”交给 critic（或后续 judge）。
- **锚点逐字化**：`anchor` 必须是原文/分析中的连续片段，不能写成结构化摘要，否则无法定位。
- **去重计数**：同一 expected 只计一次 TP，防止“多报刷召回”。
- **hold-out 不调参**：困难用例只在最后跑一次，用来检查是否过拟合。

## 已知限制

- 调参集只有 20 条，hold-out 只有 5 条，置信区间较宽；
- v2 同时改了“原文、范围约束、锚点契约”三件事；
- hold-out 的 expected 分母还没统一；
- 机械返工仍是原型，未纳入主结果；
- 当前主要针对客观错误（日期、单位、计算），开放语义问题的 gold label 仍不稳定。

## Roadmap

1. 统一 hold-out 的 expected 计数，重算 precision/recall/F1；
2. 完成机械返工：`output_path`、最大两轮、`unresolved` 兜底；
3. 增加“doc 分析写错、critic 抓出来”的 analysis-error 用例；
4. 把调参集扩到 40–50 条，hold-out 扩到 10 条；
5. 补英文 README 和一张架构图。

## 安全

- 不要提交带明文 API key 的 `config.yaml`；
- 使用 `config.example.yaml` + `DEEPSEEK_API_KEY`；
- `.gitignore` 排除 `.env`、`config.yaml`、`runs/`、`node_modules/`、`.venv/`、日志。

## Attribution

Base project: `bytedance/deer-flow` at commit `<base-commit>`.
This repository contains the author's modifications, prompts, evaluation harness and documentation, not the upstream project itself.
