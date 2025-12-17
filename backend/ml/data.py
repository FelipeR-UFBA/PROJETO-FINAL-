import pandas as pd
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
import torch
import numpy as np
import random

from typing import Tuple, List, Dict

def set_seed(seed: int = 42):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.backends.cudnn.deterministic = True
    print(f"[System] Global Seed set to {seed}")
set_seed(42)

COLUMNS = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot", "num_failed_logins",
    "logged_in", "num_compromised", "root_shell", "su_attempted", "num_root",
    "num_file_creations", "num_shells", "num_access_files", "num_outbound_cmds",
    "is_host_login", "is_guest_login", "count", "srv_count", "serror_rate",
    "srv_serror_rate", "rerror_rate", "srv_rerror_rate", "same_srv_rate",
    "diff_srv_rate", "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate", "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate", "class", "difficulty"
]

CATEGORICAL_COLS = ["protocol_type", "service", "flag"]

class NSL_KDD_DataProcessor:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.encoders: Dict[str, LabelEncoder] = {}
        self.scaler = MinMaxScaler()
        
    def load_raw_data(self, dataset_type: str = "train") -> pd.DataFrame:
        """Loads raw data from txt files."""
        filename = "KDDTrain+.txt" if dataset_type == "train" else "KDDTest+.txt"
        path = f"{self.data_path}/{filename}"
        
        df = pd.read_csv(path, names=COLUMNS)
        return df

    def preprocess(self, df: pd.DataFrame, fit_scalers: bool = False) -> Tuple[pd.DataFrame, pd.Series]:
        """Preprocesses the dataframe: Encoding and Scaling."""
        
        if "difficulty" in df.columns:
            df = df.drop("difficulty", axis=1)
            
        X = df.drop("class", axis=1)
        y = df["class"]
        
        y_binary = y.apply(lambda x: 0 if x == "normal" else 1)
        
        for col in CATEGORICAL_COLS:
            if fit_scalers:
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col])
                self.encoders[col] = le
            else:
                if col in self.encoders:
                    le = self.encoders[col]
                    mapping = dict(zip(le.classes_, range(len(le.classes_))))
                    X[col] = X[col].map(mapping).fillna(-1) 
                
        numerical_cols = [c for c in X.columns if c not in CATEGORICAL_COLS] 
        
        if fit_scalers:
            self.scaler.fit(X)
            
        X_scaled = pd.DataFrame(self.scaler.transform(X), columns=X.columns)
        
        return X_scaled, y_binary

    def get_datasets(self) -> Dict[str, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Returns processed PyTorch tensors for:
        1. Train (KDDTrain+) - To be distributed among clients
        2. Test (KDDTest+) - For server evaluation (and client eval if desired)
        """
        train_raw = self.load_raw_data("train")
        test_raw = self.load_raw_data("test")
        
        X_train, y_train = self.preprocess(train_raw, fit_scalers=True)
        
        X_test, y_test = self.preprocess(test_raw, fit_scalers=False)
        
        train_dataset = (
            torch.tensor(X_train.values, dtype=torch.float32),
            torch.tensor(y_train.values, dtype=torch.long)
        )
        
        test_dataset = (
            torch.tensor(X_test.values, dtype=torch.float32),
            torch.tensor(y_test.values, dtype=torch.long)
        )
        
        return {
            "train": train_dataset,
            "test": test_dataset
        }

def get_dataloader(data: Tuple[torch.Tensor, torch.Tensor], batch_size: int = 32, shuffle: bool = True):
    dataset = TensorDataset(data[0], data[1])
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)
