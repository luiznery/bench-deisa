import glob
import pandas as pd
from matplotlib import pyplot as plt

# ─────────────────────────────────────────────────────────────────────────────
# Define your two experiment‐ID groups
# ─────────────────────────────────────────────────────────────────────────────

experiment_ids_1node = [
    # 'strong_1748956486:2:1:256,256,32',
    # 'strong_1748956561:2:2:256,256,32',
    # 'strong_1748956742:2:4:256,256,32',
    # 'strong_1748956771:2:8:256,256,32',

    'strong-debug_1749554067:2:8:128,64,32',
    'strong-debug_1749554211:2:4:128,64,32',
    'strong-debug_1749554412:2:1:128,64,32',
    'strong-debug_1749554418:2:2:128,64,32',
    
]

experiment_ids_2nodes = [
    # 'strong_1749055937:3:2:256,256,32',
    # 'strong_1749056169:3:4:256,256,32',
    # 'strong_1749056192:3:8:256,256,32',
]


def process_and_plot(experiment_ids, label):
    """
    Given a list of experiment IDs and a label (e.g. "1node" or "2nodes"),
    this function:
      1. Finds matching directories under ../experiment_result/
      2. Parses analytics and MPI‐stats files into two DataFrames:
         - df_<label>       : summary of each experiment’s timing + dims
         - monitor_<label>  : concatenated per‐process monitor CSVs
      3. Plots:
         - Time vs MPI Processes
         - CPU% vs Time per host
         - Mem% vs Time per host
         - SpeedUp curves
      4. Saves all figures under imgs/strong_*_{label}.png (or .pdf)
    """

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Collect all matching directories for this experiment group
    # ─────────────────────────────────────────────────────────────────────────
    experiment_dirs = []
    for exp_id in experiment_ids:
        # any folder whose name contains the exact exp_id
        found = glob.glob(f"../experiment_result/*{exp_id}*")
        experiment_dirs.extend(found)

    print(f"[{label}] Found experiment directories:\n  {experiment_dirs}\n")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Build two DataFrames: summary_df and monitor_df
    # ─────────────────────────────────────────────────────────────────────────
    summary_df = pd.DataFrame(
        columns=[
            "name",
            "exec_id",
            "total_nodes",
            "mpi_processes",
            "problem_size",
            "x_dim",
            "y_dim",
            "z_dim",
            "time_ekin",
            "time_sum",
            "time_f",
            "analytics_start",
            "analytics_end",
            "simulation_start",
            "simulation_end",
        ]
    )
    monitor_df = pd.DataFrame()

    for d in experiment_dirs:
        # 2.1 Extract ID fields from directory name
        exec_id = d.rstrip("/").split("/")[-1]
        parts = exec_id.split(":")
        name = parts[0]
        total_nodes = int(parts[1])
        mpi_processes = int(parts[2])
        problem_size = parts[3]  # e.g. "256,256,32"

        # 2.2 Read analytics.e (plain‐text) for dims & times
        res_file = f"{d}/analytics.e"
        data_lines = []
        with open(res_file, "r") as f:
            for line in f:
                if line.strip():
                    data_lines.append(line.strip())

        # X, Y, Z dims
        x_dim = int(
            [ln for ln in data_lines if ln.startswith("[Analytics] X-dim")][0]
            .split("=")[-1]
            .strip()
        )
        y_dim = int(
            [ln for ln in data_lines if ln.startswith("[Analytics] Y-dim")][0]
            .split("=")[-1]
            .strip()
        )
        z_dim = int(
            [ln for ln in data_lines if ln.startswith("[Analytics] Z-dim")][0]
            .split("=")[-1]
            .strip()
        )

        # three timing entries
        time_ekin = float(
            [ln for ln in data_lines if ln.startswith("[Analytics] time ekin")][0]
            .split(":")[-1]
            .strip()
        )
        time_sum = float(
            [ln for ln in data_lines if ln.startswith("[Analytics] time sum over xy:")][0]
            .split(":")[-1]
            .strip()
        )
        time_f = float(
            [ln for ln in data_lines if ln.startswith("[Analytics] time fourier:")][0]
            .split(":")[-1]
            .strip()
        )

        # 2.3 Read analytics_process_stats.txt (a single‐line dict)
        analytics_process_file = f"{d}/analytics_process_stats.txt"
        with open(analytics_process_file, "r") as f:
            analytics_process = eval(f.read())
        # 2.4 Read mpi_process_stats.txt (also a single‐line dict)
        simulation_process_file = f"{d}/mpi_process_stats.txt"
        with open(simulation_process_file, "r") as f:
            simulation_process = eval(f.read())

        # 2.5 Append a row to summary_df
        summary_df.loc[len(summary_df)] = [
            name,
            exec_id,
            total_nodes,
            mpi_processes,
            problem_size,
            x_dim,
            y_dim,
            z_dim,
            time_ekin,
            time_sum,
            time_f,
            analytics_process["start_date"],
            analytics_process["end_date"],
            simulation_process["start_date"],
            simulation_process["end_date"],
        ]

        # 2.6 Collect all monitor CSVs under that directory
        monitor_files = glob.glob(f"{d}/monitor*")
        for m_file in monitor_files:
            subdf = pd.read_csv(m_file)
            subdf["exec_id"] = exec_id
            # Extract “cpu”/“mem” etc. from filename e.g. monitor_cpu_*.csv
            subdf["type"] = m_file.split("/")[-1].split("_")[1]
            monitor_df = pd.concat([monitor_df, subdf], ignore_index=True)

    # 2.7 Sanity‐check: no duplicate mpi_processes in summary_df
    if summary_df.mpi_processes.duplicated().any():
        raise ValueError(f"[{label}] Duplicate MPI‐process count found in {label} set")

    # 2.8 Convert types and sort by mpi_processes
    summary_df["total_nodes"] = summary_df["total_nodes"].astype(int)
    summary_df["mpi_processes"] = summary_df["mpi_processes"].astype(int)
    summary_df.sort_values(by=["mpi_processes"], inplace=True)

    # 2.9 Compute derived timing columns
    summary_df["simulation_time"] = (
        summary_df["simulation_end"] - summary_df["simulation_start"]
    )
    summary_df["simulation_analytics_time"] = (
        summary_df["analytics_end"] - summary_df["analytics_start"]
    )
    summary_df["analytics_total_time"] = (
        summary_df["time_ekin"] + summary_df["time_sum"] + summary_df["time_f"]
    )

    # Add “mpi_processes” to each monitor row for easier plotting
    monitor_df["mpi_processes"] = monitor_df["exec_id"].apply(
        lambda x: int(x.split(":")[2])
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Plot #1: MPI Processes vs Time (Simulation vs Simulation+Analytics)
    # ─────────────────────────────────────────────────────────────────────────
    plt.figure(figsize=(8, 8))
    plt.plot(
        summary_df["mpi_processes"],
        summary_df["simulation_time"],
        marker="o",
        label="Simulation Time",
        color="black",
        linestyle="--",
        alpha=0.7,
    )
    plt.plot(
        summary_df["mpi_processes"],
        summary_df["simulation_analytics_time"],
        marker="^",
        label="Simulation + Analytics Time",
        color="blue",
        linestyle=":",
        alpha=0.7,
    )
    plt.legend(fontsize=15)
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.xticks(summary_df["mpi_processes"], rotation=45)
    plt.xlabel("Number of MPI Processes", fontsize=20)
    plt.ylabel("Time (seconds)", fontsize=20)
    plt.ylim([0, 1800])
    plt.tick_params(axis="both", which="major", labelsize=15)
    plt.title(f"Strong Scaling ({label}): Time vs MPI Processes", fontsize=20)
    plt.tight_layout()
    plt.savefig(f"imgs/strong_time_vs_processes_{label}.pdf")
    plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Plot #2 & #3: For each mpi_process count, CPU% & Mem% vs Time per host
    # ─────────────────────────────────────────────────────────────────────────
    for mpi_p in sorted(monitor_df["mpi_processes"].unique()):
        sub_df = monitor_df[monitor_df["mpi_processes"] == mpi_p]

        # 4.1 CPU Usage vs Time
        plt.figure(figsize=(8, 8))
        for host in sub_df["hostname"].unique():
            host_type = sub_df[sub_df["hostname"] == host]["type"].values[0]
            df_host = sub_df[sub_df["hostname"] == host]
            plt.plot(
                df_host["unix_time"],
                df_host["cpu_percent"],
                label=f"{host_type}_{host}",
            )

        plt.xlabel("Time (seconds)")
        plt.ylabel("CPU Usage (%)")
        handles, labels = plt.gca().get_legend_handles_labels()
        sorted_handles_labels = sorted(zip(labels, handles), key=lambda x: x[0])
        sorted_labels, sorted_handles = zip(*sorted_handles_labels)
        plt.legend(sorted_handles, sorted_labels)
        plt.tight_layout()
        plt.savefig(f"imgs/strong_cpu_vs_time_{label}_{mpi_p}.png")
        plt.close()

        # 4.2 Memory Usage vs Time
        plt.figure(figsize=(8, 8))
        for host in sub_df["hostname"].unique():
            host_type = sub_df[sub_df["hostname"] == host]["type"].values[0]
            df_host = sub_df[sub_df["hostname"] == host]
            plt.plot(
                df_host["unix_time"],
                df_host["mem_percent"],
                label=f"{host_type}_{host}",
            )

        plt.xlabel("Time (seconds)")
        plt.ylabel("Memory Usage (%)")
        handles, labels = plt.gca().get_legend_handles_labels()
        sorted_handles_labels = sorted(zip(labels, handles), key=lambda x: x[0])
        sorted_labels, sorted_handles = zip(*sorted_handles_labels)
        plt.legend(sorted_handles, sorted_labels)
        plt.tight_layout()
        plt.savefig(f"imgs/strong_memory_vs_time_{label}_{mpi_p}.png")
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Plot #4: SpeedUp Curves
    # ─────────────────────────────────────────────────────────────────────────
    # Use the single‐process (or minimum mpi_process) time as T1
    min_proc = summary_df["mpi_processes"].min()
    T1_sim_analytics = float(
        summary_df[summary_df["mpi_processes"] == min_proc]["simulation_analytics_time"]
    )
    T1_sim = float(
        summary_df[summary_df["mpi_processes"] == min_proc]["simulation_time"]
    )
    summary_df["sa_speedup"] = summary_df["simulation_analytics_time"].apply(
        lambda x: T1_sim_analytics / x
    )
    summary_df["s_speedup"] = summary_df["simulation_time"].apply(
        lambda x: T1_sim / x
    )

    plt.figure(figsize=(8, 8))
    plt.plot(
        summary_df["mpi_processes"],
        summary_df["s_speedup"],
        marker="o",
        color="black",
        label="Simulation SpeedUp",
        linestyle="--",
    )
    plt.plot(
        summary_df["mpi_processes"],
        summary_df["sa_speedup"],
        marker="^",
        color="blue",
        label="Simulation + Analytics SpeedUp",
        linestyle=":",
    )
    # Ideal line from (min_proc, 1) to (max_proc, max_proc/min_proc)
    max_proc = summary_df["mpi_processes"].max()
    plt.plot(
        [min_proc, max_proc],
        [1, max_proc / min_proc],
        linestyle="--",
        color="red",
        label="Ideal SpeedUp",
    )
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.xticks(summary_df["mpi_processes"].unique(), rotation=45)
    plt.xlabel("Number of MPI Processes", fontsize=20)
    plt.ylabel("SpeedUp", fontsize=20)
    plt.tick_params(axis="both", which="major", labelsize=15)
    plt.title(f"Strong Scaling ({label}): SpeedUp vs MPI Processes", fontsize=20)
    plt.legend(fontsize=15)
    plt.tight_layout()
    plt.savefig(f"imgs/strong_speedup_{label}.pdf")
    plt.close()

    # Return the DataFrames in case you want to inspect them
    return summary_df, monitor_df


# ─────────────────────────────────────────────────────────────────────────────
# Run for “1node” experiments
if len(experiment_ids_1node) > 0:
    df_1node, monitor_1node = process_and_plot(experiment_ids_1node, label="1node")

# Run for “2nodes” experiments
if len(experiment_ids_2nodes) > 0:
    df_2nodes, monitor_2nodes = process_and_plot(experiment_ids_2nodes, label="2nodes")

# ─────────────────────────────────────────────────────────────────────────────
# Combine Plot: Simulation vs Simulation+Analytics Time (1node vs 2nodes)
# ─────────────────────────────────────────────────────────────────────────────

plt.figure(figsize=(10, 8))

if len(experiment_ids_1node) > 0:
    
    # 1-node lines
    plt.plot(
        df_1node["mpi_processes"],
        df_1node["simulation_time"],
        marker="o",
        linestyle="-",
        label="Simulation Time (1 node)",
        color="skyblue",
    )
    plt.plot(
        df_1node["mpi_processes"],
        df_1node["simulation_analytics_time"],
        marker="o",
        linestyle=":",
        label="Sim+Analytics Time (1 node)",
        color="blue",
    )
    plt.plot(
        df_1node["mpi_processes"],
        df_1node["analytics_total_time"],
        marker="o",
        linestyle=":",
        label="Analytics Time (1 node)",
        color="blue",
    )

if len(experiment_ids_2nodes) > 0:
    # 2-node lines
    plt.plot(
        df_2nodes["mpi_processes"],
        df_2nodes["simulation_time"],
        marker="^",
        linestyle="-",
        label="Simulation Time (2 nodes)",
        color="gray",
    )
    plt.plot(
        df_2nodes["mpi_processes"],
        df_2nodes["simulation_analytics_time"],
        marker="^",
        linestyle=":",
        label="Sim+Analytics Time (2 nodes)",
        color="black",
    )

plt.legend(fontsize=12)
plt.grid(True, linestyle="--", alpha=0.7)
plt.xlabel("Number of MPI Processes", fontsize=16)
plt.ylabel("Time (seconds)", fontsize=16)
plt.title("Strong Scaling Comparison: 1 Node vs 2 Nodes", fontsize=18)
x_ticks = set(df_1node["mpi_processes"])
if len(experiment_ids_2nodes) > 0:
    x_ticks = x_ticks.union(df_2nodes["mpi_processes"])
x_ticks = sorted(x_ticks)
plt.xticks(x_ticks)
plt.tick_params(axis="both", which="major", labelsize=12)
plt.tight_layout()
plt.savefig("imgs/strong_time_vs_processes_comparison.pdf")
plt.close()
