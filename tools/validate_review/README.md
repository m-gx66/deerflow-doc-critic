# Critic 评论格式校验工具

`validate_review_tool.py` 是一个轻量的 LangChain 工具，用来检查 critic 返回的 JSON 是否符合约定格式。它只做格式校验，不判断审查结论是否正确。

## 功能

提供两个函数：

```python
validate_format(data: dict) -> bool
validate_review(review_json: str) -> dict
```

`validate_format` 检查：

- `verdict` 只能是 `pass` 或 `revise`；
- `issues` 中每条 issue 的 `severity` 只能是 `blocker`、`major`、`minor`；
- 每条 issue 的 `anchor`、`problem`、`suggest` 必须是非空字符串。

`validate_review` 先把 JSON 字符串解析成对象，再调用 `validate_format`，返回：

```json
{"ok": true, "errors": []}
```

或：

```json
{"ok": false, "errors": ["json: Expecting value: line 1 column 1 (char 0)"]}
```

## 使用示例

```python
from validate_review_tool import validate_format, validate_review

data = {
    "verdict": "revise",
    "issues": [
        {
            "severity": "blocker",
            "anchor": "1 3 4 2 6 5",
            "problem": "数字未按升序排列",
            "suggest": "改为 1 2 3 4 5 6",
        }
    ],
}

print(validate_format(data))  # True
print(validate_review(json.dumps(data, ensure_ascii=False)))
# {"ok": True, "errors": []}
```

非法 JSON：

```python
print(validate_review("not json"))
# {"ok": False, "errors": ["json: Expecting value: line 1 column 1 (char 0)"]}
```

字段缺失或枚举错误：

```python
print(validate_review('{"verdict":"fail","issues":[]}'))
# {"ok": False, "errors": ["format invalid"]}
```

## 接入 DeerFlow

把文件放到可导入的模块路径，例如：

```text
backend/packages/harness/deerflow/tools/builtins/validate_review_tool.py
```

然后在 `config.yaml` 的工具注册表中加入：

```yaml
- name: validate_review
  group: file:read
  use: deerflow.tools.builtins.validate_review_tool:validate_review
```

`group` 按你部署里的工具分组填写；这个工具本身不读写文件，示例里的 `file:read` 只是为了满足注册表格式，具体以你的 DeerFlow 版本为准。

## 它检查什么，不检查什么

检查：

- JSON 能否解析；
- `verdict` / `severity` 枚举；
- `anchor` / `problem` / `suggest` 是否非空。

不检查：

- `anchor` 是否真的出现在原文；
- `verdict=pass` 时 `issues` 是否为空；
- `issue_id` 是否重复；
- `editable`、`target`、`base` 等完整 schema；
- 审查结论在语义上是否正确。

所以它适合做**第一层格式闸门**，不能替代语义审查或锚点校验。

## 已知限制

1. `pass` 且带 issues 目前会通过，因为代码没有检查这两个字段的关系。需要的话可以加：

```python
if data["verdict"] == "pass" and data.get("issues"):
    return False
```

2. 只返回 `format invalid`，不告诉调用方具体缺了哪个字段。排查时建议单独打印 `data` 或使用更细的校验器。

3. 不校验 anchor 是否在原文中出现；锚点校验应交给单独的 `anchor_in_text` / validator。

## 定位

这是一个“最小可用”的格式校验工具，适合在 critic 输出进入评测或返工之前快速拦截坏 JSON。若要用于完整的 `target/base/sha256/edit` 链路，应升级为完整 schema 校验器。
