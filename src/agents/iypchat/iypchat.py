import ast
import json
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph

from src.agents.iypchat.schema.schema import Neo4jSchema
from src.agents.iypchat.query_iyp import run_iyp_query
from src.agents.iypchat.prompts.templates import (
    create_entity_prompt,
    create_cypher_template,
    create_presenter_prompt,
)
from src.agents.iypchat.prompts.examples import entity_examples, presenter_examples
from src.agents.utils.states import SplitThinkingAgentState, remove_thoughts, serialize_state
from src.agents.utils.models import ModelParams



class GraphState(SplitThinkingAgentState):
    entities: list[str]
    user_query: str
    cypher_query: str
    cypher_result: str
    cypher_thoughts: str
    
    
def get_iyp_graph(debug=False, model_params=ModelParams()) -> CompiledStateGraph:
    """Return IYP graph agent"""
    llm = ChatOpenAI(**model_params.model_dump())

    schema = Neo4jSchema.from_json("src/agents/iypchat/schema/neo4j-schema.json")

    def entity_extractor(state: GraphState) -> list:
        sysprompt = create_entity_prompt(entity_examples)
        user_query = state["messages"][-1]
        response = llm.invoke([SystemMessage(sysprompt), state["messages"][-1]])
        entities = ast.literal_eval(remove_thoughts(response.content))
        
        return {
            "entities": entities,
            "thoughts": [response],
            "user_query": user_query.content,
        }


    def iyp_assistant(state: GraphState) -> list:
        cypher_template = create_cypher_template(schema, state["entities"])
        sysprompt = cypher_template.format(
            schema=schema,
            entities=state["entities"],
            topK=5,
        )

        response = llm.invoke(
            [SystemMessage(sysprompt), HumanMessage(state["user_query"])]
        )
        cypher_query = remove_thoughts(response.content)
        try:
            cypher_result = run_iyp_query(cypher_query)
        except Exception as e:
            print(f"{e}")
            print(cypher_query)

        return {
            "cypher_query": cypher_query,
            "cypher_result": cypher_result,
            "thoughts": [response],
        }


    def iyp_presenter(state: GraphState) -> list:
        sysprompt = create_presenter_prompt(presenter_examples, state["entities"])
        response = llm.invoke(
            [
                SystemMessage(sysprompt),
                HumanMessage("\n".join([state["user_query"],
                                        str(state["cypher_query"]),
                                        str(state["cypher_result"])]))
            ]
        )
        return {"messages": [response], "thoughts": [response]}


    builder = StateGraph(GraphState)

    builder.add_node("entity_extractor", entity_extractor)
    builder.add_node("iyp_assistant", iyp_assistant)
    builder.add_node("iyp_presenter", iyp_presenter)


    builder.add_edge(START, "entity_extractor")
    builder.add_edge("entity_extractor", "iyp_assistant")
    builder.add_edge("iyp_assistant", "iyp_presenter")
    builder.add_edge("iyp_assistant", END)
    iyp_graph = builder.compile(debug=True, name="iypchat")
    
    return iyp_graph

if __name__ == "__main__":
    
    iyp_graph = get_iyp_graph(debug=True)
    
    png_bytes = iyp_graph.get_graph(xray=True).draw_mermaid_png()
    with open("src/agents/iypchat/iypchat.png", "wb") as f:
        f.write(png_bytes)


    # user_msg = "Return everything that is related with 8.8.8.0/24"
    user_msg = "Find the Japanese IXPs' names where the AS with asn 2497 is present"
    # user_msg = "Find the QUERIED_FROM's value for the DomainName with name 'google.com' and the Country with country_code 'US'"
    # user_msg = "Return the names and asn of the AS peering with rrc25"
    # user_msg = "Find the AS nodes associated with the country code 'JP' through the COUNTRY relationship. Match these AS nodes to Ranking nodes with a rank below 10 according to the 'ihr.country_dependency' reference_name and for the Ranking in Japan."
    # user_msg = "What is the RPKI status of 138.121.42.0/24. Include as much details as possible."
    
    response = iyp_graph.invoke({"messages": [HumanMessage(user_msg)]})
    
    print(json.dumps(serialize_state(response), indent=4))
