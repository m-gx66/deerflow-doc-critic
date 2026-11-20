# Agent 分工与 leader

## 分工

来源：`df/agent team harness/分工.md`

**1. 靠 system prompt 定角色**
每个 agent 有自己的一段角色设定，告诉同一个模型“你现在是谁、只能干什么、输出成什么格式”。这是分工最核心的地方。
**2. 靠输入输出定边界**
每个 agent 收的东西、吐的东西不一样。leader 收的是“原始问题”，doc agent 收的是“文档”，critic 收的是“doc agent 的结果”。数据流一分开，职责就分开了。
**3. 靠代码里的调用顺序做编排**
先调谁、后调谁、要不要循环，由你代码里的调度逻辑决定，而不是靠模型自己决定。模型只负责“在自己那一步里给出回答”。
## 分工到底靠什么落地

1. **system prompt 定角色**：doc_processor 只会“读和提炼”，critic 只会“审查”，边界写在提示词里。
2. **tools 定能力**：给每个子 agent 配不同的工具白名单，critic 甚至可以不给它文件写入权限。
3. **lead agent 的调用顺序定编排**：谁先谁后、要不要循环，是 lead agent 决策 + 你给的终止条件决定的。
4. **子 agent 是无状态的**：每次被调用都是一个全新临时上下文，不共享记忆、也不能反问用户。这是你后面想做“多 agent 记忆编排”研究时的关键约束——现在先别管记忆，先把分工跑通。

## 现在你该做的顺序

1. 先读仓库里的 Sub-Agents 文档，和 `config.example.yaml` 里注释掉的 `subagents.custom_agents` 那个完整示例块（以它为准核对 tools/skills/model 的准确写法）。
2. 照上面的结构，把 `doc_processor` 和 `critic` 两个自定义子 agent 写进 `config.yaml`。
3. 调 lead agent 的系统提示词，告诉它：遇到文档任务先派 doc_processor，结果出来再派 critic 自查。
4. 用一个真实问题端到端测一遍，确认它会依次调用两个子 agent。
- **leader（调度者）**：只做决策。输入用户问题，输出一个结构化计划，比如 `{"next": "doc", "task": "总结这份文档"}`。它自己不去读文档、也不做检查。

- **文档处理 agent**：只做“读和提炼”。输入任务 + 文档内容，输出摘要或答案。

- **critic（反思者）**：只做“检查”。输入 doc agent 的输出，输出 `{"pass": true/false, "reason": "..."}` 或修改意见。它不重新去读原始文档，只审别人交上来的东西。

用户问题
   │
   ▼
leader ──(决策)──► 文档处理 agent
   ▲                   │
   │                   ▼
   │              摘要/答案
   │                   │
   └──(返回重改)── critic ◄──┘
                       │
                       ▼
                   最终答案



**决策、执行、验证分开。小任务 leader 直做；大任务 doc 提案 + 工具执行 + critic 验收**

将文档好不好这个问题拆分成五个可测部分
- **leader**：理解任务、决定 analyze/edit、编排流程、给最终答复。
- **doc-processor**：解析原文、输出锚点笔记；编辑模式下输出 `changes`（before/after/reason），不直接写二进制。
- **确定性工具/脚本**：按 `changes` 改 docx，校验 zip 完整性和格式保留。
- **critic**：拿“原文 + changes + 输出文件信息”逐条判断 before 是否真实、after 是否满足要求，输出 verdict/issues。
- **确定性检查**：锚点是否存在、文件是否生成、zip 是否完整——这些不交给 critic。

## leader

来源：`df/agent team harness/leader/leader.md`

leader 只做三件事：接收任务 → 判断要不要交给文档处理 agent → 拿到结果后转给 critic。不要一上来做复杂规划。

关键点：

- 三个 agent 可以**共用同一个 DeepSeek V3**，用不同的 system prompt 区分角色，不用为每个 agent 单独接模型。
- leader 的输出一定要**结构化**（JSON 或 function calling），比如 `{"next_agent": "doc", "query": "..."}`，而不是自由文本再靠正则去解析。这能省掉后面大量调试时间。
- 先写死一两条简单的调度规则（比如：涉及文档的问题转给 doc），把“能路由”这个能力做出来，再考虑让模型自己决策。

调用包
  from deerflow.subagents import get_available_subagent_names, get_subagent_config

**委派不是成本优化，是结构性工具**
**预测是优化上限，护栏是守住下限**
> [图片已省略：屏幕截图 2026-11-13 180450.png]

## 路由

来源：`df/agent team harness/leader/路由.md`

def route(state):
    if state.has_uploaded_files:
        return "doc_processor"
    if state.needs_code_review:
        return "critic"
    return "direct_answer"

def doc_flow(state):
    result = call_subagent("doc-processor", state.task)
    review = call_subagent("critic", result)
    if review.has_issues:
        result = call_subagent("doc-processor", state.task, feedback=review.issues)
        review = call_subagent("critic", result)
    return final_answer(result, review)

**编排**
task(
  subagent_type="critic",
  description="审查生成结果是否满足用户需求",
  prompt=f"""
用户原始需求：
{user_request}

系统生成的草稿：
{generated_output}
"""
)

## 问题

来源：`df/agent team harness/leader/问题.md`

- **上下文污染**：leader 亲自做一个长任务，中间过程会塞满它的上下文，后面推理质量会下降，还会触发压缩。省了委派成本，却付出了质量成本。
- **串行等待**：几个互不依赖的子任务，一个 agent 只能排队做，并行能省的是 wall-clock，公式里那项经常被低估。
- **错误相关性**：让 leader 审自己写的东西，等于同一套推理逻辑自查，很容易把漏洞读成合理。独立 context 的价值是“错误去相关”，不是省钱。
- **权限隔离**：子 agent 可以被限制工具和沙箱，leader 直接做则带着全部权限和副作用。

## leader_调用的包

来源：`df/agent team harness/leader/leader_调用的包.md`

type_allowlist = sorted(set(get_available_subagent_names(
    app_config=app_config, allowed_subagents=allowed_subagents)))

runtime_limits = {}
for name in type_allowlist:
    subagent_config = get_subagent_config(name, app_config=app_config)
    if subagent_config is None:
        continue
    runtime_limits[name] = {
        "max_turns": subagent_config.max_turns,
        "timeout_seconds": subagent_config.timeout_seconds,
    }

它先拿到这次能用哪些子 agent，再逐个查它们的配置，最后生成一个 policy 字典，包含 type_allowlist（允许的类型）和 runtime_limits（每个类型的轮数和超时上限）。这个 policy 就是本次运行实际会执行的委派限制。
