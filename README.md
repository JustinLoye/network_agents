# Networking Agents Chatbot

An Ollama/LangGraph/Chainlit app showcasing networking-focused agents.

## Agents

Each agent uses a custom LangGraph implementation to support lightweight "thinking" models.

### data_retriever

A ReAct agent with two tools:

- `whois`: Queries bgp.tools for IP/ASN ownership info.
- `iypchat`: Natural language interface to the Internet Yellow Pages knowledge graph (powered by an LLM workflow).

**Features:**

- Dynamic context selection to explain Internet concepts:
  - Filtered explanations of Internet entities
  - Filtered knowledge graph schema
- Dynamic few-shot prompting using the CypherEval dataset

![data_retriever](src/agents/data_retriever/data_retriever.png)
![iypchat](src/agents/iypchat/iypchat.png)

### network_operator

A ReAct agent with built-in networking tools:

- `ping`
- `traceroute`
- `get_routing_table`

![network_operator](src/agents/network_operator/network_operator.png)

### supervisor

A ReAct agent that delegates tasks to `data_retriever` and `network_operator`.

**Features:**

- Custom handoff messages between agents
- State injection to hide message history from other agents

![supervisor](src/agents/supervisor/supervisor.png)

## UI

**Features:**

- Streaming responses
- Chat memory
- Live execution tree integrated with LangGraph
- Agent state display alongside the conversation

![UI homepage](src/ui/networking_agent_homepage.png)

**Demo:**

Coming soon!
