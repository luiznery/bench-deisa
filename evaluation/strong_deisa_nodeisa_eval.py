import glob
import pandas as pd
from matplotlib import pyplot as plt
import glob
import numpy as np


experiment_ids_deisa = ['strong_1748863610:2:8:0','strong_1748863606:2:4:0','strong_1748863600:2:2:0',
                        'strong_1748863539:2:1:0','strong_1748863616:2:16:0','strong_1748863691:2:32:0']

experiment_ids_nodeisa = ['strong_nodeisa_1748866343:2:1:0','strong_nodeisa_1748866517:2:2:0',
                          'strong_nodeisa_1748866533:2:4:0','strong_nodeisa_1748866541:2:8:0',
                          'strong_nodeisa_1748866560:2:16:0','strong_nodeisa_1748866570:2:32:0']
  

# Find all directories that match the experiment IDs
experiment_dirs_deisa = []
for _dir in experiment_ids_deisa:
    experiment_dirs_deisa.extend(glob.glob(f"../experiment_result/*{_dir}*"))
print(f"Found experiment directories: {experiment_dirs_deisa}")

experiment_dirs_nodeisa = []
for _dir in experiment_ids_nodeisa:
    experiment_dirs_nodeisa.extend(glob.glob(f"../experiment_result/*{_dir}*"))
print(f"Found experiment directories: {experiment_dirs_nodeisa}")

# Create a DataFrame to store the results
df = pd.DataFrame(columns=["name", "exec_id", "total_nodes", "mpi_processes", "problem_size",  
                           "simulation_start", "simulation_end","deisa"])

monitor_df = pd.DataFrame()

# Loop through each experiment directory and extract the required information to fill the DataFrame
for d in experiment_dirs_deisa:
    exec_id = d.split("/")[-1]
    name = d.split("/")[-1].split(":")[0]
    total_nodes = int(d.split("/")[-1].split(":")[1])
    mpi_processes = int(d.split("/")[-1].split(":")[2])
    problem_size = int(d.split("/")[-1].split(":")[3])

    simulation_process_file = f"{d}/mpi_process_stats.txt"
    with open(simulation_process_file, "r") as f:
        simulation_process = eval(f.read())

    df.loc[len(df)] = [
        name, exec_id, total_nodes, mpi_processes, problem_size, 
        simulation_process["start_date"], simulation_process["end_date"], True
    ]
    
for d in experiment_dirs_nodeisa:
    exec_id = d.split("/")[-1]
    name = d.split("/")[-1].split(":")[0]
    total_nodes = int(d.split("/")[-1].split(":")[1])
    mpi_processes = int(d.split("/")[-1].split(":")[2])
    problem_size = int(d.split("/")[-1].split(":")[3])

    simulation_process_file = f"{d}/mpi_process_stats.txt"
    with open(simulation_process_file, "r") as f:
        simulation_process = eval(f.read())

    df.loc[len(df)] = [
        name, exec_id, total_nodes, mpi_processes, problem_size, 
        simulation_process["start_date"], simulation_process["end_date"], False
    ]

if df.duplicated(['mpi_processes','deisa']).any():
    raise ValueError("There are duplicate MPI processes in the DataFrame. Please check the experiment ids.")

# Converting columns to appropriate data types
df["total_nodes"] = df["total_nodes"].astype(int)
df["mpi_processes"] = df["mpi_processes"].astype(int)
df["problem_size"] = df["problem_size"].astype(int)
df.sort_values(by=["mpi_processes"], inplace=True)

# Computing run times
df["simulation_time"] = df["simulation_end"] - df["simulation_start"]

# Plotting the results

# MPI Processes vs Problem Size
plt.figure(figsize=(10, 6))
plt.plot(
    df[df.deisa]["mpi_processes"],
    df[df.deisa]["simulation_time"],
    marker='o',
    label='Simulation Time DEISA',
    color='blue'
)
plt.plot(
    df[~df.deisa]["mpi_processes"],
    df[~df.deisa]["simulation_time"],
    marker='o',
    label='Simulation Time No DEISA',
    color='red'
)

plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(df[df.deisa]["mpi_processes"], rotation=45)
plt.xlabel("Number of MPI Processes")
plt.ylabel("Time (seconds)")
plt.savefig("imgs/deisa_nodeisa_time_vs_processes.png")

# SpeedUp Calculation
T1 = df[(~df.deisa)&(df.mpi_processes==1)]["simulation_time"]
print(f"T1: {T1.values[0]} seconds")
df["speedup"] = df.simulation_time.apply(lambda x: T1/x)

# Plotting SpeedUp
plt.figure(figsize=(10, 6))
plt.plot(
    df[~df.deisa]["mpi_processes"],
    df[~df.deisa]["speedup"],
    marker='o',
    label='SpeedUp Simulation No DEISA',
    color='blue'
)
plt.plot(
    df[df.deisa]["mpi_processes"],
    df[df.deisa]["speedup"],
    marker='o',
    label='SpeedUp Simulation DEISA',
    color='red'
)
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(df[df.deisa]["mpi_processes"], rotation=45)
plt.xlabel("Number of MPI Processes")
plt.ylabel("SpeedUp")
plt.savefig("imgs/speedup.png")


