import asyncio
from typing import List, Dict
import aiohttp
from aiohttp import ClientTimeout
import aiohttp_client_cache
from langchain_core.tools import tool
import requests
import requests_cache
import csv
import io

# Base url for api
IYP_API_BASE = "https://iyp.iijlab.net/iyp/db/neo4j/query/v2"
# Default timeout before api calls are considered failed
DEFAULT_TIMEOUT = 1800  # 180 seconds

SCHEMA = """Node properties are the following:
"labels","properties"
"Name","name"
"Country","name,country_code,alpha3"
"Tag","label"
"AuthoritativeNameServer","name"
"Ranking","name"
"Prefix","prefixlen,af,network,prefix"
"BGPCollector","name,project"
"OpaqueID","id"
"Organization","name"
"URL","url"
"PeeringdbOrgID","id"
"Facility","name"
"PeeringdbFacID","id"
"PeeringdbIXID","id"
"IXP","name"
"PeeringdbNetID","id"
"CaidaIXID","id"
"DomainName","name"
"HostName","name"
"IP","ip,af"
"AtlasProbe","country_code,asn_v6,type,prefix_v6,first_connected,prefix_v4,asn_v4,address_v4,geometry_coordinates_1,description,status_id,status_name,id,is_anchor,geometry_coordinates_0,address_v6,is_public"
"AtlasMeasurement","type,query_type,target_prefix,protocol,result,probes_requested,start_time,target_ip,target_hostname,creation_time,af,participant_count,interval,resolve_on_probe,is_oneoff,target_asn,use_probe_resolver,query_string,description,stop_time,status_id,status_name,query_class,id,probes_scheduled,method,is_public,query_argument"
"Estimate","name"
"AS","asn"

Relationship properties are the following:
"type","properties"
"NAME","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info"
"COUNTRY","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,registry"
"CATEGORIZED","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,layer,moas"
"RANK","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,cc,rank,cumulative,percent,country,hege,af,longitude,latitude"
"POPULATION","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,cc,rank,cumulative,percent,samples,value"
"ORIGINATE","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,count,af"
"PEERS_WITH","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,af,rel"
"RESERVED","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,registry"
"ASSIGNED","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,registry"
"AVAILABLE","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,registry"
"ROUTE_ORIGIN_AUTHORIZATION","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,notAfter,maxLength,notBefore"
"DEPENDS_ON","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,af,hege"
"PART_OF","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info"
"WEBSITE","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info"
"EXTERNAL_ID","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info"
"MANAGED_BY","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info"
"LOCATED_IN","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info"
"MEMBER_OF","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info"
"RESOLVES_TO","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,glue,ttl"
"SIBLING_OF","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info"
"TARGET","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info"
"PARENT","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info"
"ALIAS_OF","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info"
"QUERIED_FROM","reference_name,reference_org,reference_time_fetch,reference_url_data,reference_time_modification,reference_url_info,value"

Relationship point from source to target nodes:
"source","relationship","target"
"AtlasMeasurement","TARGET","AuthoritativeNameServer,AS,IP,HostName"
"Country","POPULATION","Estimate"
"AS","POPULATION","Country"
"AtlasProbe","LOCATED_IN","AS"
"IXP","LOCATED_IN","Facility"
"AS","LOCATED_IN","Facility"
"AS","MEMBER_OF","IXP"
"Prefix","DEPENDS_ON","AS"
"AS","DEPENDS_ON","AS"
"AuthoritativeNameServer","RANK","Ranking"
"HostName","RANK","Ranking"
"DomainName","RANK","Ranking"
"AS","RANK","Ranking"
"AS","RESERVED","OpaqueID"
"Prefix","RESERVED","OpaqueID"
"Prefix","PART_OF","Prefix"
"IP","PART_OF","Prefix"
"URL","PART_OF","AuthoritativeNameServer,HostName"
"Tag","PART_OF","Tag"
"AtlasProbe","PART_OF","AtlasMeasurement"
"AuthoritativeNameServer","PART_OF","DomainName"
"HostName","PART_OF","DomainName"
"IXP","MANAGED_BY","Organization"
"AS","MANAGED_BY","Organization"
"DomainName","MANAGED_BY","AuthoritativeNameServer,HostName"
"Facility","MANAGED_BY","Organization"
"Prefix","MANAGED_BY","IXP"
"Organization","SIBLING_OF","Organization"
"AS","SIBLING_OF","AS"
"AS","PEERS_WITH","BGPCollector,AS"
"Organization","NAME","Name"
"Facility","NAME","Name"
"AS","NAME","Name"
"IXP","NAME","Name"
"Prefix","AVAILABLE","OpaqueID"
"AS","AVAILABLE","OpaqueID"
"AS","COUNTRY","Country"
"Facility","COUNTRY","Country"
"Prefix","COUNTRY","Country"
"IXP","COUNTRY","Country"
"AtlasProbe","COUNTRY","Country"
"Ranking","COUNTRY","Country"
"Organization","COUNTRY","Country"
"AuthoritativeNameServer","RESOLVES_TO","IP"
"HostName","RESOLVES_TO","IP"
"HostName","ALIAS_OF","AuthoritativeNameServer,HostName"
"AuthoritativeNameServer","ALIAS_OF","AuthoritativeNameServer,HostName"
"AS","ROUTE_ORIGIN_AUTHORIZATION","Prefix"
"Facility","EXTERNAL_ID","PeeringdbFacID"
"AS","EXTERNAL_ID","PeeringdbNetID"
"Organization","EXTERNAL_ID","PeeringdbOrgID"
"IXP","EXTERNAL_ID","CaidaIXID,PeeringdbIXID"
"DomainName","QUERIED_FROM","AS,Country"
"Prefix","ASSIGNED","OpaqueID"
"AS","ASSIGNED","OpaqueID"
"IP","ASSIGNED","AtlasProbe"
"DomainName","PARENT","DomainName"
"AS","ORIGINATE","Prefix"
"URL","CATEGORIZED","Tag"
"Prefix","CATEGORIZED","Tag"
"AS","CATEGORIZED","Tag"
"IXP","WEBSITE","URL"
"Organization","WEBSITE","URL"
"AS","WEBSITE","URL"
"Facility","WEBSITE","URL"""

TO_REMOVE = [
        "reference_org",
        "reference_url",
        "reference_url_info",
        "reference_time_fetch",
        "reference_name",
        "reference_time_modification",
        "reference_url_data"
    ]

def filter_internal_fields(api_result: list):
    """Remove non essential fields that might confuse the LLM"""
    for elem in api_result:
        for key, val in elem.items():
            for remove_me in TO_REMOVE:
                val.pop(remove_me, None)
    return api_result

def parse_node_schema(schema_str: str) -> Dict[str, List[str]]:
    """
    Parse the SCHEMA text and extract node properties as a mapping:
        label -> list of property names
    """
    # Split off the node properties section before the first blank line after the header
    sections = schema_str.split("\n\n")
    node_section = sections[0]

    # Skip the first two lines (description + CSV header)
    lines = node_section.splitlines()[2:]

    reader = csv.reader(lines)
    schema_map: Dict[str, List[str]] = {}
    for row in reader:
        if len(row) != 2:
            continue
        label, props = row
        # strip quotes if present
        label = label.strip('"')
        props_list = [p.strip() for p in props.strip('"').split(",") if p]
        schema_map[label] = props_list

    return schema_map


def get_filtered_node_schema(
    labels: List[str], schema_str: str = SCHEMA
) -> Dict[str, List[str]]:
    """
    Return a subset of the node schema containing only the specified labels.

    Args:
        labels: A list of node labels to filter by.
        schema_str: The SCHEMA string to parse.

    Returns:
        A dict mapping each requested label to its list of properties.
        Labels not found in the schema will be omitted.
    """
    node_schema = parse_node_schema(schema_str)
    filtered = {label: node_schema[label] for label in labels if label in node_schema}
    return filtered


def format_response(results: Dict) -> List[Dict]:
    """Format the response data"""
    result_list = []
    keys = results["fields"]

    for row in results["values"]:
        obj = {}
        count_elements_in_row = 0

        for row_val in row:
            if isinstance(row_val, dict):
                if "properties" in row_val:
                    obj[keys[count_elements_in_row]] = row_val["properties"]
                else:
                    obj[keys[count_elements_in_row]] = row_val
            elif isinstance(row_val, list):
                obj[keys[count_elements_in_row]] = [
                    val["properties"]
                    if isinstance(val, dict) and "properties" in val
                    else val
                    for val in row_val
                ]
            else:
                obj[keys[count_elements_in_row]] = row_val

            count_elements_in_row += 1

        # Convert None values properly
        result_list.append(obj)

    return result_list

def run_iyp_query(query: str, use_cache: bool = True) -> Dict:
    """
    Executes an IYP (Internet Yellow Pages) Cypher query synchronously, with optional caching.

    Args:
        query (str): A Cypher query like "MATCH (n) RETURN n LIMIT 5".
        use_cache (bool, optional): Whether to cache the HTTP responses. Defaults to True.

    Returns:
        Dict: Formatted query result.

    Raises:
        requests.exceptions.RequestException: If the HTTP request fails or returns a non-202 status.
    """
    timeout = DEFAULT_TIMEOUT  # seconds

    # Set up session: cached or plain
    if use_cache:
        session = requests_cache.CachedSession(
            cache_name="iyp_cache",
            backend="sqlite",
            expire_after=None,  # you can set a TTL here if desired
        )
    else:
        session = requests.Session()

    try:
        # Prepare payload
        payload = {"statement": query, "parameters": {}}
        resp = session.post(IYP_API_BASE, json=payload, timeout=timeout)

        # Raise for any HTTP error
        if resp.status_code != 202:
            resp.raise_for_status()

        data = resp.json().get("data", [])
        try:
            return filter_internal_fields(format_response(data))
        except AttributeError:
            return format_response(data)

    finally:
        session.close()


async def arun_iyp_query(query: str, use_cache: bool = True) -> Dict:
    """
    Executes a IYP (Internet Yellow Pages) Cypher query asynchronously, with optional caching.

    Args:
        query (str): A Cypher query like "MATCH (n) RETURN n LIMIT 5".
        use_cache (bool, optional): Whether to cache the HTTP responses. Defaults to True.

    Returns:
        Dict: Formatted query result.

    Raises:
        aiohttp.ClientError: If the API response status is not 202 (accepted).
    """

    timeout = ClientTimeout(total=DEFAULT_TIMEOUT)

    # Use cached session if requested, otherwise regular session
    if use_cache:
        session = aiohttp_client_cache.CachedSession(
            cache=aiohttp_client_cache.SQLiteBackend(), timeout=timeout
        )
    else:
        session = aiohttp.ClientSession(timeout=timeout)

    try:
        async with session:

            # Convert query format if needed (query -> statement)
            request_body = {"statement": query, "parameters": {}}

            response = await session.post(IYP_API_BASE, json=request_body)
            if response.status != 202:  # Neo4j Query API returns 202 for success
                error_text = await response.text()
                raise aiohttp.ClientError(
                    f"API Error {response.status}: {error_text}"
                )
            
            response = await response.json() 
        try:
            return filter_internal_fields(format_response(response["data"]))
        except AttributeError:
            return format_response(response["data"])
            

    finally:
        if not session.closed:
            await session.close()


async def run_iyp_queries(
    queries: List[str], use_cache: bool = True
) -> List[List[Dict]]:
    """
    Executes a list of IYP (Internet Yellow Pages) Cypher queries asynchronously, with optional caching.

    Args:
        queries (List[str]): A list of Cypher queries like
            "MATCH (n) RETURN n LIMIT 5".
        use_cache (bool, optional): Whether to cache the HTTP responses. Defaults to True.

    Returns:
        List[List[Dict]]: A list of formatted query result sets. Each result set is a list of dictionaries.

    Raises:
        aiohttp.ClientError: If the API response status is not 202 (accepted).
    """

    timeout = ClientTimeout(total=DEFAULT_TIMEOUT)

    # Use cached session if requested, otherwise regular session
    if use_cache:
        session = aiohttp_client_cache.CachedSession(
            cache=aiohttp_client_cache.SQLiteBackend(), timeout=timeout
        )
    else:
        session = aiohttp.ClientSession(timeout=timeout)

    try:
        async with session:
            tasks = []

            for query in queries:
                # Convert query format if needed (query -> statement)
                request_body = {"statement": query, "parameters": {}}
                print(request_body)

                async def fetch_query(q=request_body):
                    async with session.post(IYP_API_BASE, json=q) as response:
                        if (
                            response.status != 202
                        ):  # Neo4j Query API returns 202 for success
                            error_text = await response.text()
                            raise aiohttp.ClientError(
                                f"API Error {response.status}: {error_text}"
                            )
                        return await response.json()

                tasks.append(fetch_query())

            responses = await asyncio.gather(*tasks)

        return [format_response(res["data"]) for res in responses]

    finally:
        if not session.closed:
            await session.close()
            

if __name__ == "__main__":
        
    queries = ["MATCH (n) RETURN n LIMIT 5", "MATCH (n) RETURN n LIMIT 2"]

    # res = asyncio.run(run_iyp_queries(queries, use_cache=True))
    # print(res)

    # selected = ["AS", "IXP", "UnknownLabel"]
    # result = get_filtered_node_schema(selected)
    # print(result)
    
    
    few_shots = [
        r"MATCH (:AS {asn: 2497})-[:MEMBER_OF]->(ixp:IXP) RETURN DISTINCT ixp.name",
        r"""MATCH (gdns:Prefix {prefix:'8.8.8.0/24'})-[relationship]-(neighbor:Tag {label:"RPKI Valid"}) RETURN neighbor, relationship""",
        r"MATCH (:Ranking)-[r:RANK]-(domain:DomainName)--(:HostName)--(:IP)--(:Prefix)-[:ORIGINATE]-(:AS)-[:COUNTRY]-(cc:Country) WHERE r.rank<10000 AND domain.name ENDS WITH '.ru' RETURN cc.country_code, count(DISTINCT domain.name) AS dm_count ORDER BY dm_count DESC LIMIT 10",
        r"""MATCH (as:AS)-[:PEERS_WITH]->(collector:BGPCollector {name: 'rrc25'}), (as)-[r {reference_org:"BGP.Tools"}]-(n:Name) RETURN n.name AS peerName, as.asn as ASN LIMIT 10"""
    ]
    
    # results = asyncio.run(run_iyp_queries(few_shots, use_cache=True))
    # print(results)
    
    results = run_iyp_query(few_shots[-1])
    
    # results = asyncio.run(
    #     arun_iyp_query(
    #         few_shots[-1]
    #     )
    # )
    # long_res: list[dict] = results
    print(results)
    # print(long_res)
    
    # for elem in long_res:
    #     for key, val in elem.items():
    #         for remove_me in TO_REMOVE:
    #             val.pop(remove_me, None)
        
    # print(long_res)[{'neighbor': {'prefixlen': 8, 'af': 4, 'prefix': '8.0.0.0/8', 'network': '8.0.0.0'}, 'relationship': {'prefix_types': ['RDNSPrefix']}}, {'neighbor': {'prefixlen': 12, 'af': 4, 'prefix': '8.0.0.0/12', 'network': '8.0.0.0'}, 'relationship': {'prefix_types': ['BGPPrefix']}}, {'neighbor': {'af': 4, 'ip': '8.8.8.4'}, 'relationship': {'prefix_types': ['RPKIPrefix', 'RIRPrefix', 'BGPPrefix', 'RDNSPrefix']}}, {'neighbor': {'af': 4, 'ip': '8.8.8.59'}, 'relationship': {'prefix_types': ['RPKIPrefix', 'RIRPrefix', 'BGPPrefix', 'RDNSPrefix']}}, {'neighbor': {'af': 4, 'ip': '8.8.8.57'}, 'relationship': {'prefix_types': ['RPKIPrefix', 'RIRPrefix', 'BGPPrefix', 'RDNSPrefix']}}, {'neighbor': {'af': 4, 'ip': '8.8.8.8'}, 'relationship': {'prefix_types': ['RPKIPrefix', 'RIRPrefix', 'BGPPrefix', 'RDNSPrefix']}}, {'neighbor': {'name': 'ns4.google.com'}, 'relationship': {'source': 'ARIN', 'ttl': 86400}}, {'neighbor': {'name': 'ns1.google.com'}, 'relationship': {'source': 'ARIN', 'ttl': 86400}}, {'neighbor': {'name': 'ns2.google.com'}, 'relationship': {'source': 'ARIN', 'ttl': 86400}}, {'neighbor': {'name': 'ns3.google.com'}, 'relationship': {'source': 'ARIN', 'ttl': 86400}}, {'neighbor': {'asn': 15169}, 'relationship': {'count': 72, 'seen_by_collectors': ['route-collector.ros.pch.net', 'route-collector.cdg.pch.net', 'route-collector.decix-bcn.mad.pch.net', 'route-collector.dfw.pch.net', 'route-collector.ams.pch.net', 'route-collector.lhr.pch.net', 'route-collector.beg.pch.net', 'route-collector.sfo.pch.net', 'route-collector.lux.pch.net', 'route-collector.decix.bom2.pch.net', 'route-collector.sof.pch.net', 'route-collector.lis.pch.net', 'route-collector.sna.pch.net', 'route-collector.bom2.pch.net', 'route-collector.los.pch.net', 'route-collector.bcn.pch.net', 'route-collector.pss.pch.net', 'route-collector.bur.pch.net', 'route-collector.espanix-mad.pch.net', 'route-collector.sea.pch.net', 'route-collector.mba.pch.net', 'route-collector.mia.pch.net', 'route-collector.dtw.pch.net', 'route-collector.yul.pch.net', 'route-collector.lonap.pch.net', 'route-collector.yxe.pch.net', 'route-collector.amsix-sfo.pch.net', 'route-collector.dub.pch.net', 'route-collector.bvy.pch.net', 'route-collector.aep.pch.net', 'route-collector.scl.pch.net', 'route-collector.unitedix-ord.pch.net', 'route-collector.dal.pch.net', 'route-collector.acc.pch.net', 'route-collector.pao.pch.net', 'route-collector.nrt.pch.net', 'route-collector.kbp.pch.net', 'route-collector.iad.pch.net', 'route-collector.kul.pch.net', 'route-collector.mcix.pch.net', 'route-collector.decix-muc.fra.pch.net', 'route-collector.den.pch.net', 'route-collector.prg.pch.net', 'route-collector.mad.pch.net', 'route-collector.netix.pch.net', 'route-collector.ecix-fra.pch.net', 'route-collector.lga.pch.net', 'route-collector.megaport-sof.pch.net', 'route-collector.decix-lis.mad.pch.net', 'route-collector.jnb.pch.net', 'route-collector.ham.pch.net', 'route-collector.tie-ny.pch.net', 'route-collector.atl.pch.net', 'route-collector.megaport-syd.pch.net', 'route-collector.jhb.pch.net', 'route-collector.napafrica-jnb.pch.net', 'route-collector.waw.pch.net', 'route-collector.nl-ix.pch.net', 'route-collector.bog2.pch.net', 'route-collector.fra.pch.net', 'route-collector.equinix-dallas.dfw.pch.net', 'route-collector.otp.pch.net', 'route-collector.decix-ny.lga.pch.net', 'route-collector.icn.pch.net', 'route-collector.los2.pch.net', 'route-collector.ord.pch.net', 'route-collector.zrh.pch.net', 'route-collector.syd.pch.net', 'route-collector.equinix-sg.pch.net', 'route-collector.qpg.pch.net', 'route-collector.ecix-muc.fra.pch.net', 'route-collector.nsw-ix.pch.net']}}, {'neighbor': {'label': 'Anycast'}, 'relationship': {}}, {'neighbor': {'name': 'United States of America', 'country_code': 'US', 'alpha3': 'USA'}, 'relationship': {}}, {'neighbor': {'asn': 15169}, 'relationship': {'visibility': 100.0, 'af': 4, 'prefix': '8.8.8.0/24', 'moas': 'f', 'hege': 1.0, 'delegated_asn_status': 'assigned', 'asn_id': '15169', 'descr': 'Google', 'irr_status': 'Valid', 'timebin': '2025-05-13 00:00:00+00', 'delegated_prefix_status': 'assigned', 'rpki_status': 'Valid', 'originasn_id': '15169', 'id': '0', 'country_id': 'US'}}, {'neighbor': {'label': 'IRR Valid'}, 'relationship': {'visibility': 100.0, 'af': 4, 'prefix': '8.8.8.0/24', 'moas': 'f', 'hege': 1.0, 'delegated_asn_status': 'assigned', 'asn_id': '15169', 'descr': 'Google', 'irr_status': 'Valid', 'timebin': '2025-05-13 00:00:00+00', 'delegated_prefix_status': 'assigned', 'rpki_status': 'Valid', 'originasn_id': '15169', 'id': '0', 'country_id': 'US'}}, {'neighbor': {'label': 'RPKI Valid'}, 'relationship': {'visibility': 100.0, 'af': 4, 'prefix': '8.8.8.0/24', 'moas': 'f', 'hege': 1.0, 'delegated_asn_status': 'assigned', 'asn_id': '15169', 'descr': 'Google', 'irr_status': 'Valid', 'timebin': '2025-05-13 00:00:00+00', 'delegated_prefix_status': 'assigned', 'rpki_status': 'Valid', 'originasn_id': '15169', 'id': '0', 'country_id': 'US'}}, {'neighbor': {'asn': 15169}, 'relationship': {'visibility': 100.0, 'af': 4, 'prefix': '8.8.8.0/24', 'moas': 'f', 'hege': 1.0, 'delegated_asn_status': 'assigned', 'asn_id': '15169', 'descr': 'Google', 'irr_status': 'Valid', 'timebin': '2025-05-13 00:00:00+00', 'delegated_prefix_status': 'assigned', 'rpki_status': 'Valid', 'originasn_id': '15169', 'id': '0', 'country_id': 'US'}}, {'neighbor': {'asn': 15169}, 'relationship': {'notAfter': '2025-07-22 13:01:01', 'uri': 'rsync://rpki.arin.net/repository/arin-rpki-ta/5e4a23ea-e80a-403e-b08c-2171da2157d3/f60c9f32-a87c-4339-a2f3-6299a3b02e29/5e9328a9-e1d2-45d8-bdb5-eefe152994f9/d74ad38d-11d3-3c79-a22a-29626dd55bea.roa', 'notBefore': '2025-04-23 13:01:01', 'maxLength': '24'}}, {'neighbor': {'id': '9d99e3f7d38d1b8026f2ebbea4017c9f'}, 'relationship': {'registry': 'arin'}}, {'neighbor': {'name': 'United States of America', 'country_code': 'US', 'alpha3': 'USA'}, 'relationship': {'registry': 'arin'}}, {'neighbor': {'asn': 15169}, 'relationship': {'prefix': '8.8.8.0/24', 'count': 767, 'asn': 15169}}]