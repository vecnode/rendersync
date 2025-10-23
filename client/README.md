Folder for network connections to rendersync

```
python .\get_server_info.py 127.0.0.1 8080
==> rendersync Client - Server Info
==> ===============================
==> Connecting to: http://127.0.0.1:8080/api/server-info
==> Connection successful!

Server Information:
==================
Status: running
Service: rendersync
Hostname: DESKTOP-XXXXXXX
Local IP: xxx.xxx.x.x
Connection Status: enabled
Network Accessible: True
CORS Enabled: True

Port Information:
================
preferred_ports: [8080, 8000, 8081, 8082, 3000, 5000, 9000, 8888, 8001, 8083, 7000]
default_port: 8080
port_usage: {'8080': {'available': True, 'processes': [{'pid': XXXXX, 'name': 'python.exe'}, {'pid': XXXXX, 'name': 'python.exe'}]}, '8000': {'available': True, 'processes': []}, '8081': {'available': True, 'processes': []}, '8082': {'available': True, 'processes': []}, '3000': {'available': True, 'processes': []}}

==> Server info retrieved successfully!
```
