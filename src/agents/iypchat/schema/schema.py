import json
import pandas as pd
from dataclasses import dataclass
from typing import Literal

ENTITIES_EXPLANATIONS = """- AS: Autonomous System involved in BGP traffic (e.g., 2497, AS2497, IIJ (ASN2497))
- Country: Country name or code (e.g., France, Japan, JP, jp).
- Prefix: Internet ipv4 or ipv6 prefix (e.g., 192.168.1.0/24, 2001:db8::/32)
- IP: Internet ipv4 or ipv6 address (e.g., 192.168.1.12, 2001:db8::)
- URL: URL (e.g., https://www.iij.ad.jp/)
- DomainName: Domain name (e.g., iij.ad.jp)
- Hostname: Host name (e.g., www.iij.ad.jp)
- IXP: Internet Exchange Point (e.g., PITER-IX Tallinn, DE-CIX Barcelona, Equinix Dublin)
- Facility: Data center (e.g., ACT Gillette, Equinix DE1 - Denver)
- AuthoritativeNameServer: URL to name servers that provied answer to DNS queries (e.g., "www.astro.com", "ns.in.ua", "ns3.dk")
- Ranking: Ranking dataset (e.g., APNIC eyeball estimates, CAIDA ASRank, IHR country ranking: Total AS)
- BGPCollector: BGP routes collector from the RouteViews and RIPE RIS data collection project (e.g., route-views2, route-views.amsix, rrc00, rrc12)
- Organization: Name of Internet organization (e.g., Juniper Networks, Internet Initiative Japan Inc.)
- Tag: A way to classify nodes. For AS nodes, tag is the business type like (e.g., ISP, CDN, University, E-commerce), For Prefix nodes, tag is "RPKI Valid", "IRR Valid", "Anycast". In general, if the message mention RPKI, IRR or Anycast extract the Tag entity.
- PeeringdbOrgID: Organization index in PeeringDB dataset (e.g., 42)
- PeeringdbFacID: Facility/Data center index in PeeringDB dataset (e.g., 42)
- PeeringdbIXID: IXP index in PeeringDB dataset (e.g., 42) 
- PeeringdbNetID: AS index in PeeringDB dataset (e.g., 42)
- CaidaIXID: IXP index in Caida dataset (e.g., 42)
- AtlasProbe: Probe from the ATLAS Internet data collection project
- AtlasMeasurement: Result of an ATLAS probe 
- Estimate: Population Estimate from Worldbank population dataset
- Name: A label only used to store AS names (e.g., Internet Initiative Japan Inc.)"""


def filtered_explanations(labels: list[str]):
    filtered = []
    for line in ENTITIES_EXPLANATIONS.splitlines():
        for label in labels:
            if label in line:
                filtered.append(line)

    return "\n".join(filtered)


@dataclass
class Neo4jSchema:
    """Class to store large Neo4J schema and filter it to no pollute LLM contexts"""

    node_props: pd.DataFrame
    rel_props: pd.DataFrame
    relationships: pd.DataFrame

    REQUIRED_NODE_PROPS_COLS = {"labels", "properties"}
    REQUIRED_REL_PROPS_COLS = {"type", "properties"}
    REQUIRED_RELATIONSHIPS_COLS = {"source", "relationship", "target"}

    REL_METADATA = [
        "reference_name",
        "reference_org",
        "reference_time_fetch",
        "reference_url_data",
        "reference_time_modification",
        "reference_url_info",
    ]

    def __post_init__(self):
        for df, cols in zip(
            [self.node_props, self.rel_props, self.relationships],
            [
                self.REQUIRED_NODE_PROPS_COLS,
                self.REQUIRED_REL_PROPS_COLS,
                self.REQUIRED_RELATIONSHIPS_COLS,
            ],
        ):
            if len(cols.difference(set(df.columns))) > 0:
                raise ValueError(f"df cols {df.columns} misses required columns {cols}")

        self.updated_node_props = self.node_props.copy()
        self.updated_rel_props = self.rel_props.copy()
        self.updated_relationships = self.relationships.copy()

    @classmethod
    def from_json(cls, json_path: str):
        with open(json_path, "r") as f:
            data = json.load(f)

        node_rows = [
            {"labels": label, "properties": prop}
            for label, props in data["node_properties"].items()
            for prop in props
        ]
        relprop_rows = [
            {"type": rel_type, "properties": prop}
            for rel_type, props in data["relationship_properties"].items()
            for prop in props
        ]
        rel_rows = [
            {"source": source, "relationship": rel_type, "target": target}
            for source, targets in data["schema"].items()
            for rel_type, target_list in targets.items()
            for target in target_list
        ]

        return cls(
            pd.DataFrame(node_rows),
            pd.DataFrame(relprop_rows),
            pd.DataFrame(rel_rows),
        )

    def filter_labels(
        self, labels: list[str], common_rel_mode: Literal["or", "and"] = "and"
    ):
        """Project the schema only for the `labels` of interest"""

        if common_rel_mode == "or":
            self.updated_relationships = self.relationships.loc[
                self.relationships["source"].isin(labels)
                | self.relationships["target"].isin(labels)
            ]
        elif common_rel_mode == "and":
            self.updated_relationships = self.relationships.loc[
                self.relationships["source"].isin(labels)
                & self.relationships["target"].isin(labels)
            ]
        else:
            raise ValueError(
                f"Provide or/and instead of {common_rel_mode} for common_rel_mode"
            )

        self.updated_rel_props = self.updated_rel_props.loc[
            self.updated_rel_props["type"].isin(
                self.updated_relationships["relationship"]
            )
        ]

        self.updated_node_props = self.node_props.loc[
            self.node_props["labels"].isin(self.updated_relationships["source"])
            | self.node_props["labels"].isin(self.updated_relationships["target"]),
        ]
        return self

    def to_llm(self, full=False, include_rel_metadata=False) -> str:
        """Convert schema to LLM-friendly string"""
        if full:
            node_props = self.node_props
            rel_props = self.rel_props
            relationships = self.relationships
        else:
            node_props = self.updated_node_props
            rel_props = self.updated_rel_props
            relationships = self.updated_relationships

        output = "Node properties are the following:\n"
        rolled_df = node_props.groupby("labels", as_index=False).agg(
            {"properties": lambda props: ",".join(props)}
        )
        output += rolled_df.to_markdown(index=False)

        output += "\n\nRelationship properties are the following:\n"
        if include_rel_metadata:
            to_drop = []
        else:
            to_drop = self.REL_METADATA

        rolled_df = (
            rel_props.loc[~rel_props["properties"].isin(to_drop)]
            .groupby("type", as_index=False)
            .agg({"properties": lambda props: ",".join(props)})
        )
        output += rolled_df.to_markdown(index=False)

        output += "\n\nRelationship point from source to target nodes:\n"
        rolled_df = (
            relationships.groupby(["source", "relationship"], as_index=False)["target"]
            .apply(lambda g: ",".join(g))
            .reset_index(drop=True)
        )
        output += rolled_df.to_markdown(index=False)

        return output

    def get_labels(self) -> list[str]:
        return list(self.node_props["labels"].unique())

if __name__ == "__main__":
    
    node_props = pd.read_csv("src/agents/iypchat/schema/node_properties.csv")
    rel_props = pd.read_csv("src/agents/iypchat/schema/relationship_properties.csv")
    rel = pd.read_csv("src/agents/iypchat/schema/relationships.csv")

    entities = ["AS", "IXP"]
    
    print("Explanations projected to entities", entities)
    print(filtered_explanations(entities))
    print()
    
    print("Neo4j schema projected to entities", entities)
    schema = Neo4jSchema(node_props=node_props, rel_props=rel_props, relationships=rel)
    print(schema.filter_labels(entities, common_rel_mode="and").to_llm())
    print()
    
    print("Neo4j schema projected to entities, from json", entities)
    schema = Neo4jSchema.from_json("schema/neo4j-schema.json")
    print(schema.filter_labels(entities, common_rel_mode="and").to_llm())
    print()
