## Simple NSO MCP Server 

A Network Service Orchestrator (NSO) MCP (Model Context Protocol) server using NSO unauthenticated IPC socket (port 4569) to fetching NSO's CDB information and running actions.
NSO RESTAPI is not used by the MCP server

## Prerequisites

- Python 3.11+
- FastMCP

## MCP Server variables

Following variables can be define in the .env file (and the respective default values used):

- NSO_USER='nsoadmin'
- NSO_CONTEXT='system'
- API_PORT=8000
- LOG_DIRECTORY='/var/log/ncs'
- NCS_ADDRESS=127.0.0.1

## Running MCP server:

### 1. Start the MCP Server

- uv sync
- uv run main.py

### 2. Start the MCP Server

- adapt the systemctl script to your needs

## Tools list

Use MCP inspector to troubleshoot tool usage: npx @modelcontextprotocol/inspector

- get_neds_list - get NSO NEDs list
- get_devices_name_list - get NSO device list
- get_devices_groups_list - get NSO device-group list
- get_device_info - get NSO device information
- check_sync_devices_status - check NSO device sync status
- sync_device - run action to sync NSO device
- sync_device_group - run action to sync NSO device-group
- get_devices_from_device_group - get device list from NSO device-group
- get_devices_list_per_model - get NSO device list for a specific model
- get_devices_list_per_model_and_version - get NSO device list for a specific model and version
- get_devices_list_per_model_dont_match_version - get NSO device list for a specific model that does not match a specific version
- get_day1_services - get all NSO day1 services
- get_all_services - get the list of all NSO services
- get_device_configured_services - get all services configured against an NSO device
- check_service_sync_status - check NSO service status


## Logs

Check the application logs for detailed error information in /var/log/ncs/ncs-python-mcp-server.log

