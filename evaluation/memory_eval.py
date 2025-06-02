import glob
import pandas as pd
from matplotlib import pyplot as plt
import glob


experiment_ids = ['weak_1748729080']

# Find all directories that match the experiment IDs
experiment_dirs = []
for _dir in experiment_ids:
    experiment_dirs.extend(glob.glob(f"../experiment_result/*{_dir}*"))
print(f"Found experiment directories: {experiment_dirs}")

monitor_df = pd.DataFrame()

# Loop through each experiment directory and extract the required information to fill the DataFrame
for d in experiment_dirs:
    exec_id = d.split("/")[-1]
    name = d.split("/")[-1].split(":")[0]
    total_nodes = int(d.split("/")[-1].split(":")[1])
    mpi_processes = int(d.split("/")[-1].split(":")[2])
    problem_size = int(d.split("/")[-1].split(":")[3])

    res_file = f"../experiment_result/{d}/analytics.e"
    

    monitor_files = glob.glob(f"{d}/monitor*")
    for m_file in monitor_files:
        new_df = pd.read_csv(m_file)
        new_df["exec_id"] = exec_id
        new_df["type"] = m_file.split("/")[-1].split("_")[1]  # Extract type from filename
        monitor_df = pd.concat([monitor_df, new_df], ignore_index=True)
    


# Plotting the results


monitor_df["mpi_processes"] = monitor_df["exec_id"].apply(
    lambda x: int(x.split(":")[2])
)
for mpi_p in monitor_df["mpi_processes"].unique():
    sub_df = monitor_df[monitor_df["mpi_processes"] == mpi_p]
    
    #CPU Usage vs Time for each node
    plt.figure(figsize=(10, 6))
    for host in sub_df["hostname"].unique():
        host_type = sub_df[sub_df["hostname"] == host]["type"].values[0]
        plt_df = sub_df[sub_df["hostname"] == host]
        plt.plot(
            plt_df["unix_time"],
            plt_df["cpu_percent"],
            label=f"{host_type}_{host}",
        )
    plt.xlabel("Time (seconds)")
    plt.ylabel("CPU Usage (%)")
    
    # Sort legend by label
    handles, labels = plt.gca().get_legend_handles_labels()
    sorted_handles_labels = sorted(zip(labels, handles), key=lambda x: x[0])
    sorted_labels, sorted_handles = zip(*sorted_handles_labels)
    plt.legend(sorted_handles, sorted_labels)

    plt.savefig(f"imgs/cpu_vs_time_{mpi_p}.png")

    # Memory Usage vs Time for each node
    plt.figure(figsize=(10, 6))
    for host in sub_df["hostname"].unique():
        host_type = sub_df[sub_df["hostname"] == host]["type"].values[0]
        plt_df = sub_df[sub_df["hostname"] == host]
        plt.plot(
            plt_df["unix_time"],
            plt_df["mem_percent"],
            label=f"{host_type}_{host}",
        )
    plt.xlabel("Time (seconds)")
    plt.ylabel("Memory Usage (%)")
    
    # Sort legend by label
    handles, labels = plt.gca().get_legend_handles_labels()
    sorted_handles_labels = sorted(zip(labels, handles), key=lambda x: x[0])
    sorted_labels, sorted_handles = zip(*sorted_handles_labels)
    plt.legend(sorted_handles, sorted_labels)
    
    plt.savefig(f"imgs/memory_vs_time_{mpi_p}.png")
        
