#!/bin/bash

cleanup() {
    echo -e "\nCtrl+C detected! Terminating all experiments..."
    pkill -P $$  # Kill all child processes of this script
    exit 1
}

trap cleanup SIGINT

BASE_SCRIPT="python run_experiment.py"
BASE_PD="/home/lmascare/bench/experiment_code/strong"
BASE_SI="$BASE_PD"
NAME="strong_$(date +%s)"
DW=1

BASE_TIME=6000 # 1 hour in seconds
# Keeps last value if no argument is provided
if [ -n "$1" ]; then
    BASE_TIME=$1
fi

NODES=1
PROBLEM_SIZE=0

MPI_PROCESSES=(32)
if [ -n "$2" ]; then
    IFS=',' read -r -a MPI_PROCESSES <<< "$2"
fi



for NP in "${MPI_PROCESSES[@]}"; do
    OMP_THREADS=1

    SI_PATH="${BASE_SI}/${NODES}/strong_${NODES}.ini"
    PD_PATH="${BASE_PD}/${NODES}/io_deisa.yml"

    $BASE_SCRIPT \
        -n $((NODES + 1)) \
        -np $NP \
        -ps $PROBLEM_SIZE \
        -nm "$NAME" \
        -t $BASE_TIME \
        -dw $DW \
        -omp_t $OMP_THREADS \
        -m \
        & \

    sleep 1  # Small delay to avoid collisions
done

wait
echo "All experiments completed."
