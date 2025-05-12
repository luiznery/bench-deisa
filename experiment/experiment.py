"""
This code should be execute from the root of the project.
All paths should be absolute paths.
"""

import execo
import execo_g5k
import execo_engine
import time
import os

# this will be /home/lmascare
HOME_DIR = os.path.expanduser("~")

PATH_TO_SIF_FILE = HOME_DIR + "/bench/docker/images/bench.sif"

SIMULATION_INI = HOME_DIR + "/bench/simulation/setup.ini"
PDI_DEISA_YML = HOME_DIR + "/bench/simulation/io_deisa.yml"
SIM_EXECUTABLE = HOME_DIR + "/bench/simulation/build/main"
DEISA_PATH = HOME_DIR + "/bench/deisa/"

SCHEDULER_FILE = HOME_DIR + "/bench/experiment/scheduler.json"

OUTPUT_DIR = HOME_DIR + "/bench/experiment/output/"


def run_experiment(nb_reserved_nodes):

    # Getting the nodes
    
    jobs = execo_g5k.oarsub(
        [
            (
                execo_g5k.OarSubmission(f"nodes={nb_reserved_nodes}", walltime=5*60),
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


    ##########################################################
    #                   RUNNING SCHEDULER
    ##########################################################
    # Sending the commands for head node
    
    if os.path.exists(SCHEDULER_FILE):
        os.remove(SCHEDULER_FILE)

    #redirecting the output to a file
    head_node_cmd = (
        f"dask scheduler --scheduler-file {SCHEDULER_FILE}"
    )
    head_node_process = execo.SshProcess(
        f'singularity exec {PATH_TO_SIF_FILE} bash -c "{head_node_cmd}"',
        head_node,
    )
    head_node_process.start()

    print()
    print("#"*20)
    print("Output:")
    print(head_node_process.stdout)
    print("-"*20)
    print("Error:")
    print(head_node_process.stderr)
    print()
    print("#"*20)

    ##########################################################
    #                   RUNNING SIMULATION
    ##########################################################
    
    # Starting the simulation 32 - 30 for sim and 2 for dask 


# """
# export OMP_NUM_THREADS=2; \
# export OMP_PROC_BIND=spread; \
# export OMP_PLACES=threads; \
# pdirun /home/lmascare/bench/simulation/build/main /home/lmascare/bench/simulation/setup.ini /home/lmascare/bench/simulation/io_deisa.yml > simulation_output.log 2>&1"

# """
    host_list = ",".join([f"{node.address}:{cores_per_node}" for node in nodes])
    simulation_cmd = (
        'export OMP_NUM_THREADS=2; '
        'export OMP_PROC_BIND=spread; '
        'export OMP_PLACES=threads; '
        f'pdirun {SIM_EXECUTABLE} {SIMULATION_INI} {PDI_DEISA_YML} > simulation_output.log 2>&1'
    )

    # Build the command with two singularity exec calls:
    mpi_cmd = (
        f'singularity exec {PATH_TO_SIF_FILE} bash -c "'
        f"mpirun -np 5 "#{total_simulation_cores} "
        f"--host {host_list} "
        f'singularity exec {PATH_TO_SIF_FILE} bash -c \'{simulation_cmd}\'"'
    )

    print("Simulation command:")
    print(mpi_cmd)
    mpi_process = execo.SshProcess(
        mpi_cmd,
        nodes[0],
    )
    mpi_process.start()

    mpi_process.wait()

    print("Output:")
    print(mpi_process.stdout)
    print("-"*20)
    print("Error:")
    print(mpi_process.stderr)
    print()
    print("#"*20)


    
    
    #Working a bit - small bug in deisa, i guess
    """
    singularity exec docker/images/bench.sif bash -l -c "mpirun -np 4 --host dahu-12.grenoble.grid5000.fr:32,dahu-21.grenoble.grid5000.fr:32 bash -l -c 'pdirun ~/bench/simulation/build/main ~/bench/simulation/setup.ini ~/bench/simulation/io_deisa.yml' "
    """

    # I guess we dont need to execute singularity 2 times
    """"
    singularity exec docker/images/bench.sif bash -l -c "mpirun -np 4 --host dahu-12.grenoble.grid5000.fr:32,dahu-21.grenoble.grid5000.fr:32 bash -l -c 'which pdirun' "
    """






    # simulation_node_cmd = f"""mpirun --host {node_i.address} bash -c " """

    # print(simulation_node_cmd)




    
    # configs = get_configs("simulation/setup.ini")
    # NMPI = int(configs["mx"]) * int(configs["my"]) * int(configs["mz"])
    # pre_cmd = f"export PYTHONPATH={DEISA_PATH}"
    
    
    
    # # Optionally, load additional simulation configuration from an ini file.
    # configs = get_configs(SIM_SETUP_INI)
    # NMPI = int(configs["mx"]) * int(configs["my"]) * int(configs["mz"])
    # print(f"Simulation configuration NMPI (grid size product): {NMPI}")
    
    # # Build the complete MPI command.
    # # You can adjust flags (e.g., --report-bindings) as necessary.
    # mpi_cmd = (
    #     f"mpirun --report-bindings -np {total_simulation_cores} "
    #     f"--host {host_list} "
    #     f"singularity exec {PATH_TO_SIF_FILE} {SIM_EXECUTABLE}"
    # )








    
    # host = node_i.address
    # cmd_to_run_simulation = (
    #     f" mpirun --host {} -np {NMPI} pdirun "
    #     f"{SIM_EXECUTABLE} {SIMULATION_INI} {PDI_DEISA_YML} --kokkos-map-device-id-by=mpi_rank "
    # )

    # new_process = execo.SshProcess(
    #     f'singularity exec {PATH_TO_SIF_FILE} bash -c "{pre_cmd} && {cmd_to_run_simulation}"',
    #     node_i
    # )
    # new_process.start()
    # node_processes.append(new_process)

    # time.sleep(1)

    # for process_it in node_processes:
    #     print("Process Output:")
    #     print(process_it.stdout)

    #     print()
    #     print("Process Error:")
    #     print(process_it.stderr)
    
    #time.sleep(1)

    #print("Jobs from my user:")
    #print(execo_g5k.get_current_oar_jobs())

    #print("Waiting for the execution to finish...")
    #head_node_process.wait()
    
    #print("#"*50);print("Command output:")
    #print("#"*50);print(head_node_process.stdout);print("#"*50)
    #print("Command error output:")
    #print("#"*50);print(head_node_process.stderr);print("#"*50)


""" 
Get configs from a .ini file.

Arguments:
    config_file (str): Path to the .ini configuration file.
"""
def get_configs(config_file):
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


if __name__ == "__main__":
    configs = get_configs("simulation/setup.ini")
    run_experiment(3)
    
