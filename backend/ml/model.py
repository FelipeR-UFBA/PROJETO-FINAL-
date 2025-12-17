
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from typing import Tuple, Dict

class IDSModel(nn.Module):
    def __init__(self, input_dim: int = 41, output_dim: int = 2):
        super(IDSModel, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=1, out_channels=64, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(64)
        self.relu = nn.ReLU()
        self.dropout1 = nn.Dropout(0.2)
        
        self.conv2 = nn.Conv1d(in_channels=64, out_channels=128, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(128)
        self.dropout2 = nn.Dropout(0.3)
        
        self.fc1 = nn.Linear(128 * input_dim, 256) 
        self.dropout3 = nn.Dropout(0.4)
        self.fc2 = nn.Linear(256, output_dim)

    def forward(self, x):
        x = x.unsqueeze(1)
        
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.dropout1(x)
        
        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        x = self.dropout2(x)
        
        x = x.view(x.size(0), -1)
        
        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout3(x)
        x = self.fc2(x)
        
        return x

def train(model: nn.Module, train_loader: DataLoader, epochs: int = 1, lr: float = 0.001, device: str = "cpu", global_model: nn.Module = None, mu: float = 0.0) -> Dict[str, float]:
    """Train the model for a number of epochs."""
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    model.train()
    model.to(device)
    
    if global_model:
        global_model.to(device)
        global_model.eval()

    total_loss = 0.0
    correct = 0
    total = 0

    for epoch in range(epochs):
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(device), target.to(device)
            
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            
            if mu > 0.0 and global_model is not None:
                proximal_term = 0.0
                for w, w_t in zip(model.parameters(), global_model.parameters()):
                    proximal_term += (w - w_t).norm(2) ** 2
                loss += (mu / 2) * proximal_term
            
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item() * data.size(0)
            _, predicted = torch.max(output.data, 1)
            total += target.size(0)
            correct += (predicted == target).sum().item()
            
            if batch_idx % 50 == 0:
                print(f"Batch {batch_idx}/{len(train_loader)} Loss: {loss.item():.4f}", flush=True)

    avg_loss = total_loss / total
    accuracy = correct / total
    return {"loss": avg_loss, "accuracy": accuracy}

def test(model: nn.Module, test_loader: DataLoader, device: str = "cpu") -> Dict[str, float]:
    """Evaluate the model."""
    criterion = nn.CrossEntropyLoss()
    model.eval()
    model.to(device)
    
    print(f"DEBUG_MODEL: Starting evaluation on device {device}")
    total_loss = 0.0
    correct = 0
    total = 0
    
    all_preds = []
    all_targets = []
    
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            loss = criterion(output, target)
            
            total_loss += loss.item() * data.size(0)
            _, predicted = torch.max(output.data, 1)
            total += target.size(0)
            correct += (predicted == target).sum().item()
            
            all_preds.extend(predicted.cpu().numpy())
            all_targets.extend(target.cpu().numpy())
            
    avg_loss = total_loss / total
    accuracy = correct / total
    
    from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix

    precision = precision_score(all_targets, all_preds, average='macro', zero_division=0)
    recall = recall_score(all_targets, all_preds, average='macro', zero_division=0)
    f1 = f1_score(all_targets, all_preds, average='macro', zero_division=0)
    conf_matrix = confusion_matrix(all_targets, all_preds).tolist() 
    
    return {
        "loss": avg_loss, 
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": conf_matrix
    }
