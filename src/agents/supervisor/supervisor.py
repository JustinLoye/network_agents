import json
from typing_extensions import Annotated
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.prebuilt import InjectedState
from langgraph.types import Command, Send
from langgraph_supervisor.handoff import create_handoff_back_messages

from src.agents.data_retriever.data_retriever import get_data_retriever_graph
from src.agents.network_operator.network_operator import get_network_operator_graph
from src.agents.utils.states import (
    SplitThinkingAgentState,
    serialize_state,
)
from src.agents.utils.models import ModelParams

METADATA_KEY_HANDOFF_DESTINATION = "__handoff_destination"
METADATA_KEY_IS_HANDOFF_BACK = "__is_handoff_back"

supervisor_prompt = """You are a supervisor managing two agents in order to reply to the last user message:
- 'network_operator' agent, a network operator agent. Assign concrete actions like ping, traceroute, ip route show to this agent.
- 'data_retriever', an Internet data retriever agent. Assign information-retrieval tasks to this agent.


Assign work to one agent at a time, do not call agents in parallel.
Carefully plan the steps to resolve the user message and clearly separate each step so each agent is focused on a simple task.
Do not do any work yourself except basic common sense tasks.
After workflow execution always reply to the user original question (the user don't see the agents response so you need to forward it).
Assume the user has a background on Internet data and knows what he wants.


Example workflow (for reference only):

Example user message: “Get my ISP via traceroute to google.com, then find its AS number and check if the AS is present in a Japanese IXP.”

Example supervisor workflow (this is a text description, you are meant to execute these steps):
1. transfer_to_network_operator(task_description="Run traceroute to google.com")
2. [extract the first‑hop IP]
3. transfer_to_data_retriever(task_description="Lookup ASN for IP 12.34.56.78")
4. [extract the ASN]
5. transfer_to_data_retriever(task_description="Check whether ASN 2497 is present in any Japanese IXP")
6. [aggregate results and return summary to user]"""


def create_task_description_handoff_tool(
    *, agent_name: str, description: str | None = None
):
    """
    Custom handoff constructor that
    - update the state to signal agent handoffs
    - send only a `task_description` instead of the whole state to the agent
    """
    name = f"transfer_to_{agent_name}"
    description = description or f"Ask {agent_name} for help."

    @tool(name, description=description)
    def handoff_tool(
        # this is populated by the supervisor LLM
        task_description: Annotated[
            str,
            "Description of what the next agent should do, including all of the relevant context.",
        ],
        # these parameters are ignored by the LLM
        state: Annotated[SplitThinkingAgentState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_message = ToolMessage(
            content=f"Successfully transferred to {agent_name} with payload [{task_description}]",
            name=name,
            tool_call_id=tool_call_id,
            response_metadata={METADATA_KEY_HANDOFF_DESTINATION: agent_name},
        )
        task_description_message = HumanMessage(content=task_description)
        agent_input = {**state, "messages": [task_description_message]}
        return Command(
            # highlight-next-line
            goto=Send(agent_name, agent_input),
            graph=Command.PARENT,
            update={"messages": [tool_message]}
        )

    return handoff_tool


def get_supervisor_graph(debug=False, checkpointer=None, model_params=ModelParams()) -> CompiledStateGraph:
    """Return supervisor agent"""
    
    assign_to_data_retriever = create_task_description_handoff_tool(
        agent_name="data_retriever",
        description="Assign task to a data_retriever agent. Useful to get data about the Internet entities like AS, IXP, prefix, ip.")

    assign_to_network_operator = create_task_description_handoff_tool(
        agent_name="network_operator",
        description="Assign task to a network_operator agent. Useful to do: ping, traceroute, ip tables, get the current time.")

    supervisor_tools = [assign_to_data_retriever, assign_to_network_operator]
    
    llm = ChatOpenAI(
        **model_params.model_dump()).bind_tools(supervisor_tools, parallel_tool_calls=False)

    def assistant(state: SplitThinkingAgentState):
        sysprompt = SystemMessage(supervisor_prompt)
        response = llm.invoke([sysprompt] + state["messages"])

        return {"messages": [response], "thoughts": [response]}
    
    # Define react supervisor
    builder = StateGraph(SplitThinkingAgentState)
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(supervisor_tools))
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        # If the latest message requires a tool, route to tools
        # Otherwise, provide a direct response
        tools_condition,
    )
    builder.add_edge("tools", "assistant")
    supervisor_agent = builder.compile(debug=debug, name="supervisor_agent")
    
    data_retriever = get_data_retriever_graph(model_params=model_params)
    network_operator = get_network_operator_graph(model_params=model_params)
    
    def call_data_retriever(state: SplitThinkingAgentState):
        """wrapper for custom return values"""
        response = data_retriever.invoke(state)
        reply = [response["messages"][-1]]
        handoff = create_handoff_back_messages("data_retriever", "supervisor_agent")
        reply.extend(handoff)
        return {"messages": reply, "thoughts": response["thoughts"]}

    def call_network_operator(state: SplitThinkingAgentState):
        """wrapper for custom return values"""
        response = network_operator.invoke(state)
        reply = [response["messages"][-1]]
        handoff = create_handoff_back_messages("network_operator", "supervisor_agent")
        reply.extend(handoff)
        return {"messages": reply, "thoughts": response["thoughts"]}

    # Define the multi-agent supervisor graph
    supervisor = (
        StateGraph(SplitThinkingAgentState)
        # NOTE: `destinations` is only needed for visualization and doesn't affect runtime behavior
        .add_node(
            supervisor_agent, destinations=("data_retriever", "network_operator", END)
        )
        .add_node("data_retriever", call_data_retriever)
        .add_node("network_operator", call_network_operator)
        .add_edge(START, "supervisor_agent")
        # always return back to the supervisor
        .add_edge("data_retriever", "supervisor_agent")
        .add_edge("network_operator", "supervisor_agent")
        .compile(debug=debug, checkpointer=checkpointer)
    )
    
    return supervisor


if __name__ == "__main__":
    supervisor_graph = get_supervisor_graph(debug=True)

    png_bytes = supervisor_graph.get_graph(xray=True).draw_mermaid_png()
    with open("src/agents/supervisor/supervisor.png", "wb") as f:
        f.write(png_bytes)
    
    # user_msg = "Get my Internet Service Provider ip on a traceroute to google.com and search the associated AS name"
    # user_msg = "For all IPs address on a traceroute to google, retrieve their AS number and their countries. Then for each of these AS in Japan, research data involving the depency to other ASes."
    # user_msg = "Get my Internet Service Provider with a traceroute to google.com, then search the associated AS number and check if the AS is in a Japanese IXP"
    # user_msg = "Search the IXP where AS2497 is present"
    user_msg = "Run a ping to google.com"


    response = supervisor_graph.invoke({"messages": [HumanMessage(user_msg)]})

    serialized = serialize_state(response)
    print(json.dumps(serialized, indent=4))
    with open("src/agents/supervisor/supervisor_response.json", "w") as f:
        json.dump(serialized, f)