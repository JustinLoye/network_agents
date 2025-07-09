import subprocess
import json
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.state import CompiledStateGraph

from src.agents.utils.states import SplitThinkingAgentState, serialize_state
from src.agents.iypchat.iypchat import get_iyp_graph


@tool(parse_docstring=True)
def whois(resource: str) -> str:
    """
    Query WHOIS information from bgp.tools for an ASN, IP address, or MAC address.

    Args:
        resource (str): The identifier to look up. Can be an ASN (e.g., "AS2497", "2497"), an IPv4/IPv6 address (e.g., "1.1.1.1" or "2a00::"), or a MAC address (e.g., "90:e2:ba:61:c3:88").

    Returns:
        str: A tool-formatted string containing a dictionary of lookup results with the following keys:
            - 'AS': str, the Autonomous System number
            - 'IP': str, the queried IP address
            - 'BGP Prefix': str, the BGP prefix
            - 'CC': str, the country code
            - 'Registry': str, the registry that allocated the resource
            - 'Allocated': str, the allocation date in YYYY-MM-DD format
            - 'AS Name': str, the name of the AS
    """

    # fix when LLM call with ASN only (no AS prefix)
    try:
        asn = int(resource)
        resource = f"AS{asn}"
    except ValueError:
        pass

    result = subprocess.run(
        ["whois", "-h", "bgp.tools", "-v", resource],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    res = result.stdout if result.returncode == 0 else result.stderr

    i = 0
    for line in res.splitlines():
        splitted = line.split("|")
        if not len(splitted) == 7:
            continue
        if i == 0:
            keys = [col_name.strip() for col_name in line.split("|")]
        elif i == 1:
            vals = [col_name.strip() for col_name in line.split("|")]
        else:
            break
        i += 1

    res = dict(zip(keys, vals))
    return f"<tool>{res}</tool>"


def get_data_retriever_graph(debug=False) -> CompiledStateGraph:
    "Return data_retriever react agent"

    iyp_graph = get_iyp_graph()

    @tool(parse_docstring=True)
    def call_iyp(prompt: str) -> str:
        """Queries the Internet Yellow Pages (IYP) knowledge graph using a natural language prompt.

        This function forwards a user-provided natural language prompt to an agent that interfaces
        with the Internet Yellow Pages knowledge graph and returns the agent's response.
        Useful to learn about: AS dependencies, ranks, IXPs, and many other things.

        Args:
            prompt (str): A natural language query describing the information to retrieve from the IYP database.

        Returns:
            str: The response message returned by the IYP query agent.
        """
        response = iyp_graph.invoke({"messages": [HumanMessage(prompt)]})
        return {"messages": [response], "thoughts": [response]}
        # return response["messages"][-1]    

    data_tools = [call_iyp, whois]
    data_llm = ChatOpenAI(
        base_url="http://localhost:11434/v1", api_key="ollama", model_name="qwen3:4b"
    ).bind_tools(data_tools)


    def assistant(state: SplitThinkingAgentState):
        """Note: could be improved by trying out langgraph forward feature"""
        sys_msg = SystemMessage(
            content="""You are an expert in retrieving Internet data.
You have two tools to answer user message: `whois` and `call_iyp`.
Carefully evaluate how `whois` tool is able to answer the user request.
If not, always assume `call_iyp` has the answer.
Forward the user message to `call_iyp` without alteration"""
        )
        response = data_llm.invoke([sys_msg] + state["messages"])
        return {"messages": [response], "thoughts": [response]}

    builder = StateGraph(SplitThinkingAgentState)
    
    # Define nodes: these do the work
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(data_tools))

    # Define edges: these determine how the control flow moves
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
    )
    builder.add_edge("tools", "assistant")
    react_graph = builder.compile(debug=True, name="data_retriever")
    
    return react_graph

if __name__ == "__main__":
    data_retriever_graph = get_data_retriever_graph(debug=True)

    png_bytes = data_retriever_graph.get_graph(xray=True).draw_mermaid_png()
    with open("src/agents/data_retriever/data_retriever.png", "wb") as f:
        f.write(png_bytes)

    user_msg = "Get the name of AS2497 and find the IXP it is present at"
    response = data_retriever_graph.invoke({"messages": [HumanMessage(user_msg)]})

    print(json.dumps(serialize_state(response), indent=4))