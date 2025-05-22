import execo
import execo_g5k
import execo_engine
import time
import os
from dask.distributed import Client
import socket
import configparser

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



def get_configs(config_file):
    """ 
    Get configs from a .ini file.

    Arguments:
        config_file (str): Path to the .ini configuration file.
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    configs = {}
    for section in config.sections():
        for key, value in config.items(section):
            configs[key] = value

    return configs


def alloc_nodes(nb_reserved_nodes: int, walltime: int):
    """
    Allocates nodes for the simulation. The first node is the head node and the others are execution nodes.
    If nb_reserved_nodes is 1, the head node is the only node reserved.

    Arguments:
        nb_reserved_nodes (int): Number of nodes to reserve, including the head node. Must be greater than 0.
        walltime (int): Walltime in seconds. Must be greater than 0.
    """    
    assert nb_reserved_nodes > 0, "Number of reserved nodes must be greater than 0"
    assert walltime > 0, "Walltime must be greater than 0"
    jobs = execo_g5k.oarsub(
        [
            (
                execo_g5k.OarSubmission(f"nodes={nb_reserved_nodes}", walltime=walltime),
                "grenoble",
            )
        ]
    )
    return jobs

def run_scheduler(node, scheduler_file: str, output_dir: str, 
                  path_to_sif_file: str) -> execo.SshProcess:
    """
    Run the Dask scheduler in the given node.

    Arguments:
        node: The node where the scheduler will be run.
        scheduler_file (str): Path to the scheduler file.
        output_dir (str): Directory where the output files will be saved.
        path_to_sif_file (str): Path to the Singularity image file.
    """
    if os.path.exists(scheduler_file):
        os.remove(scheduler_file)

    scheduler_cmd = (
        f"dask scheduler "
        # f"--host {head_node.address} "
        f"--scheduler-file {scheduler_file} "
        f"> {output_dir}scheduler.e 2>&1; "
        "sync"
    )

    scheduler_process = execo.SshProcess(
        f'singularity exec {path_to_sif_file} bash -c "{scheduler_cmd}"',
        node,
    )
    scheduler_process.start()

    # Wait for the scheduler to start by checking the scheduler file
    while not os.path.exists(scheduler_file):
        time.sleep(1)
    
    return scheduler_process

def run_workers(nodes, head_node_ip: str, dask_workers_per_node: int, scheduler_file: str, output_dir: str, 
                path_to_sif_file: str) -> execo.SshProcess:
    """
    Run the Dask workers in the given nodes.

    Arguments:
        nodes (list): List of nodes where the workers will be run.
        head_node_ip (str): IP address of the head node.
        dask_workers_per_node (int): Number of Dask workers per node.
        scheduler_file (str): Path to the scheduler file.
        output_dir (str): Directory where the output files will be saved.
        path_to_sif_file (str): Path to the Singularity image file.
    """
    worker_cmd = (
        f"dask worker "
        f"tcp://{head_node_ip}:8786 "
        # f"--dashboard-address {head_node.address}:8787 "
        f"--nworkers {dask_workers_per_node} "
        "--nthreads 1 "
        "--local-directory /tmp "
        f"--scheduler-file {scheduler_file} "
        f"> {output_dir}worker.e 2>&1"
    )

    for node in nodes:
        worker_process = execo.SshProcess(
            f'singularity exec {path_to_sif_file} bash -c "{worker_cmd}"',
            node,
        )
        worker_process.start()

    return worker_process

def run_analytics(node, total_dask_workers: int, deisa_path: str, analytics_py_file: str, 
                  scheduler_file: str, output_dir: str, path_to_sif_file: str) -> execo.SshProcess:
    """
    Run the analytics script in the given node.

    Arguments:
        node: The node where the analytics will be run.
        total_dask_workers (int): Total number of Dask workers.
        deisa_path (str): Path to the DEISA directory.
        analytics_py_file (str): Path to the analytics Python file.
        scheduler_file (str): Path to the scheduler file.
        output_dir (str): Directory where the output files will be saved.
        path_to_sif_file (str): Path to the Singularity image file.
    """    

    py_cmd = (
        f'export PYTHONPATH={deisa_path}:$PYTHONPATH; '
        f'python3 {analytics_py_file} {total_dask_workers} {scheduler_file} > {output_dir}analytics.e 2>&1'
    )
    analytics_cmd = (
        f'singularity exec {path_to_sif_file} bash -c "{py_cmd}"'
    )

    analytics_process = execo.SshProcess(
        analytics_cmd,
        node,
    )
    analytics_process.start()
    
    return analytics_process

def run_simulation(head_node, nodes: list, mpi_np: int, cores_per_node: int, deisa_path, 
                   sim_executable: str, simulation_ini: str, pdi_deisa_yml: str, output_dir: str, 
                   path_to_sif_file: str) -> execo.SshProcess:
                       
    
    host_list = ",".join([f"{node.address}:{cores_per_node}" for node in nodes])
    # host_list = ",".join([f"{node.address}" for node in nodes])

    simulation_cmd = (
        f'export PYTHONPATH={deisa_path}:$PYTHONPATH; '
        f'pdirun {sim_executable} {simulation_ini} {pdi_deisa_yml} --kokkos-map-device-id-by=mpi_rank > {output_dir}simulation.e 2>&1'
    )

    # Build the command with two singularity exec calls:
    mpi_cmd = (
        'export OMP_NUM_THREADS=2; '
        'export OMP_PROC_BIND=spread; '
        'export OMP_PLACES=threads; '
        f"mpirun -np {mpi_np} "
        f"--map-by slot "
        f"--host {host_list} "
        f'singularity exec {path_to_sif_file} bash -c "{simulation_cmd}"'
    )

    mpi_process = execo.SshProcess(
        mpi_cmd,
        head_node,
    )
    mpi_process.start()

    return mpi_process


##############################################################

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
