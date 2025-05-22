import execo
import execo_g5k
import execo_engine
import time
import os
from dask.distributed import Client

# this will be /home/lmascare
HOME_DIR = os.path.expanduser("~")

PATH_TO_SIF_FILE = HOME_DIR + "/bench/docker/images/bench.sif"

SIMULATION_INI = HOME_DIR + "/bench/simulation/setup.ini"
PDI_DEISA_YML = HOME_DIR + "/bench/simulation/io_deisa.yml"
SIM_EXECUTABLE = HOME_DIR + "/bench/simulation/build/main"
DEISA_PATH = HOME_DIR + "/bench/deisa/"

ANALYTICS_PY_FILE = HOME_DIR + "/bench/in-situ/bench_deisa.py"

# must be in the same directory as the script/notebook
SCHEDULER_FILE = HOME_DIR + "/bench/experiment/scheduler.json"

OUTPUT_DIR = HOME_DIR + "/bench/experiment/"

# the total number of nodes needs to be THE SAME as the total number of workers passed in the analytics script
DASK_WORKERS_PER_NODE = 1
TOTAL_DASK_WORKERS = 2


def get_configs(config_file):
    """ 
    Get configs from a .ini file.

    Arguments:
        config_file (str): Path to the .ini configuration file.
    """
    import configparser

    config = configparser.ConfigParser()
    config.read(config_file)

    # Assuming the .ini file has sections and keys
    # Example: [section_name] key_name = value
    configs = {}
    for section in config.sections():
        for key, value in config.items(section):
            configs[key] = value

    return configs

#############################################
#             Alloc the nodes
#############################################

configs = get_configs(SIMULATION_INI)

nb_reserved_nodes = 2 + 1 # execution nodes + 1 head node

jobs = execo_g5k.oarsub(
    [
        (
            execo_g5k.OarSubmission(f"nodes={nb_reserved_nodes}", walltime=60*60),
            "grenoble",
        )
    ]
)

job_id, site = jobs[0]
print(f"Job {job_id} reserved on site {site}")

nodes = execo_g5k.oar.get_oar_job_nodes(job_id, site)
head_node, nodes = nodes[0], nodes[1:]

print(f"Head node: {head_node}")
print(f"Other nodes: {nodes}")


cores_per_node = execo_g5k.get_host_attributes(head_node)["architecture"]["nb_cores"]
total_simulation_cores = cores_per_node * len(nodes)

print(f"Total simulation cores: {total_simulation_cores}")


import socket

head_node_ip = socket.gethostbyname(head_node.address)

nodes_ips = []
for node in nodes:
    nodes_ips.append(socket.gethostbyname(node.address))
print(f"Head node IP: {head_node_ip}")
print(f"Other nodes IPs: {nodes_ips}")

try:

    ##########################################################
    #                   RUNNING SCHEDULER
    ##########################################################
    # Sending the commands for head node

    print("Initializing the scheduler...")

    if os.path.exists(SCHEDULER_FILE):
        os.remove(SCHEDULER_FILE)

    #redirecting the output to a file
    scheduler_cmd = (
        f"dask scheduler "
        # f"--host {head_node.address} "
        f"--scheduler-file {SCHEDULER_FILE} "
        f"> {OUTPUT_DIR}scheduler.e 2>&1; "
        "sync"
    )

    scheduler_process = execo.SshProcess(
        f'singularity exec {PATH_TO_SIF_FILE} bash -c "{scheduler_cmd}"',
        head_node,
    )
    scheduler_process.start()

    # Wait for the scheduler to start by checking the scheduler file
    while not os.path.exists(SCHEDULER_FILE):
        time.sleep(1)

    print("Scheduler started!")

    ##########################################################
    #                   RUNNING WORKERS
    ##########################################################

    print("Initializing the workers...")

    worker_cmd = (
        f"dask worker "
        f"tcp://{head_node_ip}:8786 "
        # f"--dashboard-address {head_node.address}:8787 "
        f"--nworkers {DASK_WORKERS_PER_NODE} "
        "--nthreads 1 "
        "--local-directory /tmp "
        f"--scheduler-file {SCHEDULER_FILE} "
        f"> {OUTPUT_DIR}worker.e 2>&1"
    )

    # for node in nodes:
        # redirecting the output to a file
    for node in nodes:
        worker_process = execo.SshProcess(
            f'singularity exec {PATH_TO_SIF_FILE} bash -c "{worker_cmd}"',
            node,
        )
        worker_process.start()

    print("Workers started!")


    ##########################################################
    #                   RUNNING ANALYTICS
    ##########################################################

    # python3 $OPWD/in-situ/bench_deisa.py $NDASKWORKERS $SCHEFILE 2>analytics.e&

    print("Initializing the analytics...")

    py_cmd = (
        'export PYTHONPATH=/home/lmascare/bench/deisa/:$PYTHONPATH; '
        f'python3 {ANALYTICS_PY_FILE} {TOTAL_DASK_WORKERS} {SCHEDULER_FILE} > {OUTPUT_DIR}analytics.e 2>&1'
    )
    analytics_cmd = (
        # 'hostname'
        f'singularity exec {PATH_TO_SIF_FILE} bash -c "{py_cmd}"'

    )
    print("Analytics command:")
    print(analytics_cmd)

    analytics_process = execo.SshProcess(
        analytics_cmd,
        head_node,
    )
    analytics_process.start()
    # analytics_process.wait()

    print("Analytics started!")


    ##########################################################
    #                   RUNNING SIMULATION
    ##########################################################

    print("Initializing the simulation...")

    # Starting the simulation 32 - 30 for sim and 2 for dask 

    mx = int(configs["mx"])
    my = int(configs["my"])
    mz = int(configs["mz"])

    MPI_NP = mx * my * mz

    print(f"Running simulation with {MPI_NP} MPI processes")

    host_list = ",".join([f"{node.address}:{cores_per_node}" for node in nodes])
    # host_list = ",".join([f"{node.address}" for node in nodes])
    simulation_cmd = (
        f'export PYTHONPATH=/home/lmascare/bench/deisa/:$PYTHONPATH; '
        f'pdirun {SIM_EXECUTABLE} {SIMULATION_INI} {PDI_DEISA_YML} --kokkos-map-device-id-by=mpi_rank > {OUTPUT_DIR}simulation.e 2>&1'
    )

    # Build the command with two singularity exec calls:
    mpi_cmd = (
        'export OMP_NUM_THREADS=2; '
        'export OMP_PROC_BIND=spread; '
        'export OMP_PLACES=threads; '
        f"mpirun -np {MPI_NP} "
        f"--map-by slot "
        f"--host {host_list} "
        f'singularity exec {PATH_TO_SIF_FILE} bash -c "{simulation_cmd}"'
    )

    print("Simulation command:")
    print(mpi_cmd)
    mpi_process = execo.SshProcess(
        mpi_cmd,
        head_node,
    )
    mpi_process.start()

    print("Analytics started!")

    print("Waiting for the simulation to finish...")
    mpi_process.wait()
    print("Simulation finished!")
    # Wait for the analytics to finish
    print("Waiting for the analytics to finish...")
    analytics_process.wait()
    print("Analytics finished!")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Clean up the job
    execo_g5k.oardel(jobs)
    print("Job deleted!")