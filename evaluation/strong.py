import glob
import pandas as pd


experiment_ids = ['1748275656', '1748277095']


experiment_dirs = []
for _dir in experiment_ids:
    experiment_dirs.extend(glob.glob(f"../experiment/*{_dir}*"))
print(f"Found experiment directories: {experiment_dirs}")


df = pd.DataFrame(columns=["name", "exec_id", "total_nodes", "x_dim", "y_dim", "z_dim", "time_ekin", "time_sum", "time_f"])
for d in experiment_dirs:
    name = d.split("/")[-1].split(":")[0]
    id = name.split("_")[-1]
    total_nodes = d.split("/")[-1].split(":")[1]

    res_file = f"../experiment/{d}/analytics.e"
    
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

    df.loc[len(df)] = [
        name, id, total_nodes, x_dim, y_dim, z_dim, time_ekin, time_sum, time_f
    ]
print(df)