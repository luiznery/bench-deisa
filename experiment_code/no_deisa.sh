#!/bin/bash

cleanup() {
    echo -e "\nCtrl+C detected! Terminating all experiments..."
    pkill -P $$  # Kill all child processes of this script
    exit 1
}

trap cleanup SIGINT

BASE_SCRIPT="python run_experiment_no_deisa.py"
BASE_PD="/home/lmascare/bench/experiment_code/strong"
BASE_SI="$BASE_PD"

DW=1

if [ -n "$1" ]; then
    NAME="$1"
fi
NAME="${NAME}_nodeisa_$(date +%s)"


BASE_TIME=6000 
# Keeps last value if no argument is provided
if [ -n "$2" ]; then
    BASE_TIME=$2
fi

NODES=1
if [ -n "$3" ]; then
    NODES=$3
fi

PROBLEM_SIZE=0
if [ -n "$4" ]; then
    PROBLEM_SIZE=$4
fi

MPI_PROCESSES=32
if [ -n "$5" ]; then
    MPI_PROCESSES=$5
fi

OMP_THREADS=1

$BASE_SCRIPT \
    -n $((NODES + 1)) \
    -np $MPI_PROCESSES \
    -ps $PROBLEM_SIZE \
    -nm "$NAME" \
    -t $BASE_TIME \
    -omp_t $OMP_THREADS \
    -m \
    & \



wait
echo "All experiments completed."
