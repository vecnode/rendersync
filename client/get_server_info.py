#!/usr/bin/env python3
"""
rendersync Client - Get Server Info
===============================================================================
Python script to connect to rendersync server and get server information
Usage: python get_server_info.py [server_ip] [port]
===============================================================================
"""

import sys
import json
import requests
import argparse
from typing import Dict, Any


def print_colored(text: str, color: str = "white") -> None:
    """Print colored text to terminal."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "bold": "\033[1m",
        "end": "\033[0m"
    }
    
    color_code = colors.get(color, colors["white"])
    print(f"{color_code}{text}{colors['end']}")


def print_info(text: str) -> None:
    """Print info message."""
    print_colored(f"==> {text}", "cyan")


def print_success(text: str) -> None:
    """Print success message."""
    print_colored(f"==> {text}", "green")


def print_warning(text: str) -> None:
    """Print warning message."""
    print_colored(f"==> {text}", "yellow")


def print_error(text: str) -> None:
    """Print error message."""
    print_colored(f"==> {text}", "red")


def get_server_info(server_ip: str = "127.0.0.1", port: int = 8080) -> Dict[str, Any]:
    """
    Connect to rendersync server and get server information.
    
    Args:
        server_ip: IP address of the server
        port: Port number of the server
        
    Returns:
        Dictionary containing server information
        
    Raises:
        requests.RequestException: If connection fails
    """
    url = f"http://{server_ip}:{port}/api/server-info"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise requests.RequestException(f"Failed to connect to server: {str(e)}")


def display_server_info(server_info: Dict[str, Any]) -> None:
    """Display server information in a formatted way."""
    print_colored("Server Information:", "yellow")
    print_colored("==================", "yellow")
    
    # Basic server info
    print_colored(f"Status: {server_info.get('status', 'Unknown')}", "green")
    print_colored(f"Service: {server_info.get('service', 'Unknown')}", "green")
    print_colored(f"Hostname: {server_info.get('hostname', 'Unknown')}", "white")
    print_colored(f"Local IP: {server_info.get('local_ip', 'Unknown')}", "white")
    
    # Connection status with color coding
    connection_status = server_info.get('connection_status', 'Unknown')
    status_color = "green" if connection_status == "enabled" else "red"
    print_colored(f"Connection Status: {connection_status}", status_color)
    
    # Network accessibility with color coding
    network_accessible = server_info.get('accessible_from_network', False)
    network_color = "green" if network_accessible else "red"
    print_colored(f"Network Accessible: {network_accessible}", network_color)
    
    # CORS status with color coding
    cors_enabled = server_info.get('cors_enabled', False)
    cors_color = "green" if cors_enabled else "red"
    print_colored(f"CORS Enabled: {cors_enabled}", cors_color)
    
    # Port information if available
    port_info = server_info.get('port_info')
    if port_info:
        print()
        print_colored("Port Information:", "yellow")
        print_colored("================", "yellow")
        for key, value in port_info.items():
            print_colored(f"{key}: {value}", "white")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Get rendersync server information")
    parser.add_argument("server_ip", nargs="?", default="127.0.0.1", 
                       help="Server IP address (default: 127.0.0.1)")
    parser.add_argument("port", nargs="?", type=int, default=8080,
                       help="Server port (default: 8080)")
    
    args = parser.parse_args()
    
    print_info("rendersync Client - Server Info")
    print_info("===============================")
    print_info(f"Connecting to: http://{args.server_ip}:{args.port}/api/server-info")
    
    try:
        server_info = get_server_info(args.server_ip, args.port)
        print_success("Connection successful!")
        print()
        
        display_server_info(server_info)
        
        print()
        print_success("Server info retrieved successfully!")
        
    except requests.RequestException as e:
        print_error(str(e))
        print_warning(f"Make sure the rendersync server is running and accessible at http://{args.server_ip}:{args.port}")
        print_warning("You can also try different IP addresses if connecting from another machine on the network")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
