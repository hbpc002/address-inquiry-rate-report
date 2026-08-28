"""LangGraph 编排：LLM(绑定工具) <-> 工具节点 的 ReAct 循环。"""
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode

SYSTEM_PROMPT = """你是一个企业「排班签到报表系统」的数据分析智能体，用中文回答用户关于考勤、工时、出勤率、排班的问题。

# 能力
- 优先使用提供的报表工具（query_team_ranking / query_month_summary / query_date_range / query_daily / query_efficiency / query_dashboard_stats）获取结构化数据。
- 当现有工具无法满足自定义分析时，使用 run_sql 执行只读 SQL（仅 SELECT，数据库结构见工具说明）。
- 先理解用户意图，必要时调用工具，再基于真实返回的数据给出结论，不要编造数字。

# 输出规范
- 回答简洁、面向管理决策，关键数字用中文呈现。
- 当查询结果适合用图表展示（如排名、趋势、对比）时，在回答末尾附加一个 ```chart-json 代码块，内容为 ECharts 的 option JSON（需包含 title、xAxis、yAxis、series 中适用的字段）。例如：
```chart-json
{"title":{"text":"各班组实际工时"},"tooltip":{},"xAxis":{"type":"category","data":["甲班","乙班"]},"yAxis":{"type":"value"},"series":[{"type":"bar","data":[120,98]}]}
```
- 若无需图表则不输出该代码块。
"""


def build_graph(llm, tools):
    tool_node = ToolNode(tools)
    llm_with_tools = llm.bind_tools(tools)

    def agent(state: MessagesState):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    def should_continue(state: MessagesState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", tool_node)
    graph.add_edge("tools", "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.set_entry_point("agent")
    return graph.compile()


def initial_messages(question: str) -> list:
    return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]
