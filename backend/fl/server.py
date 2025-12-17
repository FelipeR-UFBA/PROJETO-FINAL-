
from typing import List, Tuple, Dict, Optional
import flwr as fl
from flwr.common import Metrics
import torch
import numpy as np
from collections import OrderedDict
from torch.utils.data import DataLoader, TensorDataset
import os
import json
from backend.ml.model import IDSModel, test
from backend.ml.data import get_dataloader

def set_weights(model: torch.nn.Module, parameters: List[np.ndarray]):
    params_dict = zip(model.state_dict().keys(), parameters)
    state_dict = OrderedDict({k: torch.tensor(v) for k, v in params_dict})
    model.load_state_dict(state_dict, strict=True)

def get_eval_fn(test_data, device="cpu", algorithm="fedavg"):
    """Return an evaluation function for server-side evaluation."""
    
    test_loader = get_dataloader(test_data, batch_size=64, shuffle=False)

    X_test, y_test = test_data
    X_test_tensor = torch.tensor(X_test, dtype=torch.float32)
    y_test_tensor = torch.tensor(y_test, dtype=torch.long)
    
    val_loader = DataLoader(TensorDataset(X_test_tensor, y_test_tensor), batch_size=32)
    
    METRICS_FILE = f"metrics_{algorithm}.json"
    CHECKPOINT_DIR = f"backend/checkpoints/{algorithm}"
    
    if not os.path.exists(CHECKPOINT_DIR):
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    def evaluate(server_round: int, parameters: fl.common.NDArrays, config: Dict[str, fl.common.Scalar]) -> Optional[Tuple[float, Dict[str, fl.common.Scalar]]]:
        model = IDSModel()
        model.to(device)
        set_weights(model, parameters)
        
        print(f"DEBUG: Starting test() for round {server_round}")
        try:
            metrics = test(model, val_loader, device=device)
            print(f"DEBUG: test() returned. Metrics: {metrics.keys()}")
            print(f"[Server Round {server_round}] Global Eval - Loss: {metrics['loss']:.4f}, Accuracy: {metrics['accuracy']:.4f}")
        except Exception as e:
            print(f"CRITICAL ERROR IN EVALUATE: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        print("DEBUG: Saving metrics to json")
        
        metric_data = {
            "round": server_round,
            "loss": metrics["loss"],
            "accuracy": metrics["accuracy"],
            "precision": metrics.get("precision", 0),
            "recall": metrics.get("recall", 0),
            "f1": metrics.get("f1", 0),
            "confusion_matrix": metrics.get("confusion_matrix", [])
        }
        
        existing_data = []
        
        if os.path.exists(METRICS_FILE):
            
            if server_round == 0:
                print(f"DEBUG: Round 0 detected. overwriting {METRICS_FILE} for fresh experiment.")
                existing_data = [] 
            else:
                try:
                    with open(METRICS_FILE, "r") as f:
                        existing_data = json.load(f)
                        
                        existing_data = [d for d in existing_data if d["round"] < server_round]
                        
                except Exception as e:
                    print(f"ERROR reading metrics file {METRICS_FILE}: {e}")
                    existing_data = []
        
        existing_data.append(metric_data)
        
        with open(METRICS_FILE, "w") as f:
            json.dump(existing_data, f, indent=4) 
            
        try:
            ckpt_path = f"{CHECKPOINT_DIR}/model_round_{server_round}.pth"
            torch.save(model.state_dict(), ckpt_path)
            print(f"DEBUG: Saved checkpoint to {ckpt_path}")
        except Exception as e:
            print(f"ERROR Saving Checkpoint: {e}")
            
        return metrics["loss"], {"accuracy": metrics["accuracy"]}

    return evaluate

def weighted_average(metrics: List[Tuple[int, Metrics]]) -> Metrics:
    accuracies = [num_examples * m["accuracy"] for num_examples, m in metrics]
    examples = [num_examples for num_examples, _ in metrics]

    return {"accuracy": sum(accuracies) / sum(examples)}

def get_fit_config_fn(algorithm: str = "fedavg"):
    def fit_config(server_round: int):
        """Return training configuration dict for each round."""
        config = {
            "server_round": server_round,
        }
        if algorithm == "fedprox":
            config["mu"] = 0.01 
        return config
    return fit_config

class IDSServerStrategy(fl.server.strategy.FedAvg):
    def __init__(self, eval_fn, fit_config_fn, *args, **kwargs):
        super().__init__(
            *args, 
            evaluate_fn=eval_fn, 
            evaluate_metrics_aggregation_fn=weighted_average, 
            on_fit_config_fn=fit_config_fn,
            **kwargs
        )

class IDSFedProxStrategy(fl.server.strategy.FedProx):
    def __init__(self, eval_fn, fit_config_fn, proximal_mu, *args, **kwargs):
        super().__init__(
            *args, 
            evaluate_fn=eval_fn, 
            evaluate_metrics_aggregation_fn=weighted_average, 
            on_fit_config_fn=fit_config_fn,
            proximal_mu=proximal_mu,
            **kwargs
        )

def run_flower_server(algorithm: str = "fedavg"):
    print(f"Starting Flower Server with Algorithm: {algorithm}")
    
    eval_fn = get_eval_fn()
    fit_config_fn = get_fit_config_fn(algorithm)
    
    if algorithm == "fedprox":
        strategy = IDSFedProxStrategy(
            eval_fn=eval_fn,
            fit_config_fn=fit_config_fn,
            proximal_mu=0.01, 
            min_fit_clients=3,
            min_evaluate_clients=3,
            min_available_clients=3,
        )
    else:
        strategy = IDSServerStrategy(
            eval_fn=eval_fn,
            fit_config_fn=fit_config_fn,
            min_fit_clients=3,
            min_evaluate_clients=3,
            min_available_clients=3,
        )
    fl.server.start_server(
        server_address="0.0.0.0:8080",
        config=fl.server.ServerConfig(num_rounds=50),
        strategy=strategy,
    )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Flower Server')
    parser.add_argument('--algorithm', type=str, default='fedavg', help='Algorithm to use (fedavg/fedprox)')
    args = parser.parse_args()
    
    run_flower_server(args.algorithm)

