import chainlit as cl
import json
import asyncio
import re
from langchain.schema.runnable.config import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import (
    HumanMessage,
)
from chainlit.input_widget import Select, Slider

from src.agents.utils.states import serialize_state
from src.agents.supervisor.supervisor import get_supervisor_graph
from src.agents.utils.models import ModelParams

# python -m chainlit run src/ui/app.py -w


def extract_tool(content: str):
    extracted = re.findall(r"<tool>(.*?)</tool>", content, flags=re.DOTALL)
    return extracted  # returns a list of all matches


def remove_tool(content: str):
    cleaned = re.sub(r"<tool>.*?</tool>\s*", "", content, flags=re.DOTALL)
    return cleaned


AS_dependency_start = """**Determine my ISP’s AS dependencies by following these steps:**
1. Run a traceroute to identify my ISP’s IP address.
2. Look up the AS number assigned to that IP.
3. Retrieve that AS’s dependencies.
4. Return a list of the resulting AS numbers, each annotated with its organization name and country.
"""


@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Ping Google",
            message="Ping google.com",
            icon="/public/network-settings.svg",
        ),
        cl.Starter(
            label="Ping my gateway",
            message="Get my gateway ip and ping it",
            icon="/public/network-settings.svg",
        ),
        # cl.Starter(
        #     label="IIJ IODA",
        #     message="Give me the prefix visibility of AS 2497 (Internet Initiative Japan) for the last 6 hours",
        #     # icon="/public/idea.svg",
        # ),
        cl.Starter(
            label="AS2497 IXP membership",
            message="Get me the list of IXPs where AS2497 is present",
            icon="/public/knowledge-graph-data.svg",
        ),
        cl.Starter(
            label="AS dependencies of my ISP (easy)",
            message=AS_dependency_start,
            icon="/public/collaboration.svg",
        ),
        cl.Starter(
            label="AS dependencies of my ISP (hard)",
            message="Determine my ISP's AS dependencies",
            icon="/public/collaboration.svg",
        ),
    ]


@cl.on_chat_start
async def start_chat():
    cl.user_session.set("message_history", [])
    checkpointer = InMemorySaver()
    cl.user_session.set("agent", get_supervisor_graph(checkpointer=checkpointer))

    settings = await cl.ChatSettings(
        [
            Select(
                id="model",
                label="Model",
                values=["qwen3:4b", "qwen2.5-coder:3b", "llama3.2"],
                initial_index=0,
            ),
            Slider(
                id="temperature",
                label="Temperature",
                initial=0,
                min=0,
                max=2,
                step=0.1,
            ),
        ]
    ).send()


@cl.on_settings_update
async def setup_agent(settings):
    checkpointer = InMemorySaver()
    model_params = ModelParams(**settings)
    cl.user_session.set(
        "agent",
        get_supervisor_graph(checkpointer=checkpointer, model_params=model_params),
    )


@cl.action_callback("show_tool")
async def on_tool(action):
    tool_res = action.payload["tool_res"]
    if isinstance(tool_res, list):
        tool_res = " ".join(tool_res)
    await cl.Message(tool_res).send()


@cl.on_message
async def on_message(msg: cl.Message):
    config = {"configurable": {"thread_id": cl.context.session.id}}
    message_history = cl.user_session.get("message_history")
    message_history.append(HumanMessage(content=msg.content))

    # Config setup
    cb = cl.LangchainCallbackHandler()
    cb._schema_format = "original+chat"
    config = RunnableConfig(callbacks=[cb], **config)

    final_answer = cl.Message(content="")

    graph = cl.user_session.get("agent")

    for msg, metadata in graph.stream(
        {"messages": message_history},
        stream_mode="messages",
        config=config,
    ):
        if (
            msg.content
            and not isinstance(msg, HumanMessage)
            and not metadata["langgraph_node"] == "supervisor_agent"
        ):
            await final_answer.stream_token(msg.content)

    actions = []

    tool_results = extract_tool(final_answer.content)
    if tool_results:
        for i, tool_result in enumerate(tool_results):
            actions.append(
                cl.Action(
                    name="show_tool",
                    payload={"tool_res": tool_result},
                    label=f"🛠️#{i + 1}💬",
                )
            )

    # final_answer.content = remove_thoughts(final_answer.content)
    # final_answer.content = remove_tool(final_answer.content)

    final_answer.actions = actions

    # Get final_state to update the message history...
    final_state = graph.get_state(config=config).values
    message_history.append(final_state["messages"][-1])
    final_answer.content = final_state["messages"][-1].content

    # ... and display it on the side for monitoring
    json_element = cl.CustomElement(
        name="CollapsibleJSON",
        props={
            "data": serialize_state(final_state),
            "title": "Agent state",
            "defaultExpanded": True,
        },
    )
    elements = [json_element]
    await cl.ElementSidebar.set_elements(elements=elements)
    await cl.ElementSidebar.set_title("Agent state")

    await asyncio.sleep(3)

    await final_answer.send()


@cl.on_chat_end
def on_chat_end():
    if len(cl.chat_context.to_openai()) == 0:
        return

    with open("last_chat.json", "w") as f:
        json.dump(cl.chat_context.to_openai(), f)
    print(cl.chat_context.to_openai())
    print("The user disconnected!")
