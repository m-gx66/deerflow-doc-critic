# rework_guard

`rework_guard` 是纯代码工具：不调用模型、不写文件，只判断 critic 的 review 是否允许再返工一轮。

## 职责

```text
review + round_no + max_rounds
  -> resolved：没有 blocker
  -> continue：有 blocker 且还能再改
  -> unresolved：有 blocker 但轮数用完
  -> invalid：review JSON 不合法
```

它把“还能不能继续返工”写死，把“这一轮怎么改”留给 doc-agent。

## 轮数约定

- `round_no=0`：第一次 critic 审查后，尚未返工；
- `round_no=1`：完成第 1 轮 doc edit + critic 复审后；
- `round_no=2`：完成第 2 轮；
- `max_rounds=2`：最多两轮 edit；`round_no>=2` 时还有 blocker，返回 `unresolved`。

## 参数

```python
rework_guard(
    review_json='{"verdict":"revise","issues":[...]}',
    round_no=0,
    max_rounds=2,
)
```

## 返回

```json
{
  "status": "continue",
  "needs_rework": true,
  "round_no": 0,
  "max_rounds": 2,
  "next_round": 1,
  "blockers": [...],
  "remaining_issues": [...],
  "unresolved": [],
  "errors": []
}
```

状态：

- `resolved`：没有 blocker，可以交付；`remaining_issues` 里是 major/minor，可附带说明；
- `continue`：有 blocker，且 `round_no < max_rounds`；
- `unresolved`：有 blocker，但轮数用完，停止返工；
- `invalid`：JSON/字段不合法，不能继续。

## Leader 编排

```text
review = critic(...)
guard = rework_guard(review, round_no=0, max_rounds=2)

while guard["needs_rework"]:
    doc.edit(review.blockers)
    review = critic(revised_draft)
    guard = rework_guard(review, round_no=guard["next_round"], max_rounds=2)

if guard["status"] == "resolved":
    deliver()
else:
    report_unresolved(guard["unresolved"])
```

leader 负责调 doc/critic 子 agent，guard 只负责轮数和状态。这样 UI 里能看到 critic、doc、critic 的真实子 agent 调用，而不是一个黑盒 tool。

## 放置与注册

```text
backend/packages/harness/deerflow/tools/builtins/rework_guard_tool.py
```

```yaml
- name: rework_guard
  group: file:read
  use: deerflow.tools.builtins.rework_guard_tool:rework_guard
```

这个工具不读写文件，`group` 只需满足你部署的工具分组要求。
