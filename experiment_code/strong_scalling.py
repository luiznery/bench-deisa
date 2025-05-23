import execo_g5k
import os
import socket
import time

from experiment import *

# this will be /home/lmascare
HOME_DIR = os.path.expanduser("~")

PATH_TO_SIF_FILE = HOME_DIR + "/bench/docker/images/bench.sif"

PDI_DEISA_YML = HOME_DIR + "/bench/simulation/io_deisa.yml"
SIM_EXECUTABLE = HOME_DIR + "/bench/simulation/build/main"
DEISA_PATH = HOME_DIR + "/bench/deisa/"

ANALYTICS_PY_FILE = HOME_DIR + "/bench/in-situ/bench_deisa.py"

# must be in the same directory as the script/notebook
SCHEDULER_FILE = HOME_DIR + "/bench/experiment/scheduler.json"

OUTPUT_DIR = HOME_DIR + "/bench/experiment/"

DEISA_PATH = HOME_DIR + "/bench/deisa/"


SIMULATION_INI = HOME_DIR + "/bench/experiment_code/setup_strong.ini"

# the total number of nodes needs to be THE SAME as the total number of workers passed in the analytics script
DASK_WORKERS_PER_NODE = 1
TOTAL_DASK_WORKERS = 4

nb_reserved_nodes = 4 + 1 # execution nodes + 1 head node

walltime = 60*60 # in seconds

exp_name = f"STRONG:{nb_reserved_nodes-1}"


if __name__ == "__main__":

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
        configs = get_configs(SIMULATION_INI)

        # Getting the ip addresses of the nodes
        head_node_ip = socket.gethostbyname(head_node.address)
        nodes_ips = []
        for node in nodes:
            nodes_ips.append(socket.gethostbyname(node.address))
        print(f"[{exp_name}] Head node IP: {head_node_ip}")
        print(f"[{exp_name}] Other nodes IPs: {nodes_ips}")

        # Running the scheduler
        print(f"[{exp_name}] Initializing the scheduler...")
        run_scheduler(head_node, SCHEDULER_FILE, OUTPUT_DIR, PATH_TO_SIF_FILE)
        print(f"[{exp_name}] Scheduler started!")

        # Running the Dask workers
        print(f"[{exp_name}] Initializing the workers...")
        run_workers(nodes, head_node_ip, DASK_WORKERS_PER_NODE, SCHEDULER_FILE, OUTPUT_DIR, PATH_TO_SIF_FILE)
        print(f"[{exp_name}] Workers started!")

        time.sleep(5)  # wait for the workers to start

        # Running the analytics
        print(f"[{exp_name}] Initializing the analytics...")
        analytics_process = run_analytics(head_node, TOTAL_DASK_WORKERS, DEISA_PATH, ANALYTICS_PY_FILE, SCHEDULER_FILE, 
                                        OUTPUT_DIR, PATH_TO_SIF_FILE)
        print(f"[{exp_name}] Analytics started!")

        # Running the simulation
        print(f"[{exp_name}] Initializing the simulation...")
        mx = int(configs["mx"])
        my = int(configs["my"])
        mz = int(configs["mz"])
        mpi_np = mx * my * mz
        assert mpi_np <= total_simulation_cores, "mpi_np must be less than or equal to total_simulation_cores"
        print(f"[{exp_name}] Running simulation with {mpi_np} MPI processes")
        mpi_process = run_simulation(head_node, nodes, mpi_np, cores_per_node, DEISA_PATH, SIM_EXECUTABLE, SIMULATION_INI, 
                            PDI_DEISA_YML, OUTPUT_DIR, PATH_TO_SIF_FILE)
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
