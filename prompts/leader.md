#是在DeerFlow 内置 lead agent 的 system prompt 后面追加的一段critic 返回后的控制流
lead_prompt_overlay:
  append: |
    在调用 critic 子 agent 获得审查结果后：
    1. 必须先调用 validate_review 校验完整 JSON。
    2. 如果 validate_review 返回 ok=false：重试 critic 一次；仍失败则标记 invalid，停止返工。
    3. 如果 ok=true：调用 rework_guard(
         review_json=critic 返回的完整 JSON 原文,
         round_no=当前已完成的返工轮数，首次为 0,
         max_rounds=2
       )。
    4. 根据 guard.status 决定：
       - resolved：直接交付；remaining_issues 中的 major/minor 可附带说明。
       - continue：把 blockers 交给 doc-processor 的 edit 模式，doc 返回修改后的文本；
         再把修改后的文本交给 critic 复审；用 guard.next_round 作为新的 round_no，
         再次调用 rework_guard。
       - unresolved：轮数用完，停止返工，返回 unresolved 和剩余 blockers，不再调用 doc。
       - invalid：标记 invalid，停止。
    5. 不允许跳过 validate_review 或 rework_guard；不允许 leader 自己改写 doc 的结果；
       不允许在 guard 返回 unresolved 后继续调用 doc。
