import ncs

from pydantic import BaseModel, Field
from typing import List


class SyncResult(BaseModel):
    name: str = Field(description="The name of the network device")
    result: str = Field(description="Sync operation result")


class DeviceInfo(BaseModel):
    name: str = Field(description="The name of the network device")
    address: str = Field(description="The address of the network device")
    platform_version: str = Field(description="The software version of the network device")
    platform_name: str = Field(description="The name of the network device (e.g. junos, cisco, arcos, nokia, ios, ios-xr, ios-xe)")
    platform_model: str = Field(description="The model of the network device")
    ned_type: str =  Field(description="device NED type used by NSO (netconf or cli)") 
    ned: str = Field(description="NED (Network Element Driver) used by NSO to connect to device")


def build_device_info(device: ncs.maagic.ListElement) -> DeviceInfo:
    """
    Build device information for a device from NSO

    Args:
        device (ncs.maagic.ListElement): device element from NSO CDB

    Returns:
        DeviceInfo with the device's information:
            - name: The name of the network device.
            - address: The address of the network device.
            - platform-version: The software version of the network device.
            - platform-name: The name of the network device (e.g. junos, cisco, arcos, nokia).
            - platform-model: The model of the network device.
            - ned-type: device NED (Network Element Driver) type used by NSO (netconf or cli)
            - ned: NED (Network Element Driver) used by NSO to connect to device
    """

    if device.device_type.netconf.ned_id:
        ned_type = 'netconf'
        ned = device.device_type.netconf.ned_id

    elif device.device_type.cli.ned_id:
        ned_type = 'cli'
        ned = device.device_type.cli.ned_id

    else:
        ned_type = 'unknown'
        ned = 'unknown'

    if len(ned.split(':')) == 2:
        ned = ned.split(':')[1]

    result = DeviceInfo(
        name=device.name,
        address=device.address,
        platform_version=device.platform.version, 
        platform_name=device.platform.name,
        platform_model=device.platform.model,
        ned_type=ned_type,
        ned=ned
    )

    return result