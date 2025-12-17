
from collections import OrderedDict
from typing import List, Tuple, Dict
import flwr as fl
import torch
import numpy as np
from backend.ml.model import IDSModel, train, test
from backend.ml.data import get_dataloader

class IDSFlowerClient(fl.client.NumPyClient):
    def __init__(self, cid: str, train_data, test_data, device="cpu"):
        self.cid = cid
        self.model = IDSModel()
        self.device = device
        self.train_loader = get_dataloader(train_data, batch_size=32, shuffle=True)
        self.test_loader = get_dataloader(test_data, batch_size=32, shuffle=False)
        self.local_epochs = 3

    def get_parameters(self, config) -> List[np.ndarray]:
        return [val.cpu().numpy() for _, val in self.model.state_dict().items()]

    def set_parameters(self, parameters: List[np.ndarray]):
        params_dict = zip(self.model.state_dict().keys(), parameters)
        state_dict = OrderedDict({k: torch.tensor(v) for k, v in params_dict})
        self.model.load_state_dict(state_dict, strict=True)

    def fit(self, parameters, config) -> Tuple[List[np.ndarray], int, Dict]:
        print(f"[Client {self.cid}] Starting Fit...", flush=True)
        self.set_parameters(parameters)
        
        import copy
        global_model = copy.deepcopy(self.model)
        
        server_round = int(config.get("server_round", 1))
        lr = 0.001 * (0.9 ** ((server_round - 1) // 10))
        
        mu = float(config.get("mu", 0.01))
        
        print(f"[Client {self.cid}] Round {server_round}: LR={lr:.6f}, Mu={mu}", flush=True)

        metrics = train(self.model, self.train_loader, epochs=self.local_epochs, lr=lr, device=self.device, global_model=global_model, mu=mu)
        print(f"[Client {self.cid}] Training finished. Loss: {metrics['loss']:.4f}, Accuracy: {metrics['accuracy']:.4f}", flush=True)
        
        return self.get_parameters(config={}), len(self.train_loader.dataset), {"loss": metrics["loss"], "accuracy": metrics["accuracy"]}

    def evaluate(self, parameters, config) -> Tuple[float, int, Dict]:
        print(f"[Client {self.cid}] Starting Evaluate...", flush=True)
        self.set_parameters(parameters)
        
        metrics = test(self.model, self.test_loader, device=self.device)
        print(f"[Client {self.cid}] Evaluation. Loss: {metrics['loss']:.4f}, Accuracy: {metrics['accuracy']:.4f}", flush=True)
        
        return float(metrics["loss"]), len(self.test_loader.dataset), {"accuracy": float(metrics["accuracy"])}

import numpy as np
