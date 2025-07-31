import glob
import pandas as pd
from matplotlib import pyplot as plt

# ─────────────────────────────────────────────────────────────────────────────
# Experiment ID lists
# ─────────────────────────────────────────────────────────────────────────────
experiment_ids_1node = [
    'weak_1748957888:2:1:32,32,32',
    'weak_1748957943:2:2:32,32,32',
    'weak_1748958086:2:4:32,32,32',
    'weak_1748958125:2:8:32,32,32'
]

experiment_ids_2nodes = [
    'weak_1749121289:3:2:32,32,32',
    'weak_1749121304:3:4:32,32,32',
    'weak_1749121315:3:8:32,32,32',
    # 'weak_1749121339:3:16:32,32,32'
]

# ─────────────────────────────────────────────────────────────────────────────
# Function to process experiments and return DataFrames + plots
# ─────────────────────────────────────────────────────────────────────────────
def process_weak_scaling(experiment_ids, label):
    experiment_dirs = []
    for _dir in experiment_ids:
        experiment_dirs.extend(glob.glob(f"../experiment_result/*{_dir}*"))
    print(f"[{label}] Found experiment directories: {experiment_dirs}")

    df = pd.DataFrame(columns=["name", "exec_id", "total_nodes", "mpi_processes", "problem_size",  
                               "x_dim", "y_dim", "z_dim", 
                               "time_ekin", "time_sum", "time_f",
                               "analytics_start", "analytics_end",
                               "simulation_start", "simulation_end"])

    monitor_df = pd.DataFrame()

    for d in experiment_dirs:
        exec_id = d.split("/")[-1]
        parts = exec_id.split(":")
        name = parts[0]
        total_nodes = int(parts[1])
        mpi_processes = int(parts[2])
        problem_size = parts[3]

        res_file = f"{d}/analytics.e"
        with open(res_file, "r") as f:
            data = [line.strip() for line in f if line.strip()]

        x_dim = int([lin for lin in data if lin.startswith("[Analytics] X-dim")][0].split("=")[-1].strip())
        y_dim = int([lin for lin in data if lin.startswith("[Analytics] Y-dim")][0].split("=")[-1].strip())
        z_dim = int([lin for lin in data if lin.startswith("[Analytics] Z-dim")][0].split("=")[-1].strip())

        time_ekin = float([lin for lin in data if lin.startswith("[Analytics] time ekin")][0].split(":")[-1].strip())
        time_sum = float([lin for lin in data if lin.startswith("[Analytics] time sum over xy:")][0].split(":")[-1].strip())
        time_f = float([lin for lin in data if lin.startswith("[Analytics] time fourier:")][0].split(":")[-1].strip())

        with open(f"{d}/analytics_process_stats.txt", "r") as f:
            analytics_process = eval(f.read())
        with open(f"{d}/mpi_process_stats.txt", "r") as f:
            simulation_process = eval(f.read())

        df.loc[len(df)] = [
            name, exec_id, total_nodes, mpi_processes, problem_size, 
            x_dim, y_dim, z_dim, 
            time_ekin, time_sum, time_f,
            analytics_process["start_date"], analytics_process["end_date"],
            simulation_process["start_date"], simulation_process["end_date"]
        ]

        monitor_files = glob.glob(f"{d}/monitor*")
        for m_file in monitor_files:
            new_df = pd.read_csv(m_file)
            new_df["exec_id"] = exec_id
            new_df["type"] = m_file.split("/")[-1].split("_")[1]
            monitor_df = pd.concat([monitor_df, new_df], ignore_index=True)

    if df.mpi_processes.duplicated().any():
        raise ValueError(f"[{label}] Duplicate MPI processes found")

    df["total_nodes"] = df["total_nodes"].astype(int)
    df["mpi_processes"] = df["mpi_processes"].astype(int)
    df.sort_values(by=["mpi_processes"], inplace=True)

    df["simulation_time"] = df["simulation_end"] - df["simulation_start"]
    df["simulation_analytics_time"] = df["analytics_end"] - df["analytics_start"]
    df["analytics_total_time"] = df["time_ekin"] + df["time_sum"] + df["time_f"]

    # ────────────────────────────
    # Plot time vs MPI processes
    # ────────────────────────────
    plt.figure(figsize=(8, 8))
    plt.plot(df["mpi_processes"], df["simulation_time"], marker='o', label='Simulation Time',
             color='black', linestyle='--', alpha=0.7)
    plt.plot(df["mpi_processes"], df["simulation_analytics_time"], marker='^',
             label='Simulation + Analytics Time', color='blue', linestyle=':', alpha=0.7)
    plt.legend(fontsize=15)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(df["mpi_processes"], rotation=45)
    plt.xlabel("Number of MPI Processes", fontsize=20)
    plt.ylabel("Time (seconds)", fontsize=20)
    plt.tick_params(axis='both', which='major', labelsize=15)
    plt.title(f"Weak Scaling ({label}): Time vs MPI Processes", fontsize=20)
    plt.tight_layout()
    plt.savefig(f"imgs/weak_time_vs_processes_{label}.pdf")
    plt.close()

    # ────────────────────────────
    # Monitor plots (CPU & MEM)
    # ────────────────────────────
    monitor_df["mpi_processes"] = monitor_df["exec_id"].apply(lambda x: int(x.split(":")[2]))
    for mpi_p in monitor_df["mpi_processes"].unique():
        sub_df = monitor_df[monitor_df["mpi_processes"] == mpi_p]

        plt.figure(figsize=(8, 8))
        for host in sub_df["hostname"].unique():
            host_type = sub_df[sub_df["hostname"] == host]["type"].values[0]
            plt_df = sub_df[sub_df["hostname"] == host]
            plt.plot(plt_df["unix_time"], plt_df["cpu_percent"], label=f"{host_type}_{host}")
        plt.xlabel("Time (seconds)")
        plt.ylabel("CPU Usage (%)")
        handles, labels = plt.gca().get_legend_handles_labels()
        sorted_handles_labels = sorted(zip(labels, handles), key=lambda x: x[0])
        sorted_labels, sorted_handles = zip(*sorted_handles_labels)
        plt.legend(sorted_handles, sorted_labels)
        plt.tight_layout()
        plt.savefig(f"imgs/weak_cpu_vs_time_{label}_{mpi_p}.png")
        plt.close()

        plt.figure(figsize=(10, 6))
        for host in sub_df["hostname"].unique():
            host_type = sub_df[sub_df["hostname"] == host]["type"].values[0]
            plt_df = sub_df[sub_df["hostname"] == host]
            plt.plot(plt_df["unix_time"], plt_df["mem_percent"], label=f"{host_type}_{host}")
        plt.xlabel("Time (seconds)")
        plt.ylabel("Memory Usage (%)")
        handles, labels = plt.gca().get_legend_handles_labels()
        sorted_handles_labels = sorted(zip(labels, handles), key=lambda x: x[0])
        sorted_labels, sorted_handles = zip(*sorted_handles_labels)
        plt.legend(sorted_handles, sorted_labels)
        plt.tight_layout()
        plt.savefig(f"imgs/weak_memory_vs_time_{label}_{mpi_p}.png")
        plt.close()

    return df, monitor_df

# ─────────────────────────────────────────────────────────────────────────────
# Process both 1-node and 2-nodes experiment sets
# ─────────────────────────────────────────────────────────────────────────────
df_1node, monitor_1node = process_weak_scaling(experiment_ids_1node, label="1node")
df_2nodes, monitor_2nodes = process_weak_scaling(experiment_ids_2nodes, label="2nodes")

# ─────────────────────────────────────────────────────────────────────────────
# Final comparison plot: Time vs MPI Processes (1-node vs 2-nodes)
# ─────────────────────────────────────────────────────────────────────────────
plt.figure(figsize=(10, 8))

# 1-node
plt.plot(df_1node["mpi_processes"], df_1node["simulation_time"], marker="o",
         linestyle="-", label="Sim Time (1 node)", color="skyblue")
plt.plot(df_1node["mpi_processes"], df_1node["simulation_analytics_time"], marker="o",
         linestyle=":", label="Sim+Analytics (1 node)", color="blue")

# 2-nodes
plt.plot(df_2nodes["mpi_processes"], df_2nodes["simulation_time"], marker="^",
         linestyle="-", label="Sim Time (2 nodes)", color="gray")
plt.plot(df_2nodes["mpi_processes"], df_2nodes["simulation_analytics_time"], marker="^",
         linestyle=":", label="Sim+Analytics (2 nodes)", color="black")

plt.legend(fontsize=12)
plt.grid(True, linestyle="--", alpha=0.7)
plt.xlabel("Number of MPI Processes", fontsize=16)
plt.ylabel("Time (seconds)", fontsize=16)
plt.title("Weak Scaling Comparison: 1 Node vs 2 Nodes", fontsize=18)
plt.xticks(sorted(set(df_1node["mpi_processes"]).union(df_2nodes["mpi_processes"])))
plt.tight_layout()
plt.savefig("imgs/weak_time_vs_processes_comparison.pdf")
plt.close()
