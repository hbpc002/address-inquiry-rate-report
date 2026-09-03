"""LangGraph 编排：LLM(绑定工具) <-> 工具节点 的 ReAct 循环。"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode

SYSTEM_PROMPT = (
    "你是一个企业「排班签到报表系统」的数据分析智能体，用中文回答用户关于考勤、工时、出勤率、排班的问题。\n"
    "\n"
    "# 能力\n"
    "- 优先使用提供的报表工具（query_team_ranking / query_month_summary / query_date_range / query_daily / query_efficiency / query_dashboard_stats）获取结构化数据。\n"
    "- 当现有工具无法满足自定义分析时，使用 run_sql 执行只读 SQL（仅 SELECT，数据库结构见工具说明）。\n"
    "- 先理解用户意图，必要时调用工具，再基于真实返回的数据给出结论，不要编造数字。\n"
    "\n"
    "# 输出规范\n"
    "- 回答简洁、面向管理决策，关键数字用中文呈现。\n"
    "- 当查询结果适合用图表展示（如排名、趋势、对比）时，在回答末尾附加一个 ```chart-json 代码块，内容为 ECharts 的 option JSON（需包含 title、xAxis、yAxis、series 中适用的字段）。例如：\n"
    '```chart-json\n'
    '{"title":{"text":"各班组实际工时"},"tooltip":{},"xAxis":{"type":"category","data":["甲班","乙班"]},"yAxis":{"type":"value"},"series":[{"type":"bar","data":[120,98]}]}\n'
    '```\n'
    '- 若无需图表则不输出该代码块。\n'
)

# 单轮对话内的最大工具循环次数，超出后强制收尾，避免无限调用消耗令牌
MAX_ITERATIONS = 6
# 构造给 LLM 的历史消息上限（最近 N 条），更早的工具结果压缩为摘要
MAX_HISTORY_MESSAGES = 12


def _trim_history(state: dict) -> list:
    """压缩消息历史，控制每轮发给 LLM 的上下文大小（限流 TPM 友好）。

    保留系统提示与最近的 MAX_HISTORY_MESSAGES 条消息。从头部整体裁掉最旧的
    完整消息；若裁剪边界落在 (AIMessage.tool_calls, ToolMessage) 配对中间，
    则连同挂单的 ToolMessage 一起裁掉，避免提交给模型的历史出现缺失前文的
    工具结果。
    """
    msgs = list(state["messages"])
    if len(msgs) <= MAX_HISTORY_MESSAGES:
        return msgs

    system_idx = None
    for i, m in enumerate(msgs):
        if isinstance(m, SystemMessage):
            system_idx = i
            break
    head = system_idx + 1 if system_idx is not None else 0
    start = max(head, len(msgs) - MAX_HISTORY_MESSAGES)

    if start > head:
        first_kept = msgs[start]
        if isinstance(first_kept, ToolMessage):
            # 领头的 ToolMessage 缺它所对应的 AIMessage.tool_calls，一并裁掉
            start += 1

    msgs = msgs[:head] + msgs[start:]
    # 仍超限则强制截到最近 N 条（极端情况下丢弃少量配对）
    if len(msgs) > MAX_HISTORY_MESSAGES:
        msgs = msgs[:head] + msgs[len(msgs) - MAX_HISTORY_MESSAGES:]
    return msgs


def build_graph(llm, tools):
    tool_node = ToolNode(tools)
    llm_with_tools = llm.bind_tools(tools)

    def agent(state):
        trimmed = _trim_history(state)
        return {"messages": [llm_with_tools.invoke(trimmed)]}

    # 迭代计数，防止无限循环耗尽令牌
    iteration_counter = {"n": 0}

    def route(state) -> str:
        last = state["messages"][-1]
        if not getattr(last, "tool_calls", None):
            return END
        iteration_counter["n"] += 1
        if iteration_counter["n"] >= MAX_ITERATIONS:
            return "force_finalize"
        return "tools"

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", tool_node)
    graph.add_node("force_finalize", lambda state: {"messages": [
        AIMessage(content="工具已执行多轮但结果未能收敛，基于已有信息给出以上结论。")
    ]})
    graph.add_edge("tools", "agent")
    graph.add_conditional_edges("agent", route, {"tools": "tools", "force_finalize": "force_finalize", END: END})
    graph.add_edge("force_finalize", END)
    graph.set_entry_point("agent")
    return graph.compile()


def initial_messages(question: str) -> list:
    return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]
