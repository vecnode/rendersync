#!/usr/bin/env python3
"""
rendersync Client - Get Public Endpoints
===============================================================================
Python script to connect to rendersync server and get public server information
Only accesses public endpoints that are controlled by connection_access_enabled
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


def get_health_status(server_ip: str = "127.0.0.1", port: int = 8080) -> Dict[str, Any]:
    """
    Get health status from rendersync server.
    
    Args:
        server_ip: IP address of the server
        port: Port number of the server
        
    Returns:
        Dictionary containing health status
        
    Raises:
        requests.RequestException: If connection fails
    """
    url = f"http://{server_ip}:{port}/health"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise requests.RequestException(f"Failed to connect to health endpoint: {str(e)}")


def get_process_status(server_ip: str = "127.0.0.1", port: int = 8080) -> Dict[str, Any]:
    """
    Get process status from rendersync server.
    
    Args:
        server_ip: IP address of the server
        port: Port number of the server
        
    Returns:
        Dictionary containing process status
        
    Raises:
        requests.RequestException: If connection fails
    """
    url = f"http://{server_ip}:{port}/api/process-status"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise requests.RequestException(f"Failed to connect to process status endpoint: {str(e)}")





def display_public_info(health_info: Dict[str, Any], process_info: Dict[str, Any]) -> None:
    """Display public server information in a formatted way."""
    print_colored("Public Server Information:", "yellow")
    print_colored("==========================", "yellow")
    
    # Health status
    print_colored(f"Health Status: {health_info.get('status', 'Unknown')}", "green")
    print_colored(f"Service: {health_info.get('service', 'Unknown')}", "green")
    
    # Process information
    if process_info:
        print()
        print_colored("Process Information:", "yellow")
        print_colored("===================", "yellow")
        for key, value in process_info.items():
            if isinstance(value, dict):
                print_colored(f"{key}:", "white")
                for sub_key, sub_value in value.items():
                    print_colored(f"  {sub_key}: {sub_value}", "white")
            else:
                print_colored(f"{key}: {value}", "white")
    


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Get rendersync public server information")
    parser.add_argument("server_ip", nargs="?", default="127.0.0.1", 
                       help="Server IP address (default: 127.0.0.1)")
    parser.add_argument("port", nargs="?", type=int, default=8080,
                       help="Server port (default: 8080)")
    
    args = parser.parse_args()
    
    print_info("rendersync Client - Public Server Info")
    print_info("======================================")
    print_info(f"Connecting to: http://{args.server_ip}:{args.port}")
    print_info("Accessing only PUBLIC endpoints (controlled by connection_access_enabled)")
    
    try:
        # Get health status (always accessible)
        print_info("Getting health status")
        health_info = get_health_status(args.server_ip, args.port)
        
        # Try to get process status (public endpoint)
        process_info = None
        try:
            print_info("Getting process status")
            process_info = get_process_status(args.server_ip, args.port)
        except requests.RequestException as e:
            print_warning(f"Process status not accessible: {str(e)}")
            print_warning("This may indicate external connections are disabled")
        
        print_success("Connection successful")
        print()
        
        display_public_info(health_info, process_info)
        
        print()
        print_success("Public server info retrieved successfully")
        
        # Show connection status based on what we could access
        if process_info:
            print_colored("External connections: ENABLED", "green")
        else:
            print_colored("External connections: DISABLED (only health check accessible)", "yellow")
        
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
