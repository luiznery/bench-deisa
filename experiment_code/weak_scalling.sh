#!/bin/bash

cleanup() {
    echo -e "\nCtrl+C detected! Terminating all experiments..."
    pkill -P $$  # Kill all child processes of this script
    exit 1
}

trap cleanup SIGINT

BASE_SCRIPT="python run_experiment.py"
NAME="weak_$(date +%s)"
DW=1

BASE_TIME=6000 # 1 hour in seconds
# Keeps last value if no argument is provided
if [ -n "$1" ]; then
    BASE_TIME=$1
fi

MPI_PROCESSES=32
if [ -n "$2" ]; then
    MPI_PROCESSES=$2
fi

PROBLEM_SIZE=2
if [ -n "$3" ]; then
    PROBLEM_SIZE=$3
fi

NODES=1
if [ -n "$4" ]; then
    NODES=$4
fi

OMP_THREADS=1

$BASE_SCRIPT \
    -n $((NODES + 1)) \
    -np $MPI_PROCESSES \
    -ps $PROBLEM_SIZE \
    -nm "$NAME" \
    -t $BASE_TIME \
    -dw $DW \
    -omp_t $OMP_THREADS \
    -m \
    & \

sleep 1  # Small delay to avoid collisions

wait
echo "All experiments completed."
