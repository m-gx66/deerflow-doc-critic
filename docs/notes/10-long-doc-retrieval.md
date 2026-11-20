# 长文档检索与短文档全文

## 步骤

来源：`df/doc长文档检索短文档全文/步骤.md`

| 要素  | 必须做到                              | 验收                                           |
| --- | --------------------------------- | -------------------------------------------- |
| 数据  | 3 篇长文档，切成 chunk                   | `chunks.jsonl` 至少 50–100 条，带 id/locator/text |
| 检索  | `retrieve_chunks(query, top_k=5)` | 能按问题返回 top-5，不是 `read_file` 整篇读              |
| 集成  | 接进 doc-processor                  | 长文档走检索，短文档走全文                                |
| 评测  | 30 条问题，标好答案所在 chunk               | 能算 `recall@5`                                |
| 对照  | 全文 vs 检索                          | 两组都跑，记 recall、answer accuracy、输入 token       |
| 事故  | 一个真实失败案例                          | 现象 → 定位 → 修复 → 指标变化                          |
| 交付  | 代码 + README + demo                | 别人能按 README 跑起来                              |
