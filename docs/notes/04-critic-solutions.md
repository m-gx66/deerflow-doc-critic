# Critic 机制：解决方案

## 关于critic返回意见的文本格式

来源：`df/critic机制/df_solution/关于critic返回意见的文本格式.md`

prompt 只能要求，不能保证。评测脚本里一定要解析和校验：

import json

def parse_review(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    data = json.loads(text)
    assert data["verdict"] in ("pass", "fail")
    for issue in data.get("issues", []):
        assert issue["severity"] in ("blocker", "major", "minor")
        assert issue["location"].strip()
        assert issue["evidence"].strip()
    return data


解析失败就重试一次，提示它“上次输出不是合法 JSON，请只输出 JSON”。第二次还失败，就把这条记为 `invalid`，**不要当成 pass**。否则你的召回率会被“解析失败”悄悄污染。

## critic problem solution

来源：`df/critic机制/df_solution/critic problem solution.md`

设置最大迭代轮次

增加收敛判定：critic评审分数达标/连接两轮评审无修改-->主动退出循环，不再传回leader

增加兜底机制：达到最大循环轮次之后，输出其中评分最高文档，不再循环

uploads:
  auto_convert_documents: true
开了之后，上传 docx 时后端会用 MarkItDown 把它转成同名的 `1.md`（代码在 `utils/file_conversion.py`，输出就是 `file_path.with_suffix(".md")`），agent 直接 `read_file("/mnt/user-data/uploads/1.md")` 就能读到，完全不需要 bash。这是对文档处理 agent 最合适的方案，也避免给 agent 开 shell 权限。
