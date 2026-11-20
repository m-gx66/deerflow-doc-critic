# Critic 评测集

这是一个面向 DeerFlow 文档评审链路的 **critic 子 agent 评测集**，用于衡量 critic
在固定输入下的判断能力，而不是整条链路的端到端效果。

把 critic 单独拿出来测，是为了避免“文档解析错误”和“评审判断错误”混在一起，
让漏报和误报都能归因到具体环节。

## 数据集构成

- 共 20 条用例：15 条带标准问题，5 条 clean。
- 错误类型覆盖：数字排序、日期、时间、温度、单位、百分比、加法、单位换算、
  前后矛盾、数量不一致、笔记失真、无依据结论。
- 每条标准问题有一个**逐字 anchor**，以及 `type` 和 `severity`。
- clean 用例的 `expected` 为空数组，只用于统计误报。
- `case_19`、`case_20` 是“笔记保真”用例：标准 anchor 在**笔记**里，不在原文里。

## 目录结构

```text
eval/
  README.md
  README.en.md                 # 英文版
  cases.jsonl                  # 20 条用例与标准答案
  cases.csv                    # 同内容的表格版
  results_baseline.csv         # 只给笔记：逐条 TP/FP/FN
  results_improved.csv         # 原文+笔记：逐条 TP/FP/FN
  results_summary.json         # 汇总 precision / recall / F1
  fixtures/
    case_01.txt ... case_20.txt
  notes/
    case_19.txt
    case_20.txt
  runs/
    baseline/
      case_01.json ... case_20.json
    improved/
      case_01.json ... case_20.json
```

## 快速开始

1. 把整个目录复制到 `~/deer-flow/eval/`。
2. `case_01`–`case_18` 用 doc-processor 生成笔记；`case_19`、`case_20` 已有笔记。
3. 基线组：critic 只拿笔记，输出保存为 `runs/baseline/<case_id>.json`。
4. 改进组：critic 拿“原文 + 笔记”，输出保存为 `runs/improved/<case_id>.json`。
5. 按下面的匹配规则统计 TP/FP/FN，计算 precision、recall、F1。

## Prompt 模板

基线（只给笔记）：

```text
调用 critic 子 agent，只审查下面的笔记，不要调用 doc-processor，不要修改文件。
【任务要求】<case.task>
【笔记】<doc-processor 输出>
只输出 JSON：
{"verdict":"pass 或 revise","issues":[{"severity":"blocker 或 major 或 minor","anchor":"原文逐字引用","problem":"问题","suggest":"建议"}]}
```

改进组（原文 + 笔记）：

```text
调用 critic 子 agent，只审查下面的内容，不要调用 doc-processor，不要修改文件。
【任务要求】<case.task>
【原文】<fixtures/case_XX.txt 全文>
【笔记】<doc-processor 输出>
只输出 JSON：
{"verdict":"pass 或 revise","issues":[{"severity":"blocker 或 major 或 minor","anchor":"原文逐字引用","problem":"问题","suggest":"建议"}]}
```

两组的模型、温度、prompt 措辞、JSON schema、`max_turns`、timeout 必须完全一致，
唯一变化是输入里有没有【原文】。

## 输出契约

```json
{
  "verdict": "pass 或 revise",
  "issues": [
    {
      "severity": "blocker 或 major 或 minor",
      "anchor": "原文逐字引用",
      "problem": "问题描述",
      "suggest": "修改建议"
    }
  ]
}
```

规则：

- `issues` 只放真实存在的问题；“没发现问题”不要写进 `issues`。
- `anchor` 必须是连续的逐字引用，不能写成结构化摘要。
- `verdict=pass` 时 `issues` 必须为空。
- JSON 解析失败记为 `invalid`，不能算 `pass`。

## 匹配与指标

匹配前先归一化：NFKC、折叠连续空白、去首尾空格。

- 每条 expected 最多匹配一条 critic issue。
- 同一 expected 被多条 issue 命中时，只算 1 个 TP，其余记 FP/duplicate。
- critic 多报的 issue 记 FP。
- 没被命中的 expected 记 FN。

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 * precision * recall / (precision + recall)
```

clean 用例 `expected=0`，recall 记 `N/A`，但仍参与 precision 的 FP 统计。

## 当前结果（去重版）

| 组别 | TP | FP | FN | precision | recall | F1 |
| --- | --- | --- | --- | --- | --- | --- |
| 只给笔记（baseline） | 12 | 16 | 3 | 42.86% | 80.00% | 55.81% |
| 原文+笔记（v2） | 15 | 6 | 0 | 71.43% | 100.00% | 83.33% |

两组 expected 总数都是 15，口径一致。

## 可复现性

- 固定模型、prompt、schema、`max_turns`、timeout 后再做对比。
- 每次 critic 的原始 JSON 保存到 `runs/<run_id>/<case_id>.json`。
- 结果表记录 `run_id`、模型、token、延迟、invalid 数量。
- 改过 prompt 就升版本号，不要和旧 `run_id` 混在一起。

## 已知局限

- 20 条样本偏小，置信区间较宽。
- 改进组同时改了“原文、范围约束、锚点契约”三件事，测的是 v2 方案整体，
  不能单独归因给“原文”。
- `case_01`–`case_18` 的原始笔记没有保存在目录里；复跑基线需要重新生成。
- 基线召回率偏高，是因为很多错误值在笔记里原样可见（天花板效应）。
- `case_04`（30 度下雪）标为语义不一致；`case_05`（apple 是苹果）是 clean。
- `case_19`、`case_20` 的 anchor 在笔记里，校验时 base 要用 `notes/` 下的文件。

## 发布注意

不要把 `.env`、带明文 API key 的 `config.yaml`、`backend/.deer-flow/` 提交到
GitHub。如果要把 prompt 公开，使用 `config.example.yaml`，并写
`api_key: $DEEPSEEK_API_KEY`。
