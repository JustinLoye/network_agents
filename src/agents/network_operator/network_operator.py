
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.state import CompiledStateGraph

from src.agents.utils.states import SplitThinkingAgentState, serialize_state
from src.agents.network_operator.tools import NETWORKING_TOOLS
from src.agents.utils.models import ModelParams

def get_network_operator_graph(debug=False, checkpointer=None, model_params=ModelParams()) -> CompiledStateGraph:
    """Return network_operator react agent"""

    llm = ChatOpenAI(**model_params.model_dump()).bind_tools(
        NETWORKING_TOOLS, parallel_tool_calls=False
    )


    def assistant(state: SplitThinkingAgentState):
        print("state in network agent", state)
        sys_msg = SystemMessage(
            content="""You are an Internet expert with many tool to get real-time information about the Internet. 
Use tools if related to the user question.
Use tools one at a time, and process the output of the previous tool before running a new one.
If you dont need any more tool call, reply to the user in a professional tone.
Reply to the user question only, no apologies and no follow-up questions"""
        )
        response = llm.invoke([sys_msg] + state["messages"])

        return {"messages": [response], "thoughts": [response]}
    
    builder = StateGraph(SplitThinkingAgentState)
    
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(NETWORKING_TOOLS))

    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
    )
    builder.add_edge("tools", "assistant")
    react_graph = builder.compile(debug=debug, checkpointer=checkpointer, name="network_operator")
    
    return react_graph


if __name__ == "__main__":
    
    network_operator_graph = get_network_operator_graph(debug=True)
    
    png_bytes = network_operator_graph.get_graph(xray=True).draw_mermaid_png()
    with open("src/agents/network_operator/network_operator.png", "wb") as f:
        f.write(png_bytes)


    # user_msg = "Ping all the IPs you see on a traceroute to google.com"
    # user_msg = "Get my gateway IP and ping it"
    user_msg = "Ping google.com"
    response = network_operator_graph.invoke({"messages": [HumanMessage(user_msg)]})
        
    serialized = serialize_state(response)
    print(json.dumps(serialized, indent=4))
    with open("src/agents/network_operator/network_operator_response.json", "w") as f:
        json.dump(serialized, f)