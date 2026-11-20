# 评测方法

目标是测量 critic 的审查能力，而不是“整条链路看起来能跑”。核心指标是 TP、FP、FN、precision、recall、F1。

## 数据集

| 数据集 | 数量 | 用途 | 是否参与调参 |
| --- | --- | --- | --- |
| `eval/tuning/` | 20 | 开发 prompt、rubric、锚点契约 | 是 |
| `eval/holdout/` | 5 | 验证泛化，只跑一次 | 否 |

调参集包含 15 条带 expected 的用例和 5 条 clean；错误类型覆盖数字排序、日期、时间、温度、单位、百分比、加法、单位换算、前后矛盾、数量不一致、笔记失真等。

hold-out 使用 doc_021–doc_025，要求跨句计算、单位换算和日期推理。

## 两组输入

| 组别 | critic 看到的输入 |
| --- | --- |
| baseline | 只给 doc-processor 的笔记/分析 |
| v2 | 原文 + 笔记/分析，并启用范围约束和锚点契约 |

除输入和 prompt 约束外，模型、JSON schema、`max_turns`、timeout 保持一致。

## 输出契约

```json
{
  "verdict": "pass 或 revise",
  "issues": [
    {
      "severity": "blocker 或 major 或 minor",
      "anchor": "原文或分析中的逐字引用",
      "problem": "问题描述",
      "suggest": "修改建议"
    }
  ]
}
```

规则：

- `issues` 只放真实存在的问题；
- `anchor` 必须是连续逐字引用；
- `verdict=pass` 时 `issues` 必须为空；
- JSON 解析失败、缺字段、anchor 找不到，记 `invalid`，不能算 `pass`。

## 匹配与去重

匹配前做 NFKC、折叠连续空白、去首尾空格。

- 每条 expected 最多匹配一条 critic issue；
- 同一 expected 被多条 issue 命中时，只算 1 个 TP，其余记 FP/duplicate；
- 多报且没对上 expected 的 issue 记 FP；
- 没被命中的 expected 记 FN。

## 指标

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 * precision * recall / (precision + recall)
expected  = TP + FN
```

clean 用例 `expected=0`，recall 记 `N/A`，但仍参与 precision 的 FP 统计。

## 当前结果

### 调参集

| 组别 | TP | FP | FN | expected | precision | recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 只给笔记 | 12 | 16 | 3 | 15 | 42.9% | 80.0% | 55.8% |
| 原文+笔记（v2） | 15 | 6 | 0 | 15 | 71.4% | 100.0% | 83.3% |

### Hold-out（原表口径）

| 组别 | TP | FP | FN | expected | precision | recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 只给笔记 | 1 | 5 | 3 | 4 | 16.7% | 25.0% | 20.0% |
| 原文+笔记（v2） | 4 | 1 | 1 | 5 | 80.0% | 80.0% | 80.0% |


## 复现

1. 固定模型、prompt、schema、`max_turns`、timeout；
2. 每组输出保存为 `runs/<split>/<run_id>/<case_id>.json`；
3. 结果表记录 `run_id`、模型、token、延迟、invalid；
4. 改过 prompt 就升版本号，不和旧 `run_id` 混用。

## 已知局限

- 调参集 20 条、hold-out 5 条，样本小，置信区间宽；
- v2 同时改了原文、范围约束、锚点契约，测的是组合方案；
- hold-out 的 expected 分母未统一；
- 机械返工未纳入主结果；
- 主要覆盖客观错误，开放语义问题的 gold label 仍不稳定。

## 后续实验

1. 增加“doc 分析写错、critic 抓出来”的 analysis-error 集；
2. 动态 rubric vs 固定 rubric；
3. 记忆编排：历史误报检索，目标是降低 hold-out 的重复 FP；
4. 异构 critic：不同模型家族的第二意见。
