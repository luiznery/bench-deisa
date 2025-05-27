import execo
import execo_g5k
import time
import os
import configparser
import re

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

def extract_scheduler_path(filename):
    """
    Reads the given file and returns the path following 'scheduler_info:'.
    Returns None if no match is found.
    """
    pattern = re.compile(r'scheduler_info:\s+(\S+)')
    
    with open(filename, 'r') as file:
        for line in file:
            match = pattern.search(line)
            if match:
                return match.group(1)
    
    return None  # if no match is found


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
        f'python3 {analytics_py_file} {total_dask_workers} {scheduler_file} {output_dir} > {output_dir}analytics.e 2>&1'
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
    """
    Run the simulation in the given nodes.

    Arguments:
        head_node: The head node where the simulation will be run.
        nodes (list): List of nodes where the simulation will be run.
        mpi_np (int): Number of MPI processes.
        cores_per_node (int): Number of cores per node.
        deisa_path (str): Path to the DEISA directory.
        sim_executable (str): Path to the simulation executable.
        simulation_ini (str): Path to the simulation ini file.
        pdi_deisa_yml (str): Path to the PDI DEISA YAML file.
        output_dir (str): Directory where the output files will be saved.
        path_to_sif_file (str): Path to the Singularity image file.
    """
    
    host_list = ",".join([f"{node.address}" for node in nodes])
    # host_list = ",".join([f"{node.address}:{cores_per_node}" for node in nodes])
    # host_list = ",".join([f"{node.address}" for node in nodes])

    simulation_cmd = (
        'export OMP_NUM_THREADS=2; '
        'export OMP_PROC_BIND=spread; '
        'export OMP_PLACES=threads; '
        f'export PYTHONPATH={deisa_path}:$PYTHONPATH; '
        f'pdirun {sim_executable} {simulation_ini} {pdi_deisa_yml} --kokkos-map-device-id-by=mpi_rank '
    )

    # Build the command with two singularity exec calls:
    mpi_cmd = (
        'export OMP_NUM_THREADS=2; '
        'export OMP_PROC_BIND=spread; '
        'export OMP_PLACES=threads; '
        'mpirun '
        f"--host {host_list} "
        f"--map-by node "
        f"-np {mpi_np} "
        f'singularity exec {path_to_sif_file} bash -c "{simulation_cmd}" '
        f'> {output_dir}simulation.e 2>&1'
    )

    mpi_process = execo.SshProcess(
        mpi_cmd,
        head_node,
    )
    mpi_process.start()

    return mpi_process