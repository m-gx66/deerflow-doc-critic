# 评测集说明

这个目录包含两组用例，分别用于“开发调参”和“留出验证”。两组必须分开统计，不能混在一起报告。

## 目录结构

```text
eval/
  README.md                 # 本文件：两组的分工与统一口径
  tuning/
    cases.jsonl             # 20 条调参用例
    fixtures/               # 原文
    notes/                  # 需要预置笔记的用例
    results_baseline.csv
    results_improved.csv
    results_summary.json
    README.md
  holdout/
    cases.jsonl             # doc_021–doc_025
    fixtures/               # 5 份 docx
    results.xlsx            # baseline / v2 明细与汇总
    README.md
```

## 两组的分工

| 目录 | 用例数 | 用途 | 是否参与调参 |
| --- | --- | --- | --- |
| `tuning/` | 20 | 开发 prompt、rubric、锚点契约；反复迭代 | 是 |
| `holdout/` | 5 | 验证泛化；只跑一次 baseline 和一次 v2 | 否 |

`tuning/` 用来“把方法调出来”，`holdout/` 用来“证明方法不是只在这 20 条上有效”。不要在看过 `holdout/` 结果后继续改 prompt 再重跑，否则它就失去了留出集的意义。

## 评测目标

评测对象是 critic 对 doc-processor 分析结果的审查能力：

1. doc-processor 先对原文做分析；
2. critic 拿到“笔记/分析”做审查；
3. 改进组额外把原文交给 critic；
4. 比较 baseline 与 v2 的 TP / FP / FN。

`tuning/` 主要是 critic 单测；`holdout/` 使用 docx，会经过 doc-processor，属于端到端 hold-out 检出率。报告时要写清楚是哪一种，不要把两者混称为“critic 召回率”。

## 运行方式

### tuning

- baseline：critic 只拿笔记；
- v2：critic 拿“原文 + 笔记”；
- 两组模型、prompt 措辞、JSON schema、`max_turns`、timeout 保持一致，唯一变化是输入里有没有原文。

### holdout

- 使用 `doc_021.docx`–`doc_025.docx`；
- 先跑一次 baseline，再跑一次 v2；
- 不根据结果改 prompt，不重复调参；
- 原始输出保存到各自的 `runs/` 目录，汇总写入 `results.xlsx`。

## 匹配规则

匹配前先归一化：NFKC、折叠连续空白、去首尾空格。

- 每条 expected 最多匹配一条 critic issue；
- 同一 expected 被多条 issue 命中时，只算 1 个 TP，其余记 FP/duplicate；
- critic 多报且没对上 expected 的 issue 记 FP；
- 没被命中的 expected 记 FN；
- JSON 不合法、缺字段、anchor 找不到，记 `invalid`，不能算 `pass`。

## 指标

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 * precision * recall / (precision + recall)
```

`expected = TP + FN`，每行的 expected 必须和这个等式一致。clean 用例的 `expected=0`，recall 记 `N/A`，但仍参与 precision 的 FP 统计。

## 当前结果

### tuning（去重版）

| 组别 | TP | FP | FN | expected | precision | recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 只给笔记 | 12 | 16 | 3 | 15 | 42.9% | 80.0% | 55.8% |
| 原文+笔记（v2） | 15 | 6 | 0 | 15 | 71.4% | 100.0% | 83.3% |

### holdout（原表口径）

当前表里 baseline 与 v2 的 expected 不一致（baseline `TP+FN=4`，v2 `TP+FN=5`），在统一分母之前不要直接横向比较两组的 recall。先确认每行的 expected 是否等于 `TP+FN`，再更新汇总。

## 复现纪律

- 固定模型、prompt、schema、`max_turns`、timeout；
- 每次输出保存为 `runs/<split>/<run_id>/<case_id>.json`；
- 改过 prompt 就升版本号，不和旧 `run_id` 混用；
- 报告时同时给出原始 `TP/FP/FN` 和百分比。

## 发布注意

不要提交 `.env`、带明文 API key 的 `config.yaml`、`backend/.deer-flow/`、`runs/` 中的敏感数据。需要公开配置时使用 `config.example.yaml`，并写 `api_key: $DEEPSEEK_API_KEY`。
