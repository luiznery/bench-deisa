import execo_g5k
import os
import socket
import time
import math

from experiment import *

# this will be /home/lmascare
HOME_DIR = os.path.expanduser("~")

PATH_TO_SIF_FILE = HOME_DIR + "/bench/docker/images/bench.sif"
SIM_EXECUTABLE = HOME_DIR + "/bench/simulation/build/main"
DEISA_PATH = HOME_DIR + "/bench/deisa/"
ANALYTICS_PY_FILE = HOME_DIR + "/bench/in-situ/bench_deisa.py"
SCHEDULER_PATH = HOME_DIR + "/bench/experiment_result/"
DEISA_PATH = HOME_DIR + "/bench/deisa/"
PATH_TO_MONITOR_FILE = HOME_DIR + "/bench/experiment_code/monitor.py"


def run_experiment(reserved_nodes: int, s_ini_file: str, pdi_deisa_yml: str, name: str, walltime=10*60, 
                   omp_num_threads=1,monitoring=False):
    """
    Run experiment with the given parameters.

    Arguments:
        reserved_nodes (int): Total number of nodes to reserve, including the head node.
        s_ini_file (str): Path to the simulation ini file.
        pdi_deisa_yml (str): Path to the PDI DEISA YAML file.
        name (str): Name of the experiment.
        walltime (int): Walltime for the reservation in seconds.
    """
    if reserved_nodes < 2:
        raise ValueError("reserved_nodes must be greater than or equal to 2")
    
    if walltime <= 0:
        raise ValueError("walltime must be greater than 0")

    try:
        # Alloc the nodes
        jobs = alloc_nodes(reserved_nodes, walltime)
        job_id, site = jobs[0]

        print(f"[{exp_name}] Job {job_id} reserved on site {site}")

        nodes = execo_g5k.oar.get_oar_job_nodes(job_id, site)
        head_node, nodes = nodes[0], nodes[1:]

        print(f"[{exp_name}] Head node: {head_node}")
        print(f"[{exp_name}] Other nodes: {nodes}")

        cores_per_node = execo_g5k.get_host_attributes(head_node)["architecture"]["nb_cores"]
        total_simulation_cores = cores_per_node * len(nodes)

        # print(f"[{exp_name}] Total simulation cores: {total_simulation_cores}")

        print(f"[{exp_name}] OMP_NUM_THREADS set to {omp_num_threads}")
        
        # Run monitoring if enabled
        if monitoring:
            print(f"[{exp_name}] Monitoring enabled. Starting monitoring process...")
            monitor_processes = run_monitor([head_node]+nodes, output_dir, 1, PATH_TO_SIF_FILE, PATH_TO_MONITOR_FILE)
            print(f"[{exp_name}] Monitoring process started!")

        # Read the simulation configuration file
        configs = get_configs(s_ini_file)

        # Getting the ip addresses of the nodes
        head_node_ip = socket.gethostbyname(head_node.address)
        nodes_ips = []
        for node in nodes:
            nodes_ips.append(socket.gethostbyname(node.address))
        print(f"[{exp_name}] Head node IP: {head_node_ip}")
        print(f"[{exp_name}] Other nodes IPs: {nodes_ips}")

        # Running the simulation
        print(f"[{exp_name}] Initializing the simulation...")
        mx = int(configs["mx"])
        my = int(configs["my"])
        mz = int(configs["mz"])
        mpi_np = mx * my * mz
        assert mpi_np <= total_simulation_cores, "mpi_np must be less than or equal to total_simulation_cores"
        print(f"[{exp_name}] Running simulation with {mpi_np} MPI processes")
        mpi_process = run_simulation(head_node, nodes, mpi_np, cores_per_node, DEISA_PATH, SIM_EXECUTABLE, s_ini_file, 
                            pdi_deisa_yml, output_dir, PATH_TO_SIF_FILE, omp_num_threads)
        print(f"[{exp_name}] Simulation started!")

        # Waiting for everything to finish
        print(f"[{exp_name}] Waiting for the simulation to finish...")
        mpi_process.wait()
        print(f"[{exp_name}] Simulation finished!")
        print(f"[{exp_name}] Waiting for the analytics to finish...")

        if monitoring:
            #kill the monitoring processes
            print(f"[{exp_name}] Stopping monitoring processes...")
            for monitor_process in monitor_processes:
                monitor_process.kill()
            print(f"[{exp_name}] Monitoring processes stopped!")

        mpi_process_stats = mpi_process.stats()
        with open(output_dir + "mpi_process_stats.txt", "w") as f_mpi:
            f_mpi.write(str(mpi_process_stats))

    except Exception as e:
        print(f"[{exp_name}] An error occurred: {e}")

    finally:
        # Delete the job
        execo_g5k.oardel(jobs)
        print(f"[{exp_name}] Job deleted!")


def produce_config_files(output_dir: str, mpi_np: int, problem_size: int):
    if problem_size < 0:
        raise ValueError("problem_size must be greater than or equal to 1")
    # base values
    nx=32
    ny=32
    nz=32
    for i in range(problem_size):
        if i%2 == 0:
            nx *= 2
        else:
            ny *= 2

    mx = 1
    my = 1
    mz = 1
    log_n_mpi = math.log2(mpi_np)
    if not log_n_mpi.is_integer():
        raise ValueError("mpi_np must be a power of 2")
    log_n_mpi = int(log_n_mpi)
    for i in range(log_n_mpi):
        if i%2 == 0:
            mx *= 2
        else:
            my *= 2

    #write the simulation ini file in output_dir
    simulation_ini_file = output_dir + f"{mpi_np}_{problem_size}.ini"
    T_END_VAR = 10
    N_STEP_MAX_VAR=500
    #read the template ini file
    template_ini_file = HOME_DIR + "/bench/experiment_code/templates/template.ini"
    with open(template_ini_file, "r") as f:
        template_content = f.read()
    #replace the variables in the template with the values
    template_content = template_content.replace("<T_END_VAR>", str(int(T_END_VAR)))
    template_content = template_content.replace("<N_STEP_MAX_VAR>", str(int(N_STEP_MAX_VAR)))
    template_content = template_content.replace("<NX_VAR>", str(int(nx)))
    template_content = template_content.replace("<NY_VAR>", str(int(ny)))
    template_content = template_content.replace("<NZ_VAR>", str(int(nz)))
    template_content = template_content.replace("<MX_VAR>", str(int(mx)))
    template_content = template_content.replace("<MY_VAR>", str(int(my)))
    template_content = template_content.replace("<MZ_VAR>", str(int(mz)))
    with open(simulation_ini_file, "w") as f:
        f.write(template_content)
    
    #write the PDI DEISA YAML file in output_dir
    pdi_deisa_yml_file = output_dir + f"{mpi_np}_{problem_size}.yml"
    #read the template yaml file
    template_yml_file = HOME_DIR + "/bench/experiment_code/templates/io_NO_deisa.yml"
    with open(template_yml_file, "r") as f:
        template_content = f.read()
    with open(pdi_deisa_yml_file, "w") as f:
        f.write(template_content)
    
    return simulation_ini_file, pdi_deisa_yml_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run strong scaling experiment.")
    parser.add_argument("--reserved_nodes","-n", type=int, required=True, 
                        help="Number of reserved nodes (including head node).")
    parser.add_argument("--mpi_np", "-np", type=int, required=True,
                        help="Number of MPI processes to run in the simulation.")
    parser.add_argument("--problem_size", "-ps", type=int, required=True,
                        help="Problem size for the simulation.")
    parser.add_argument("--name", "-nm", type=str, required=True, help="Name of the experiment.")
    parser.add_argument("--walltime", "-t",type=int, default=10*60, help="Walltime in seconds (default: 600).")
    parser.add_argument("--monitoring", "-m", action="store_true", 
                        help="Enable monitoring of the experiment (default: False).")
    parser.add_argument("--omp_num_threads", "-omp_t", type=int, default=1,
                        help="Number of OpenMP threads to use in the simulation (default: 1).")
    args = parser.parse_args()

    exp_name = f"{args.name}:{args.reserved_nodes}:{args.mpi_np}:{args.problem_size}"
    output_dir = HOME_DIR + f"/bench/experiment_result/{exp_name}/"
    if not os.path.exists(output_dir): #create output directory if it does not exist
        os.makedirs(output_dir)
    else:
        raise FileExistsError(
            f"Output directory {output_dir} already exists. Please remove it or choose a different name.")
    
    print(f"[{exp_name}] Reserved Nodes: {args.reserved_nodes}")
    print(f"[{exp_name}] MPI NP: {args.mpi_np}")
    print(f"[{exp_name}] Problem Size: {args.problem_size}")
    
    #Create the simulation ini file and PDI DEISA YAML file
    simulation_ini_file,pdi_deisa_yml_file = produce_config_files(output_dir, args.mpi_np, args.problem_size)

    run_experiment(reserved_nodes=args.reserved_nodes, 
                   s_ini_file=simulation_ini_file,
                   pdi_deisa_yml=pdi_deisa_yml_file,
                   name=args.name,
                   walltime=args.walltime,
                   omp_num_threads=args.omp_num_threads,
                   monitoring=args.monitoring)