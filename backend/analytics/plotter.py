import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
import shutil
import numpy as np

def generate_graphs(base_output_dir: str):
    """Generates rigorous plots comparing FedAvg vs FedProx."""
    
    if os.path.exists(base_output_dir):
        shutil.rmtree(base_output_dir)
    os.makedirs(base_output_dir)
    
    dirs = {
        "fedavg": os.path.join(base_output_dir, "fedavg"),
        "fedprox": os.path.join(base_output_dir, "fedprox"),
        "comparison": os.path.join(base_output_dir, "comparison")
    }

    files = [
        ("metrics_fedavg.json", "FedAvg", "tab:red", "--"),
        ("metrics_fedprox.json", "FedProx", "tab:blue", "-")
    ]
    
    dfs = []
    for fname, label, color, style in files:
        if os.path.exists(fname):
            try:
                with open(fname, "r") as f:
                    data = json.load(f)
                if data:
                    df = pd.DataFrame(data)
                    df['Experiment'] = label
                    df['Color'] = color
                    df['Style'] = style
                    df['algo_key'] = "fedavg" if "FedAvg" in label else "fedprox"
                    dfs.append(df)
                else:
                     print(f"[Plotter] {fname} is empty.")
            except Exception as e:
                print(f"[Plotter] Error reading {fname}: {e}")
        else:
            print(f"[Plotter] {fname} not found.")

    if not dfs:
        print("[Plotter] No data found.")
        return

    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    metrics_to_plot = ['accuracy', 'loss', 'precision', 'recall', 'f1']
    
    for df in dfs:
        algo_key = df['algo_key'].iloc[0]
        algo_label = df['Experiment'].iloc[0]
        output_dir = dirs[algo_key]
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"[Plotter] Generating charts for {algo_label} in {output_dir}...")
        
        for metric in metrics_to_plot:
            if metric not in df.columns: continue
            
            plt.figure(figsize=(10, 6))
            sns.lineplot(data=df, x='round', y=metric, marker='o', linewidth=2.5, color=df['Color'].iloc[0])
            plt.title(f'{algo_label}: {metric.capitalize()} Progression')
            plt.xlabel('Round')
            plt.ylabel(metric.capitalize())
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{metric}.png"), dpi=300)
            plt.close()

        last_round_data = df.iloc[-1]
        cm = np.array(last_round_data.get("confusion_matrix", [[0,0],[0,0]]))
        if isinstance(cm, list): cm = np.array(cm)
             
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=['Normal', 'Attack'], 
                    yticklabels=['Normal', 'Attack'])
        plt.xlabel('Predicted Label')
        plt.ylabel('True Label')
        plt.title(f'{algo_label}: Confusion Matrix (Round {last_round_data["round"]})')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "confusion_matrix.png"), dpi=300)
        plt.close()

    if len(dfs) > 1:
        combined_df = pd.concat(dfs)
        comp_dir = dirs['comparison']
        os.makedirs(comp_dir, exist_ok=True)
        print(f"[Plotter] Generating comparison charts in {comp_dir}...")
    
        for metric in metrics_to_plot:
             if metric not in combined_df.columns: continue
             
             plt.figure(figsize=(12, 7))
             sns.lineplot(data=combined_df, x='round', y=metric, hue='Experiment', style='Experiment', markers=True, dashes=False, linewidth=2)
             plt.title(f'Comparative Analysis: {metric.capitalize()}')
             plt.xlabel('Round')
             plt.ylabel(metric.capitalize())
             plt.legend(title='Algorithm', bbox_to_anchor=(1.05, 1), loc='upper left')
             plt.grid(True, alpha=0.3)
             plt.tight_layout()
             plt.savefig(os.path.join(comp_dir, f"compare_{metric}.png"), dpi=300)
             plt.close()
    else:
        print("[Plotter] Skipping comparison graphs: Need data from both FedAvg and FedProx.")

    print("[Plotter] All graphs generated successfully.")

if __name__ == "__main__":
    generate_graphs("backend/plots")
