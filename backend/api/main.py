import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
import os
import uvicorn
from contextlib import asynccontextmanager
import json
import aiofiles
import multiprocessing
import shutil
from datetime import datetime

try:
    multiprocessing.set_start_method('spawn')
except RuntimeError:
    pass 

from backend.agents.bdi_agents import IDSClientAgent, IDSServerAgent
from backend.utils.logger import setup_logger, LOG_FILE

logger = setup_logger("API")

class AgentManager:
    def __init__(self):
        self.server_agent: IDSServerAgent = None
        self.clients: List[IDSClientAgent] = []
        self.xmpp_host = os.getenv("XMPP_HOST", "localhost")
        self.xmpp_pass = os.getenv("XMPP_PASS", "password") 

    async def start_server_agent(self):
        jid = f"server@{self.xmpp_host}"
        self.server_agent = IDSServerAgent(jid, self.xmpp_pass)
        await self.server_agent.start(auto_register=False)
        print(f"Server Agent {jid} started")

    async def add_client(self):
        cid = str(len(self.clients) + 1)
        jid = f"client{cid}@{self.xmpp_host}"
        client = IDSClientAgent(jid, self.xmpp_pass, cid=cid)
        await client.start(auto_register=False)
        self.clients.append(client)
        print(f"Client Agent {jid} started")
        return cid

    async def stop_all(self):
        for agent in self.clients:
            await agent.stop()
        if self.server_agent:
            await self.server_agent.stop()
        self.clients = []
        self.server_agent = None

        self.clients = []
        self.server_agent = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

ws_manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("System Starting...")
    global manager
    manager = AgentManager()
    
    yield
    print("System Shutting down...")
    await manager.stop_all()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class StatusResponse(BaseModel):
    status: str
    active_agents: int

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    return {
        "status": "running",
        "active_agents": len(manager.clients)
    }

@app.post("/api/start_infrastructure")
async def start_infrastructure():
    if not manager.server_agent:
        await manager.start_server_agent()
    return {"message": "Infrastructure Started"}

@app.post("/api/add_agent")
async def add_agent():
    cid = await manager.add_client()
    return {"message": f"Agent {cid} Added", "cid": cid}

    return {"message": f"Agent {cid} Added", "cid": cid}

CURRENT_ALGORITHM = "fedprox"

class AlgorithmUpdate(BaseModel):
    algorithm: str

@app.get("/api/get_algorithm")
async def get_algorithm():
    return {"algorithm": CURRENT_ALGORITHM}

@app.post("/api/set_algorithm")
async def set_algorithm(update: AlgorithmUpdate):
    global CURRENT_ALGORITHM
    if update.algorithm not in ["fedavg", "fedprox"]:
        return {"error": "Invalid algorithm"}
        
    if CURRENT_ALGORITHM != update.algorithm:
        print(f"[API] Switching Algorithm to {update.algorithm}")
        CURRENT_ALGORITHM = update.algorithm
        
        if manager.server_agent:
            print("[API] Restarting Server with new algorithm...")
            manager.server_agent.start_server(algorithm=CURRENT_ALGORITHM)
            
    return {"message": f"Algorithm set to {CURRENT_ALGORITHM}", "algorithm": CURRENT_ALGORITHM}

@app.post("/api/start_federation")
async def start_federation():
    if manager.server_agent:
        manager.server_agent.start_server(algorithm=CURRENT_ALGORITHM) 
        
    await asyncio.sleep(5)
        
    client_jids = [str(c.jid) for c in manager.clients]
    if manager.server_agent and client_jids:
        await manager.server_agent.broadcast_command(client_jids, "START_FL")

@app.post("/api/reset_system")
async def reset_system():
    print("[API] Initiating System Reset & Archival...")
    
    if manager:
        await manager.stop_all()
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = f"experiment_backups/{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    print(f"[Reset] Created backup archive at {backup_dir}")
    
    if os.path.exists("backend/checkpoints"):
        try:
            shutil.move("backend/checkpoints", f"{backup_dir}/checkpoints")
            print("[Reset] Checkpoints archived.")
        except Exception as e:
            print(f"[Reset] Error archiving checkpoints: {e}")
            
    if os.path.exists("backend/plots"):
        try:
            shutil.move("backend/plots", f"{backup_dir}/plots")
            print("[Reset] Plots archived.")
        except Exception as e:
            print(f"[Reset] Error archiving plots: {e}")

    for algo in ["fedavg", "fedprox"]:
        fname = f"metrics_{algo}.json"
        if os.path.exists(fname):
            try:
                shutil.move(fname, f"{backup_dir}/{fname}")
                print(f"[Reset] {fname} archived.")
            except Exception as e:
                print(f"[Reset] Error archiving {fname}: {e}")

    return {"message": f"System Reset Complete. Previous experiment data archived to: {backup_dir}"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    last_mtime_metrics = 0

    f_log = None
    if os.path.exists(LOG_FILE):
        f_log = open(LOG_FILE, 'r')
        f_log.seek(0, os.SEEK_END)
    
    try:
        while True:
            METRICS_FILE = f"metrics_{CURRENT_ALGORITHM}.json"
            if os.path.exists(METRICS_FILE):
                mtime = os.path.getmtime(METRICS_FILE)
                if mtime > last_mtime_metrics:
                    last_mtime_metrics = mtime
                    try:
                        async with aiofiles.open(METRICS_FILE, "r") as f:
                            content = await f.read()
                            data = json.loads(content)
                            payload = json.dumps({"type": "metrics_update", "data": data})
                            await websocket.send_text(payload)
                    except Exception as e:
                        print(f"Error reading metrics: {e}")

            if f_log:
                line = f_log.readline()
                while line:
                    try:
                        payload = json.dumps({"type": "log", "data": line.strip()})
                        await websocket.send_text(payload)
                    except WebSocketDisconnect:
                        raise 
                    line = f_log.readline()
            elif os.path.exists(LOG_FILE):
                 f_log = open(LOG_FILE, 'r')
            
            if websocket.client_state.value == 3: 
                    break

            await asyncio.sleep(0.5) 
            
    except WebSocketDisconnect:
        print("WebSocket disconnected normally.")
    except Exception as e:
        print(f"WS Error: {e}")
    finally:
        if f_log:
            f_log.close()
        ws_manager.disconnect(websocket)

os.makedirs("backend/plots", exist_ok=True)
app.mount("/plots", StaticFiles(directory="backend/plots"), name="plots")

@app.get("/api/analytics/status")
async def get_analytics_status():
    status = {
        "fedavg": os.path.exists("metrics_fedavg.json"),
        "fedprox": os.path.exists("metrics_fedprox.json"),
        "comparison": os.path.exists("metrics_fedavg.json") and os.path.exists("metrics_fedprox.json")
    }
    return status

@app.post("/api/generate_plots")
async def trigger_plots():
    from backend.analytics.plotter import generate_graphs
    try:
        generate_graphs("backend/plots")
        return {"message": "Graphs generated successfully."}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
