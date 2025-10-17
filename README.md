# rendersync

This repository contains `rendersync` an open platform to schedule renders used in studios, warehouses and renderfarms. Currently controls platforms: 1) ComfyUI, 2) Ollama. It can be used as a modular and adaptive edge/process orchestrator and inspector, submit AI render workflows fast.   

Running the system and developing:  
- Windows 11 Laptop, NVIDIA GeForce RTX 4050 6Gb. 
- Windows 11 Desktop, NVIDIA Geforce RTX 3090 24Gb. 

The purpose of this project is to provide an adaptive piece of software that runs in Windows/Linux terminals and is accessible through the browser; it has its own dedicated server, the Core, and several Modules plug in.


### Dependencies:  
```
Python 3.10+ (e.g. version 3.13.7)   
git (e.g. version 2.51.0.windows.1)   
```

### Libraries:  
```
# Python
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
httpx>=0.27.0
pydantic>=2.7.0
psutil>=5.9.8
python-multipart
# JavaScript
bootstrap==5.3.8
```

### Module Libraries: 
```
Ollama (e.g. version 0.11.8)   
ComfyUI (e.g. version 0.3.64)  
```

### Features completed

`rendersync`
- Server (core)
    - Python FastAPI server: streaming, requests, jobs and chats
    - Server reads the modules and submodules
    - Custom vanilla JavaScript frontend
- Build
    - Automated build designed for PowerShell `run.ps1`  
    - Check if `venv` exists, create if missing
    - Start server, open browser, clean up on exit
    - Independent terminals for submodules
- Modules
    - Host OS inspector, terminals, PID, IPs, network utilities  
    - Modules: `comfyui.py`, `network.py`,  `ollama.py`, `system.py`, `utilities.py`
- Submodules
    - Ollama: Inspect, Start/Stop, chat with models  
    - ComfyUI: Inspect, Start/Stop, submit example workflow


#### Reproduce Windows 11

```
# cd to .\rendersync\
.\run.ps1
_____________________________
# ollama utils
ollama pull llama3.2:3b 
ollama pull gemma3:1b
ollama list  
```


#### In development

- Test calling renders from secondary `rendersync` to a machine with 24Gb and call SD1.5    
- Add a global open/close of endpoints.   
- Add timings to execute on clock and checking if process if on first - safe.    
- Add trainer file as module - fine-tuning stack to see.    
- Get the progress bar from the models generating on comfy terminal to the browser.   
- Check more Host OSs, multiple machines.   
- Available Models in every system that we have to download and everything. in one line with the combo.  Comfy too   
- Fast way to search for model types such as `.pt` and `.safetensors` or `.gguf`   
- Inspect Torch processes on the network and tensor computation.   
- Call jobs through SSH.      
- Download models in the interface, find a way to download ollama models (default, or input the name so it know how to search the official channels) - ollama specific, on a combo with a download button (ollama command and remove too).   
- Maybe add Bootstrap to the frontend: https://getbootstrap.com/   
- Ollama scheduling so we can make questions at specific times of day and weeks in a row.     
- Refactor the codebase to act only on one Disk `C:/` at the time and we can change according to what we can see at the top.     
- Make this server receive json calls that are sent to the comfyui as well and ollama, maybe a structured rendersync JSON file that is read through the server, the ability to have specific jobs called through rendersync - such as image-to-image.   
- A comparison module with some metrics.
- Call ollama on a different machine same network. 
- Maybe consider multiple rendersyncs for multiple users constantly on.  
- After starting a submodule check again it really started process and lock the button to start.   
- Link to the new guidelines repository will be linked here for guardrails.
- Make a test suite for the core and each module/submodule. 


### License
MIT

