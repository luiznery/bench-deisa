import glob
import pandas as pd
from matplotlib import pyplot as plt
import glob


experiment_ids = ['weak_1748863919:2:4:2','weak_1748863828:2:2:1','weak_1748863788:2:1:0','weak_1748863964:2:8:3']

# Find all directories that match the experiment IDs
experiment_dirs = []
for _dir in experiment_ids:
    experiment_dirs.extend(glob.glob(f"../experiment_result/*{_dir}*"))
print(f"Found experiment directories: {experiment_dirs}")

# Create a DataFrame to store the results
df = pd.DataFrame(columns=["name", "exec_id", "total_nodes", "mpi_processes", "problem_size",  
                           "x_dim", "y_dim", "z_dim", 
                           "time_ekin", "time_sum", "time_f",
                           "analytics_start", "analytics_end",
                           "simulation_start", "simulation_end"])

monitor_df = pd.DataFrame()

# Loop through each experiment directory and extract the required information to fill the DataFrame
for d in experiment_dirs:
    exec_id = d.split("/")[-1]
    name = d.split("/")[-1].split(":")[0]
    total_nodes = int(d.split("/")[-1].split(":")[1])
    mpi_processes = int(d.split("/")[-1].split(":")[2])
    problem_size = int(d.split("/")[-1].split(":")[3])

    res_file = f"../experiment_result/{d}/analytics.e"
    
    data = []
    with open(res_file, "r") as f:
        for line in f:
            if line.strip():
                data.append(line.strip())

    x_dim = int([
        lin
        for lin in data 
        if lin.startswith("[Analytics] X-dim")
    ][0].split("=")[-1].strip())

    y_dim = int([
        lin
        for lin in data 
        if lin.startswith("[Analytics] Y-dim")
    ][0].split("=")[-1].strip())

    z_dim = int([
        lin
        for lin in data 
        if lin.startswith("[Analytics] Z-dim")
    ][0].split("=")[-1].strip())

    time_ekin = float([
        lin
        for lin in data 
        if lin.startswith("[Analytics] time ekin")
    ][0].split(":")[-1].strip())

    time_sum = float([
        lin
        for lin in data 
        if lin.startswith("[Analytics] time sum over xy:")
    ][0].split(":")[-1].strip())

    time_f = float([
        lin
        for lin in data 
        if lin.startswith("[Analytics] time fourier:")
    ][0].split(":")[-1].strip())

    # read dict in the file
    analytics_process_file = f"{d}/analytics_process_stats.txt"
    with open(analytics_process_file, "r") as f:
        analytics_process = eval(f.read())
    
    simulation_process_file = f"{d}/mpi_process_stats.txt"
    with open(simulation_process_file, "r") as f:
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
        new_df["type"] = m_file.split("/")[-1].split("_")[1]  # Extract type from filename
        monitor_df = pd.concat([monitor_df, new_df], ignore_index=True)
    

if df.mpi_processes.duplicated().any():
    raise ValueError("There are duplicate MPI processes in the DataFrame. Please check the experiment ids.")

# Converting columns to appropriate data types
df["total_nodes"] = df["total_nodes"].astype(int)
df["mpi_processes"] = df["mpi_processes"].astype(int)
df["problem_size"] = df["problem_size"].astype(int)
df.sort_values(by=["mpi_processes"], inplace=True)

# Computing run times
df["simulation_time"] = df["simulation_end"] - df["simulation_start"]
df["simulation_analytics_time"] = df["analytics_end"] - df["analytics_start"]
df["analytics_total_time"] = df["time_ekin"] + df["time_sum"] + df["time_f"]


# Plotting the results

# MPI Processes vs Problem Size
plt.figure(figsize=(10, 6))
plt.plot(
    df["mpi_processes"],
    df["simulation_time"],
    marker='o',
    label='Simulation Time',
    color='blue'
)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(df["mpi_processes"], rotation=45)
plt.xlabel("Number of MPI Processes")
plt.ylabel("Time (seconds)")
plt.savefig("imgs/weak_simulation_time_vs_processes.png")

# MPI Processes vs Analytics Time
plt.figure(figsize=(10, 6))
plt.plot(
    df["mpi_processes"],
    df["simulation_analytics_time"],
    marker='o',
    label='Analytics Time',
    color='orange'
)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(df["mpi_processes"], rotation=45)
plt.xlabel("Number of MPI Processes")
plt.ylabel("Time (seconds)")
plt.savefig("imgs/weak_simulation_analytics_time_vs_processes.png")

# MPI Processes vs Total Analytics Time
plt.figure(figsize=(10, 6))
plt.plot(
    df["mpi_processes"],
    df["analytics_total_time"],
    marker='o',
    label='Total Analytics Time',
    color='green'
)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(df["mpi_processes"], rotation=45)
plt.xlabel("Number of MPI Processes")
plt.ylabel("Time (seconds)")
plt.savefig("imgs/weak_analytics_time_vs_processes.png")    


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

    plt.savefig(f"imgs/weak_cpu_vs_time_{mpi_p}.png")

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
    
    plt.savefig(f"imgs/weak_memory_vs_time_{mpi_p}.png")
        
