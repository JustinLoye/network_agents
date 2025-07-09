import datetime
import re
import requests
import subprocess

from geopy.geocoders import Nominatim
from langchain_core.tools import tool


def extract_tool(content: str):
    extracted = re.findall(r"<tool>(.*?)</tool>", content, flags=re.DOTALL)
    return extracted  # returns a list of all matches


def remove_tool(content: str):
    cleaned = re.sub(r"<tool>.*?</tool>\s*", "", content, flags=re.DOTALL)
    return cleaned


def get_geoloc(name: str) -> tuple[float, float]:
    geolocator = Nominatim(user_agent="myapplication")
    location = geolocator.geocode(name)
    return location.latitude, location.longitude


@tool(parse_docstring=True)
def get_current_weather(city: str):
    """
    Get the current temperature and wind speed for a given city.

    Args:
        city (str): The name of the city to retrieve weather information for.

    Returns:
        dict: A dictionary containing the current weather data, including temperature and wind speed.

    Raises:
        Exception: If the API request fails or the response does not contain the expected data.
    """
    latitude, longitude = get_geoloc(city)
    lat_lng = f"latitude={latitude}&longitude={longitude}"
    url = f"https://api.open-meteo.com/v1/forecast?{lat_lng}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    response = requests.get(url)
    json = response.json()
    return f"<tool>{json['current']}</tool>"


@tool(parse_docstring=True)
def get_current_time() -> str:
    """
    Get the current time.

    Returns:
        str: The current time in the "%Y-%m-%d %H:%M:%S" format
    """

    # No tzinfo
    return f"<tool>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</tool>"


@tool(parse_docstring=True)
def ping(host: str, count: int = 4) -> str:
    """
    Sends ICMP echo requests to a given host to test connectivity.

    Args:
        host (str): The target host to ping (e.g., "google.com" or "8.8.8.8").
        count (int, optional): Number of echo requests to send. Defaults to 4.

    Returns:
        str: The raw output from the ping command.
    """
    result = subprocess.run(
        ["ping", "-c", str(count), host],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    res = result.stdout if result.returncode == 0 else result.stderr
    return f"<tool>{res}</tool>"


@tool(parse_docstring=True)
def traceroute(host: str, max_hops: int = 30) -> str:
    """
    Traces the route packets take to reach the specified host.

    Args:
        host (str): The destination host or IP address.
        max_hops (int, optional): Maximum number of hops to probe. Defaults to 30.

    Returns:
        str: The raw output from the traceroute command, i.e. a list of ips and hostnames with the latency and hop number.
    """
    result = subprocess.run(
        ["traceroute", "-m", str(max_hops), host],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout if result.returncode == 0 else result.stderr


@tool(parse_docstring=True)
def get_routing_table():
    """
    Retrieves the current IP routing table of the system. Useful to get the router ip.

    This function executes the `ip route show` command using the subprocess module
    to query the system's routing table. The output is returned as a decoded string.

    Returns:
        str: A string containing the routing table as output by the `ip route show` command.

    Raises:
        subprocess.CalledProcessError: If the `ip route` command fails to execute.
        FileNotFoundError: If the `ip` command is not found on the system.
    """
    result = subprocess.run(
        ["ip", "route", "show"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    res = result.stdout if result.returncode == 0 else result.stderr
    return f"<tool>{res}</tool>"

NETWORKING_TOOLS = [
    get_current_time,
    ping,
    get_routing_table,
    traceroute,
]

if __name__ == "__main__":
    
    print(get_current_time.invoke(""))
    print(ping.invoke("google.com"))
    print(get_routing_table.invoke(""))
    print(traceroute.invoke("google.com"))
