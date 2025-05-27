import execo_g5k
import os
import socket
import time

from experiment import *

# this will be /home/lmascare
HOME_DIR = os.path.expanduser("~")

PATH_TO_SIF_FILE = HOME_DIR + "/bench/docker/images/bench.sif"
# PDI_DEISA_YML = HOME_DIR + "/bench/simulation/io_deisa.yml"
SIM_EXECUTABLE = HOME_DIR + "/bench/simulation/build/main"
DEISA_PATH = HOME_DIR + "/bench/deisa/"
ANALYTICS_PY_FILE = HOME_DIR + "/bench/in-situ/bench_deisa.py"
# SCHEDULER_FILE = HOME_DIR + "/bench/experiment/scheduler.json" # must be in the same directory as the script/notebook
SCHEDULER_PATH = HOME_DIR + "/bench/experiment/"
DEISA_PATH = HOME_DIR + "/bench/deisa/"

# SIMULATION_INI = HOME_DIR + "/bench/experiment_code/setup_strong.ini"
# OUTPUT_DIR = HOME_DIR + "/bench/experiment/"


def run_experiment(nb_reserved_nodes: int, s_ini_file: str, pdi_deisa_yml: str, name: str, walltime=10*60, dask_workers_per_node=1, 
                   total_dask_workers=None):
    """
    Run experiment with the given parameters.

    Arguments:
        nb_reserved_nodes (int): Total number of nodes to reserve, including the head node.
        exp_name (str): Name of the experiment.
        walltime (int): Walltime for the reservation in seconds.
        dask_workers_per_node (int): Number of Dask workers per node.
        total_dask_workers (int, optional): Total number of Dask workers. If None, it will be nb_reserved_nodes - 1.
    """
    if nb_reserved_nodes < 2:
        raise ValueError("nb_reserved_nodes must be greater than or equal to 2")
    
    if walltime <= 0:
        raise ValueError("walltime must be greater than 0")
    
    if dask_workers_per_node < 1:
        raise ValueError("dask_workers_per_node must be greater than or equal to 1")
    
    if total_dask_workers is None:
        total_dask_workers = nb_reserved_nodes - 1
    elif total_dask_workers > nb_reserved_nodes - 1:
        raise ValueError("total_dask_workers must be less than or equal to nb_reserved_nodes - 1")

    exp_name = f"{name}:{nb_reserved_nodes}:{s_ini_file.split('/')[-1].split('.')[0]}"
    output_dir = HOME_DIR + f"/bench/experiment/{exp_name}/"

    #create output directory if it does not exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        raise FileExistsError(
            f"Output directory {output_dir} already exists. Please remove it or choose a different name.")
    
    
    scheduler_file = extract_scheduler_path(pdi_deisa_yml)
    if scheduler_file is None:
        raise FileNotFoundError(
            f"Scheduler file not found in {pdi_deisa_yml}. Please check the file and try again.")

    try:
        # Alloc the nodes
        jobs = alloc_nodes(nb_reserved_nodes, walltime)
        job_id, site = jobs[0]

        print(f"[{exp_name}] Job {job_id} reserved on site {site}")

        nodes = execo_g5k.oar.get_oar_job_nodes(job_id, site)
        head_node, nodes = nodes[0], nodes[1:]

        print(f"[{exp_name}] Head node: {head_node}")
        print(f"[{exp_name}] Other nodes: {nodes}")

        cores_per_node = execo_g5k.get_host_attributes(head_node)["architecture"]["nb_cores"]
        total_simulation_cores = cores_per_node * len(nodes)

        # print(f"[{exp_name}] Total simulation cores: {total_simulation_cores}")

        # Read the simulation configuration file
        configs = get_configs(s_ini_file)

        # Getting the ip addresses of the nodes
        head_node_ip = socket.gethostbyname(head_node.address)
        nodes_ips = []
        for node in nodes:
            nodes_ips.append(socket.gethostbyname(node.address))
        print(f"[{exp_name}] Head node IP: {head_node_ip}")
        print(f"[{exp_name}] Other nodes IPs: {nodes_ips}")

        # Running the scheduler
        print(f"[{exp_name}] Initializing the scheduler...")
        run_scheduler(head_node, scheduler_file, output_dir, PATH_TO_SIF_FILE)
        print(f"[{exp_name}] Scheduler started!")

        # Running the Dask workers
        print(f"[{exp_name}] Initializing the workers...")
        run_workers(nodes, head_node_ip, dask_workers_per_node, scheduler_file, output_dir, PATH_TO_SIF_FILE)
        print(f"[{exp_name}] Workers started!")

        time.sleep(5)  # wait for the workers to start

        # Running the analytics
        print(f"[{exp_name}] Initializing the analytics...")
        analytics_process = run_analytics(head_node, total_dask_workers, DEISA_PATH, ANALYTICS_PY_FILE, scheduler_file, 
                                        output_dir, PATH_TO_SIF_FILE)
        print(f"[{exp_name}] Analytics started!")

        # Running the simulation
        print(f"[{exp_name}] Initializing the simulation...")
        mx = int(configs["mx"])
        my = int(configs["my"])
        mz = int(configs["mz"])
        mpi_np = mx * my * mz
        assert mpi_np <= total_simulation_cores, "mpi_np must be less than or equal to total_simulation_cores"
        print(f"[{exp_name}] Running simulation with {mpi_np} MPI processes")
        mpi_process = run_simulation(head_node, nodes, mpi_np, cores_per_node, DEISA_PATH, SIM_EXECUTABLE, s_ini_file, 
                            pdi_deisa_yml, output_dir, PATH_TO_SIF_FILE)
        print(f"[{exp_name}] Simulation started!")

        # Waiting for everything to finish
        print(f"[{exp_name}] Waiting for the simulation to finish...")
        mpi_process.wait()
        print(f"[{exp_name}] Simulation finished!")
        print(f"[{exp_name}] Waiting for the analytics to finish...")
        analytics_process.wait()
        print(f"[{exp_name}] Analytics finished!")

    except Exception as e:
        print(f"[{exp_name}] An error occurred: {e}")

    finally:
        # Delete the job
        execo_g5k.oardel(jobs)
        print(f"[{exp_name}] Job deleted!")

        # delete scheduler file
        if os.path.exists(scheduler_file):
            os.remove(scheduler_file)
            print(f"[{exp_name}] Scheduler file {scheduler_file} deleted!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run strong scaling experiment.")
    parser.add_argument("--nb_reserved_nodes","-nb", type=int, required=True, 
                        help="Number of reserved nodes (including head node).")
    parser.add_argument("--name", "-nm", type=str, required=True, help="Name of the experiment.")
    parser.add_argument("--simulation_ini_file", "-si", type=str, required=True,
                        help="Path to the simulation ini file.")
    parser.add_argument("--pdi_deisa_yml", "-pd", type=str, required=True,
                        help="Path to the PDI DEISA YAML file.")
    parser.add_argument("--walltime", "-t",type=int, default=10*60, help="Walltime in seconds (default: 600).")
    parser.add_argument("--dask_workers_per_node","-dw", type=int, default=1, 
                        help="Number of Dask workers per node (default: 1).")
    parser.add_argument("--total_dask_workers", "-tw", type=int, default=None,
                        help="Total number of Dask workers (default: None, which means nb_reserved_nodes - 1).")
    args = parser.parse_args()

    if args.total_dask_workers is None:
        args.total_dask_workers = args.nb_reserved_nodes - 1

    run_experiment(nb_reserved_nodes=args.nb_reserved_nodes, 
                   s_ini_file=args.simulation_ini_file,
                   pdi_deisa_yml=args.pdi_deisa_yml,
                   name=args.name,
                   walltime=args.walltime,
                   dask_workers_per_node=args.dask_workers_per_node,
                   total_dask_workers=args.total_dask_workers)