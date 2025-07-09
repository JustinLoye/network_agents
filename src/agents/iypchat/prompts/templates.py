from collections import defaultdict
import re
from langchain_core.example_selectors.base import BaseExampleSelector
import random
import pandas as pd

from langchain_core.prompts.few_shot import FewShotPromptTemplate
from langchain_core.prompts.prompt import PromptTemplate

from src.agents.iypchat.schema.schema import ENTITIES_EXPLANATIONS, Neo4jSchema, filtered_explanations
from src.agents.iypchat.prompts.examples import entity_examples, presenter_examples


def get_cypher_labels(cypher: str) -> list[str]:
    paren_contents = re.findall(r"\(([^)]+)\)", cypher)

    labels = []
    for content in paren_contents:
        match = re.search(r":\s*([A-Za-z_][A-Za-z0-9_]*)", content)
        if match:
            labels.append(match.group(1))

    return labels


def create_entity_prompt(examples: dict):
    example_prompt = PromptTemplate.from_template("user: {user}\n assistant: {assistant}")
    
    prefix = f"""You are a helpful assistant that extract or guess Internet entities from user messages.

Return ONLY a python list with a list of entities related to the Internet. Each entity has to be one of the following list:
{ENTITIES_EXPLANATIONS}


DO NOT invent new entities, pick only from the words listed above.
Include entity even if you are not sure. 


Here are some example of entities extraction:"""

    suffix = """\nRemember to pick entities only from this list:
AS Country Prefix IP URL DomainName Hostname IXP Facility AuthoritativeNameServer Ranking BGPCollector Organization Tag PeeringdbOrgID PeeringdbFacID PeeringdbIXID PeeringdbNetID CaidaIXID AtlasProbe AtlasMeasurement Estimate Name"""

    prompt = FewShotPromptTemplate(
        examples=examples,
        example_prompt=example_prompt,
        prefix=prefix,
        suffix=suffix,
    ).format()
    
    return prompt




presenter_sysprompt_template = """You are a helpful assistant that present the results of a Cypher query to the user.
The user will provide his query in natural language and the result, and your role is to present it in a clear and professional way.
Cypher queries are made to a neo4j knowledge graph called Internet Yellow Pages (IYP). 
IYP is a knowledge database that gathers information about Internet resources (for example ASNs, IP prefixes, and domain names).


You will use the context provided here to help presenting the result. Here is what you need to know about IYP:

Node labels explanation:
{entities_explanation}


Here are some examples of user message and expected assistant answer:
{examples}"""


example_prompt = PromptTemplate.from_template("Input: {input} -> Output: {output}")

cyphereval = pd.read_csv("src/agents/iypchat/cyphereval/CypherEval/variation-A.csv")
ordered_levels = [
    "Easy technical prompt",
    "Easy general prompt",
    "Medium technical prompt",
    "Medium general prompt",
    "Hard technical prompt",
    "Hard general prompt",
]
cyphereval["Difficulty Level"] = pd.Categorical(
    cyphereval["Difficulty Level"], categories=ordered_levels, ordered=True
)


class CypherEvalExampleSelector(BaseExampleSelector):
    def __init__(self, cyphereval: pd.DataFrame):
        self.cyphereval = cyphereval.copy(deep=True)

    @staticmethod
    def _get_score(cypher: str, entities: list[str]) -> int:
        return len(set(entities) & set(get_cypher_labels(cypher)))

    def add_example(self, example: dict) -> None:
        # If you need to collect examples dynamically, do it here.
        # Otherwise, just a no-op to satisfy the abstract base class:
        pass

    def select_examples(self, input_variables: dict):
        # Extracted entities
        entities: list[str] = input_variables["entities"]
        # Number of examples
        topK = input_variables["topK"]

        # Score the best match based on shared entities with cypher
        self.cyphereval["Score"] = self.cyphereval["Canonical Solution"].apply(
            self._get_score, args=(entities,)
        )
        # Break ties by Diffculty Level
        self.cyphereval.sort_values(
            by=["Score", "Difficulty Level"], ascending=[False, True], inplace=True
        )

        top_idxs = self.cyphereval.loc[self.cyphereval["Score"] > 0].head(topK).index
        examples = self.cyphereval.loc[top_idxs, "Canonical Solution"].values.tolist()
        prompts = self.cyphereval.loc[top_idxs, "Prompt"].values.tolist()

        # If there are too few examples, pick random ones
        n_missing_examples = topK - len(top_idxs)
        other_examples = self.cyphereval.loc[~self.cyphereval.index.isin(top_idxs)]
        idxs = random.sample(range(len(other_examples)), n_missing_examples)
        examples += other_examples.loc[idxs, "Canonical Solution"].values.tolist()
        prompts += other_examples.loc[idxs, "Prompt"].values.tolist()

        return [
            {"question": prompt, "query": example.replace("{", "{{").replace("}", "}}")}
            for prompt, example in zip(prompts, examples)
        ]


example_selector = CypherEvalExampleSelector(cyphereval)
example_selector.select_examples(input_variables={"entities": ["AS", "IXP"], "topK": 5})


# Configure a formatter
example_prompt = PromptTemplate(
    input_variables=["question", "query"],
    template="Question: {question}\nCypher query: {query}",
)


def create_cypher_template(schema: Neo4jSchema, entities: list[str]):
    """Few shot with dymanically loaded examples"""

    prefix = f"""Task:Generate Cypher statement to query a graph database about the Internet.
Instructions:
You will use only the context provided here to formulate the query. Here is what you need to know:

Node labels explanation:
{filtered_explanations(labels=entities)}

Neo4j schema:
{schema.filter_labels(entities, common_rel_mode="and").to_llm()}    

Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.

Examples: Here are a few examples of generated Cypher statements for some question examples:
    """

    prompt_template = FewShotPromptTemplate(
        example_selector=example_selector,
        example_prompt=example_prompt,
        prefix=prefix,
        suffix="",
        input_variables=["schema", "entities", "topK"],
    )
    return prompt_template


def create_presenter_prompt(examples: dict, entities: list[str]):
    example_prompt = PromptTemplate.from_template(
        "user: {user}\n assistant: {assistant}"
    )
    
    prefix = f"""You are a helpful assistant that present the results of a Cypher query to the user.
The user will provide his query in natural language and the result, and your role is to present it in a clear and professional way.
Cypher queries are made to a neo4j knowledge graph called Internet Yellow Pages (IYP). 
IYP is a knowledge database that gathers information about Internet resources (for example ASNs, IP prefixes, and domain names).


You will use the context provided here to help presenting the result. Here is what you need to know about IYP:

Node labels explanation:
{filtered_explanations(entities)}


Here are some examples of user message and expected assistant answer:"""

    suffix = ""

    prompt = FewShotPromptTemplate(
        examples=examples,
        example_prompt=example_prompt,
        prefix=prefix,
        suffix=suffix,
    )

    return prompt.format()


if __name__ == "__main__":
    schema = Neo4jSchema.from_json("src/agents/iypchat/schema/neo4j-schema.json")
    entities = ["AS", "Prefix"]
    
    # Entity resolution prompt
    entity_prompt = create_entity_prompt(entity_examples)
    print(entity_prompt)

    # Few shot prompt template dynamically loaded from CypherEval
    cypher_template = create_cypher_template(schema, entities)
    cypher_prompt = cypher_template.format(
        schema=schema,
        entities=entities,
        topK=5,
    )
    print(cypher_prompt)
    
    # Presenter prompt 
    entity_prompt = create_presenter_prompt(presenter_examples, entities)
    print(entity_prompt)
    