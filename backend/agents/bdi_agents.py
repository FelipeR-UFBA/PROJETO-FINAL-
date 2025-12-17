
import os
import asyncio
import multiprocessing
import time
from typing import Optional
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour, PeriodicBehaviour
from spade.message import Message
from spade.template import Template
import flwr as fl
from backend.fl.client import IDSFlowerClient
from backend.fl.server import IDSServerStrategy, get_eval_fn
from slixmpp import ClientXMPP

original_connect = ClientXMPP.connect

def patched_connect(self, address=None, **kwargs):
    if address:
        host, port = address
        return original_connect(self, host=host, port=port, **kwargs)
    return original_connect(self, **kwargs)

ClientXMPP.connect = patched_connect
from backend.utils.logger import setup_logger

logger = setup_logger("MainProcess")

from backend.ml.data import NSL_KDD_DataProcessor

DATA_PATH = os.getenv("DATA_PATH", "/home/felipe/Desktop/anti/nsl-kdd")
processor = NSL_KDD_DataProcessor(DATA_PATH)
datasets = processor.get_datasets()

try:
    multiprocessing.set_start_method('spawn')
except RuntimeError:
    pass

def run_flower_client(cid, server_address):
    proc_logger = setup_logger(f"ClientProcess-{cid}", log_prefix=f"Client-{cid}")
    try:
        full_train_data = datasets["train"]
        X, y = full_train_data
        total_len = len(X)
        cid_int = int(cid)
        num_clients = 5
        part_size = total_len // num_clients
        start = (cid_int - 1) * part_size
        end = start + part_size
        
        if cid_int == num_clients:
            end = total_len

        my_data = (X[start:end], y[start:end])
        
        proc_logger.info(f"[{cid}] Training Data Partition: {len(my_data[0])} samples.")

        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        proc_logger.info(f"[{cid}] Using Device: {device}")
        
        client = IDSFlowerClient(cid=cid, train_data=my_data, test_data=datasets["test"], device=device)
        
        fl.client.start_client(
            server_address=server_address,
            client=client.to_client(),
        )
        proc_logger.info(f"[{cid}] FL Finished.")
    except Exception as e:
        import traceback
        proc_logger.error(f"[{cid}] CRITICAL CLIENT ERROR: {e}")
        proc_logger.error(traceback.format_exc())

class IDSClientAgent(Agent):
    def __init__(self, jid, password, cid: str, server_address: str = "127.0.0.1:8080"):
        super().__init__(jid, password)
        self.cid = cid
        self.server_address = server_address
        self.fl_client_process: Optional[multiprocessing.Process] = None
        self.is_training = False
        self.stop_event = multiprocessing.Event()

    async def setup(self):
        logger.info(f"Agent {self.cid} starting...")
        
        self.add_behaviour(self.CommandListener())
        
        self.add_behaviour(self.SecurityCheck(period=5))

    class SecurityCheck(PeriodicBehaviour):
        async def run(self):
            pass

    class CommandListener(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg:
                logger.info(f"[{self.agent.cid}] Received message: {msg.body}")
                if msg.body == "START_FL":
                    self.agent.start_fl()
                elif msg.body == "STOP_FL":
                    self.agent.stop_fl()

    def start_fl(self):
        logger.info(f"[{self.cid}] Starting Federated Learning Client...")
        
        if self.fl_client_process and self.fl_client_process.is_alive():
            logger.info(f"[{self.cid}] Restarting: Terminating stale FL process...")
            self.fl_client_process.terminate()
            self.fl_client_process.join(timeout=1)
        
        self.is_training = True
        self.stop_event.clear()
        
        self.fl_client_process = multiprocessing.Process(target=run_flower_client, args=(self.cid, self.server_address))
        self.fl_client_process.start()

    def stop_fl(self):
        logger.info(f"[{self.cid}] Stopping FL...")
        self.is_training = False
        self.stop_event.set()


def run_flower_server(port, algorithm="fedprox"):
    srv_logger = setup_logger("ServerProcess", log_prefix="Server")
    try:
        srv_logger.info(f"Flower Server process starting in PID: {os.getpid()}")
        import torch
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        srv_logger.info(f"[Server] Global Evaluation Device: {device}, Algorithm: {algorithm}")
        
        from backend.fl.server import get_fit_config_fn
        fit_config_fn = get_fit_config_fn(algorithm)
        
        eval_fn = get_eval_fn(datasets["test"], device=device, algorithm=algorithm)
        
        import glob
        import re
        from backend.ml.model import IDSModel
        from backend.fl.server import IDSFedProxStrategy, IDSServerStrategy
        
        initial_parameters = None
        ckpts = glob.glob(f"backend/checkpoints/{algorithm}/model_round_*.pth")
        
        if ckpts:
            latest_ckpt = max(ckpts, key=os.path.getctime)
            srv_logger.info(f"Found checkpoint: {latest_ckpt}")
            try:
                match = re.search(r"model_round_(\d+).pth", latest_ckpt)
                if match:
                    srv_logger.info(f"Resuming from Round {match.group(1)}...")

                model = IDSModel().to(device)
                model.load_state_dict(torch.load(latest_ckpt, map_location=device))
                weights = [val.cpu().numpy() for _, val in model.state_dict().items()]
                initial_parameters = fl.common.ndarrays_to_parameters(weights)
                srv_logger.info("Checkpoint loaded successfully.")
            except Exception as e:
                srv_logger.error(f"Failed to load checkpoint: {e}")
        
        if algorithm == "fedprox":
            strategy = IDSFedProxStrategy(
                eval_fn=eval_fn,
                fit_config_fn=fit_config_fn,
                initial_parameters=initial_parameters,
                proximal_mu=0.01,
                min_fit_clients=3,
                min_evaluate_clients=3,
                min_available_clients=3,
            )
        else:
            strategy = IDSServerStrategy(
                eval_fn=eval_fn,
                fit_config_fn=fit_config_fn,
                initial_parameters=initial_parameters,
                min_fit_clients=3,
                min_evaluate_clients=3,
                min_available_clients=3,
            )
            
        fl.server.start_server(
            server_address=f"0.0.0.0:{port}",
            config=fl.server.ServerConfig(num_rounds=50),
            strategy=strategy,
        )
        srv_logger.info("Flower Server stopped.")
        
        try:
            from backend.analytics.plotter import generate_graphs
            srv_logger.info("Generating post-training analytics...")
            generate_graphs("backend/plots")
        except Exception as e:
            srv_logger.error(f"Error generating graphs: {e}")
            
    except Exception as e:
        import traceback
        srv_logger.error(f"CRITICAL ERROR IN RUN_FLOWER_SERVER: {e}")
        srv_logger.error(traceback.format_exc())

class IDSServerAgent(Agent):
    def __init__(self, jid, password, port: int = 8080):
        super().__init__(jid, password)
        self.port = port
        self.fl_server_process: Optional[multiprocessing.Process] = None

    async def setup(self):
        logger.info("Server Agent starting...")
        self.add_behaviour(self.CommandListener())

    class CommandListener(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg:
                logger.info(f"[Server Agent] Received XMPP Message: {msg.body}")
                if msg.body == "START_SERVER":
                    self.agent.start_server()
                elif msg.body == "START_FL":
                    pass

    async def broadcast_command(self, jid_list, command):
        """
        Sends a command to a list of JIDs using a OneShotBehaviour for safety.
        """
        class Broadcaster(OneShotBehaviour):
            async def run(self):
                for jid_dest in jid_list:
                    msg = Message(to=str(jid_dest), body=command)
                    msg.set_metadata("performative", "request")
                    await self.send(msg)
                    logger.info(f"[Server Agent] Sent {command} to {jid_dest}")

        self.add_behaviour(Broadcaster())

    def start_server(self, algorithm="fedprox"):
        logger.info(f"Starting Flower Server with algorithm: {algorithm}...")
        
        if self.fl_server_process and self.fl_server_process.is_alive():
            logger.info("[Server Agent] Stopping previous server process object...")
            self.fl_server_process.terminate()
            self.fl_server_process.join(timeout=2)

        import subprocess
        try:
            subprocess.run(["fuser", "-k", "8080/tcp"], stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass 
            
        self.fl_server_process = multiprocessing.Process(target=run_flower_server, args=(self.port, algorithm))
        self.fl_server_process.start()

    async def stop(self):
        if self.fl_server_process and self.fl_server_process.is_alive():
            logger.info("[Server Agent] Stopping Flower Server process...")
            self.fl_server_process.terminate()
            self.fl_server_process.join()
        await super().stop()
