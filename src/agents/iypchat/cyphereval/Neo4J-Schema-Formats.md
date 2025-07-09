# Neo4J Schema Formats

## JSON schema format: This is a JSON type schema format for representing the Neo4J database structure
```
Node properties are the following:
{'labels': 'Label1', 'properties': ['property1A']}
{'labels': 'Label2', 'properties': ['property2A', 'property2B']}
{'labels': 'Label3', 'properties': ['property3A', 'property3B']}
...

Relationship properties are the following:
{'properties': ['property1A'], 'type': 'RELATIONSHIP_TYPE1'}
{'properties': ['property2A', 'property2B'], 'type': 'RELATIONSHIP_TYPE2'}
...

Relationship point from source to target nodes:
{'source': 'Label1', 'relationship': 'RELATIONSHIP_TYPE1', 'target': ['Label2']}
{'source': 'Label1', 'relationship': 'RELATIONSHIP_TYPE2', 'target': ['Label2', 'Label3']}
...
```

## CSV schema format: This is a CSV type schema format for representing the Neo4J database structure
```
Node properties are the following:
"labels","properties"
"Label1","property1A"
"Label2","property2A,property2B"
"Label3","property3A,property3B"
...

Relationship properties are the following:
"type","properties"
"RELATIONSHIP_TYPE1","property1A"
"RELATIONSHIP_TYPE2","property2A,property2B"
...

Relationship point from source to target nodes:
"source","relationship","target"
"Label1","RELATIONSHIP_TYPE1","Label2"
"Label1","RELATIONSHIP_TYPE2","Label2,Label3"
...
```

## LLMGen1 schema format: This is an LLM custom-generated type schema format for representing the Neo4J database structure after refining the responses of GPT, Llama, DeepSeek, Qwen
```
**Nodes**
* `Label1`: `property1A`
* `Label2`: `property2A`, `property2B`
* `Label3`: `property3A`, `property3B`

**Relationships**
* `RELATIONSHIP_TYPE1`: `Label1` -> `Label2` (`property1A`)
* `RELATIONSHIP_TYPE2`: `Label1` -> `Label2`, `Label3` (`property2A`, `property2B`)
```

## LLMGen2 schema format: This is an LLM custom-generated type schema format for representing the Neo4J database structure after refining the responses of GPT, Llama, DeepSeek, Qwen
```
**Nodes**
* A `Label1` has a `property1A`.
* A `Label2` has a `property2A` and a `property2B`.
* A `Label3` has a `property3A` and a `property3B`.
...

**Relationships**
* A `Label1` can be `RELATIONSHIP_TYPE1` with a `Label2`.
* A `Label1` can be `RELATIONSHIP_TYPE2` with a `Label2` and a `Label3`.
...

**Additional details about the relationships**
* The `RELATIONSHIP_TYPE1` relationship has a `property1A` property.
* The `RELATIONSHIP_TYPE2` relationship has a `property2A` and a `property2B` properties.
...
```

## LLMGen3 schema format: This is an LLM custom-generated type schema format for representing the Neo4J database structure after refining the responses of GPT, Llama, DeepSeek, Qwen
```
1. Node Types:
    - Label1:
    - property1A
    - Label2:
    - property2A
    - property2B
    - Label3:
    - property3A
    - property3B
2. Relationship Types:
    - RELATIONSHIP_TYPE1:
    - property1A
    - RELATIONSHIP_TYPE2:
    - property2A
    - property2B
3. Schema:
    - (Label1)-[:RELATIONSHIP_TYPE1]-(Label2)
    - (Label1)-[:RELATIONSHIP_TYPE2]-(Label2)
    - (Label1)-[:RELATIONSHIP_TYPE2]-(Label3)
```