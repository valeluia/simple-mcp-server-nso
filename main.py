from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List

import ncs
import logging
import os

from tools import SyncResult, DeviceInfo, build_device_info


class Configuration:
    """Manages configuration and environment variables for the MCP client."""

    def __init__(self) -> None:
        """Initialize configuration with environment variables."""
        self.load_env()
        self.nso_user = os.getenv("NSO_USER", 'nsoadmin')
        self.nso_context = os.getenv("NSO_CONTEXT", 'system')
        self.api_port = os.getenv("API_PORT", 8000)
        self.logdir = os.getenv("LOG_DIRECTORY", "/var/log/ncs")


    @staticmethod
    def load_env() -> None:
        """Load environment variables from .env file."""
        load_dotenv()

    @property
    def get_openai_api_key(self) -> str:
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        return self.openai_api_key

config = Configuration()

# Setup logger
logname = os.path.join(config.logdir, "ncs-python-mcp-server.log")

open(logname, 'a').close()  # Create empty file
os.chmod(logname, 0o600) 

logging.basicConfig(filename=logname,
                    filemode='a+',
                    format='%(asctime)s.%(msecs)02d %(filename)s:%(lineno)s %(levelname)s: %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Create an MCP server
mcp = FastMCP(
    name="NSO MCP Server",
    host="0.0.0.0",
    port=config.api_port,  
    stateless_http=True,
)

@mcp.tool()
async def get_neds_list() -> list[str]:
    """
    get list of NEDs (Network Element Drivers) from NSO
    
    Returns:
        list[str]: A list of NEDs from the NSO server.
    """
    logger.info(f"Getting NEDs list")
    neds_list = []
    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as read_trans:
        root = ncs.maagic.get_root(read_trans)
        
        for ned in root.ncs__devices.ned_ids.ned_id:
            if ned.id in ['ned:lsa-netconf', 'ned:netconf', 'ned:snmp']:
                continue

            if len(ned.id.split(':')) == 2:
                neds_list.append(ned.id.split(':')[1])
            else:
                neds_list.append(ned.id)

    return neds_list

@mcp.tool()
async def get_devices_name_list() -> list[str]:
    """
    Get a list of network devices from the NSO server.
    
    Returns:
        list[str]: A list of network devices from the NSO server.
    """
    logger.info(f"Getting devices name list")
    devices_name_list = []
    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as read_trans:
        root = ncs.maagic.get_root(read_trans)
        
        for device in root.devices.device:
            devices_name_list.append(device.name)
    
    return devices_name_list

@mcp.tool()
async def get_devices_groups_list() -> list[str]:
    """
    Get a list of device groups from the NSO server.
    
    Returns:
        list[str]: A list of device groups from the NSO server.
    """
    logger.info(f"Getting devices name list")
    device_group_list = []
    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as read_trans:
        root = ncs.maagic.get_root(read_trans)
        
        for group in root.devices.device_group:
            device_group_list.append(group.name)
    
    return device_group_list

@mcp.tool()
async def get_device_info(device_name: str) -> DeviceInfo:
    """
    Get information about a network device from the NSO server.

    Args:
        device_name (str): The name of the network device to get information about.

    Returns:
        DeviceInfo: device information from NSO CDBa
    """
    logger.info(f"Getting device info for {device_name.strip()}")
    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as read_trans:
        root = ncs.maagic.get_root(read_trans)
                
        if root.devices.device.exists(device_name.strip()):
            device = root.ncs__devices.device[device_name.strip()]
            result = build_device_info(device)
        else:
            logger.info(f"Device {device_name.strip()} not found")
            raise ValueError(f"Device {device_name.strip()} not found in NSO CDB")

        return result

@mcp.tool()
async def check_sync_devices_status(device_name: str) -> str:
    """
    Check if network device configuration in NSO server is in sync with CDB

    Args:
        device_name (str): The name of the network device to get information about.

    Returns:
        str: in-sync if configuration is in sync, out-of-sync if configuration is not in sync, unsupported if the device doesn't support the function
    """
    logger.info(f"Check sync status for device {device_name.strip()}")
    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as read_trans:
        root = ncs.maagic.get_root(read_trans)
        result = root.ncs__devices.device[device_name.strip()].check_sync()

        return str(result.ncs__result)

@mcp.tool()
async def sync_device(device_name: str) -> SyncResult:
    """
    Sync network device configuration with NSO CDB

    Args:
        device_name (str): The name of the network device to get information about.

    Returns:
        str: true if sync was performed successfuly, and false otherwise
    """
    logger.info(f"Syncing configuration for device {device_name.strip()}")
    with ncs.maapi.Maapi() as m:
        with ncs.maapi.Session(m, config.nso_user, config.nso_context):
            with m.start_write_trans() as trans:
                root = ncs.maagic.get_root(trans)
                result = root.ncs__devices.device[device_name.strip()].sync_from()

                return SyncResult(name=device_name.strip(), result=str(result.ncs__result))

@mcp.tool()
async def sync_device_group(device_group_name: str) -> List[SyncResult]:
    """
    Sync all devices config from a specific NSO device group 

    Args:
        device_group (str): The name of the NSO device group

    Returns:
        str: true if sync was performed successfuly, and false otherwise
    """
    logger.info(f"Syncing configuration for device group {device_group_name.strip()}")
    result_list = []
    with ncs.maapi.Maapi() as m:
        with ncs.maapi.Session(m, config.nso_user, config.nso_context):
            with m.start_write_trans() as trans:
                root = ncs.maagic.get_root(trans)

                if not root.ncs__devices.device_group.exists(device_group_name.strip()):
                    raise ValueError(f"The device group {device_group_name.strip()} could not be found in NSO CDB")

                result = root.ncs__devices.device_group[device_group_name.strip()].sync_from()

                for item_result in result.sync_result:
                    sync_result = SyncResult(name=item_result.device, result=str(item_result.result))
                    result_list.append(sync_result)

                return result_list

@mcp.tool()
async def get_devices_from_device_group(device_group_name: str) -> list[str]:
    """
    Get a list of network devices from the NSO server that match the given device group.

    Args:
        device_group_name (str): The name of the device group to get the list of devices for.

    Returns:
        list[str]: A list of network devices from the NSO server.
    """
    logger.info(f"Getting devices list from device group {device_group_name.strip()}")
    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as read_trans:
        root = ncs.maagic.get_root(read_trans)
        
        if root.ncs__devices.device_group.exists(device_group_name.strip()):
            group = root.devices.device_group[device_group_name.strip()]
            return group.device_name.as_list()
        else:
            raise ValueError(f"The device group {device_group_name.strip()} could not be found in NSO CDB")
    

@mcp.tool()
async def get_devices_list_per_model(model: str) -> list[DeviceInfo]:
    """
    Get a list of network devices from the NSO server that match the given model.
    
    Args:
        model (str): The model of the network device to get the list of devices for. Options: "junos", "arcos", "nokia" "saos", "ios-xe" ,"ios", "ios-xr".

    Returns:
        list[DeviceInfo]: A list of network devices information from the NSO server
    """
    clean_model = model.strip().lower()
    logger.info(f"Getting devices list per model {clean_model}")
    devices_name_list = []
    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as read_trans:
        root = ncs.maagic.get_root(read_trans)
        
        for device in root.devices.device:
            if clean_model in device.platform.name.lower():
                device_info = build_device_info(device)
                devices_name_list.append(device_info)
    
    return devices_name_list

@mcp.tool()
async def get_devices_list_per_model_and_version(model: str, version: str) -> list[DeviceInfo]:
    """
    Get a list of network devices from the NSO server that match the given model and version.
    
    Args:
        model (str): The model of the network device to get the list of devices for. Options: "junos", "arcos", "nokia" "saos", "ios-xe" ,"ios", "ios-xr".
        version (str): The version of the network device to get the list of devices for.
    
    Returns:
        list[DeviceInfo]: A list of network devices information from the NSO server
    """
    clean_model = model.strip().lower()
    clean_version = version.strip().lower()
    logger.info(f"Getting devices list per model {clean_model} and version {clean_version}")
    devices_name_list = []
    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as read_trans:
        root = ncs.maagic.get_root(read_trans)
        
        for device in root.devices.device:
            if clean_model in device.platform.name.lower() and clean_version in device.platform.version.lower():
                device_info = build_device_info(device)
                devices_name_list.append(device_info)
    
    return devices_name_list

@mcp.tool()
async def get_devices_list_per_model_dont_match_version(model: str, version: str) -> list[DeviceInfo]:
    """
    Get a list of network devices from the NSO server that match the given model but dont match the provided version.
    (e.g. get all devices that are cisco xr and not running version 7.2)
    
    Args:
        model (str): The model of the network device to get the list of devices for. Options: "junos", "arcos", "nokia" "saos", "ios-xe" ,"ios", "ios-xr".
        version (str): The version of the network device to get the list of devices for.
    
    Returns:
        list[DeviceInfo]: A list of network devices information from the NSO server
    """
    clean_model = model.strip().lower()
    clean_version = version.strip().lower()
    logger.info(f"Getting devices list per model {clean_model} and version not{clean_version}")
    devices_name_list = []
    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as read_trans:
        root = ncs.maagic.get_root(read_trans)
        
        for device in root.devices.device:
            if clean_model in device.platform.name.lower() and not clean_version in device.platform.version.lower():
                device_info = build_device_info(device)
                devices_name_list.append(device_info)
    
    return devices_name_list

@mcp.tool()
async def get_day1_services() -> list[str]:
    """
    Get a list of day1 services from the NSO server.
    """
    DAY1_TEMPLATE = "-day1-"
    logger.info(f"Getting day1 services")
    list_results = []

    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as t:
        root = ncs.maagic.get_root(t)

        for service in root.ncs__services:
            if DAY1_TEMPLATE in service:
                split_output = service.split(":", 1)
                
                if len(split_output) == 2:
                   list_results.append(split_output[1].strip())
                else:
                    list_results.append(service)

    return list_results


@mcp.tool()
async def get_all_services() -> list[str]:
    """
    Get a list of all services from the NSO server.
    """
    logger.info(f"Getting day1 services")
    list_results = []

    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as t:
        root = ncs.maagic.get_root(t)

        for service in root.ncs__services:
            split_output = service.split(":", 1)
            
            if len(split_output) == 2:
                list_results.append(split_output[1].strip())
            else:
                list_results.append(service)

    return list_results

@mcp.tool()
async def get_device_configured_services(device_name: str) -> list[str]:
    """
    Get a list of services configured for a device from NSO CDB.
    
    Returns:
        list[str]: a list of services NSO xpath
    """
    logger.info(f"Getting services for device {device_name.strip()}")
    service_list = []
    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as read_trans:
        root = ncs.maagic.get_root(read_trans)
        
        if not device_name.strip() in root.ncs__devices.device:
            raise ValueError(f'Device {device_name.strip()} not found in NSO CDB')

        for service in root.devices.device[device_name.strip()].service_list:
            service_list.append(service)
    
    return service_list


@mcp.tool()
async def check_service_sync_status(ncs_keypath: str) -> str:
    """
    check if the service is in sync based on the NSO xpath. The xpath needs to have the following structure: '/ncs:services/service_name:service_name{device_name}'
    
    Returns:
        str: if the service is in-sync or not 
    """
    logger.info(f"Checking sync status for service {ncs_keypath}")
    service_list = []
    with ncs.maapi.single_read_trans(config.nso_user, config.nso_context) as read_trans:
        root = ncs.maagic.get_root(read_trans)

        service = ncs.maagic.get_node(root, ncs_keypath)

        result = service.check_sync()

        return str(result.in_sync)


# Run the server
if __name__ == "__main__":
    logger.info(f"Starting NSO MCP server with Streamable HTTP transport in port {config.api_port}")
    mcp.run(transport="streamable-http")
