entity_examples = [
    {
        "user": "Find the IXPs' names where the AS with asn 2497 is present.",
        "assistant": ["IXP", "AS"],
    },
    {
        "user": "Return everything that is related with 8.8.8.0/24.",
        "assistant": ["Prefix"],
    },
    {
        "user": "Get the country codes of ASes hosting .ru domain names and that are ranked in the top100. Return the country code and corresponding number of unique domain names.",
        "assistant": ["Country", "AS", "DomainName", "Ranking"],
    },
    {
        "user": "Get the names and ASN of the AS peering with rrc25",
        "assistant": ["AS", "Name", "BGPCollector"],
    },
]

cypher_examples = [
    {
        "user": "Find the IXPs' names where the AS with asn 2497 is present.",
        "assistant": "MATCH (:AS {{asn: 2497}})-[:MEMBER_OF]->(ixp:IXP) RETURN DISTINCT ixp.name",
    },
    {
        "user": "Return everything that is related with 8.8.8.0/24.",
        "assistant": "MATCH (gdns:Prefix {{prefix:'8.8.8.0/24'}})--(neighbor) RETURN neighbor",
    },
    {
        "user": "Get the names and ASN of the AS peering with rrc25",
        "assistant": "MATCH (as:AS)-[:PEERS_WITH]->(collector:BGPCollector {{name: 'rrc25'}}), (as)-[r {{reference_org:'BGP.Tools'}}]-(n:Name) RETURN n.name AS peerName, as.asn as ASN;",
    },
]

presenter_examples = [
    {
        "user": "Find the IXPs' names where the AS with asn 2497 is present.\n[{{'ixp.name': 'Equinix Los Angeles'}}, {{'ixp.name': 'DE-CIX Frankfurt'}}]",
        "assistant": "AS with ASN 2497 is present at IXPs Equinix Los Angeles and DE-CIX Frankfurt",
    },
    {
        "user": "Get the RPKI status of 8.8.8.0/24 \n[{{'neighbor': {{'label': 'RPKI Valid'}}, 'relationship': {{'visibility': 100.0, 'af': 4, 'prefix': '8.8.8.0/24', 'moas': 'f', 'hege': 1.0, 'delegated_asn_status': 'assigned', 'asn_id': '15169', 'descr': 'Google', 'irr_status': 'Valid', 'timebin': '2025-05-13 00:00:00+00', 'delegated_prefix_status': 'assigned', 'rpki_status': 'Valid', 'originasn_id': '15169', 'id': '0', 'country_id': 'US'}}}}]",
        "assistant": "The RPKI status tag on the prefix 8.8.8.0/24 is valid, with the following key details:\n* **Prefix:** 8.8.8.0/24 (IPv4, AF=4)\n* **Origin ASN:** 15169 (Google)\n* **RPKI Status:** Valid\n* **IRR Status:** Valid\n* **Delegated ASN Status:** assigned\n* **Delegated Prefix Status:** assigned\n* **Multi-origin (MOAS):** false\n* **Visibility Score:** 100.0\n* **HEGE Score:** 1.0\n* **Country:** US\n* **Snapshot Time:** 2025-05-13 00:00:00 UTC",
    },
    {
        "user": "Get the names and ASN of the AS peering with rrc25\n[{{'peerName': 'GoCodeIT Inc', 'ASN': 835}}, {{'peerName': 'Dream Fusion - IT Services, Lda', 'ASN': 39384}}, {{'peerName': 'Eviny Digital AS', 'ASN': 30950}}, {{'peerName': 'Aztelekom LLC', 'ASN': 34170}}, {{'peerName': 'Sri Lanka Telecom PLC', 'ASN': 45489}}, {{'peerName': 'EWS DS Networks Inc', 'ASN': 142271}}, {{'peerName': 'A1 Hrvatska d.o.o.', 'ASN': 15994}}, {{'peerName': 'Emirates Integrated Telecommunications Company PJSC', 'ASN': 57187}}, {{'peerName': 'SIACOM JSC', 'ASN': 198150}}, {{'peerName': 'Sky Digital Co., Ltd.', 'ASN': 134823}}]",
        "assistant": "The names and ASN of the AS peering with rrc25 are: GoCodeIT Inc (ASN835), Dream Fusion - IT Services, Lda (ASN39384), Eviny Digital AS (ASN30950), Aztelekom LLC (ASN34170), Sri Lanka Telecom PLC (ASN45489), EWS DS Networks Inc (ASN142271), A1 Hrvatska d.o.o. (ASN15994), Emirates Integrated Telecommunications Company PJSC (ASN57187), SIACOM JSC (ASN198150), Sky Digital Co., Ltd. (ASN134823).",
    },
]
