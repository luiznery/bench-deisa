#!/bin/bash

BASE_SCRIPT="python run_experiment_strong.py"

DW=1

# get name as arg
if [ -n "$1" ]; then
    PREFIX_NAME="$1"
fi
NAME="${PREFIX_NAME}_$(date +%s)"

if [ -n "$2" ]; then
    BASE_TIME=$2
fi

if [ -n "$3" ]; then
    MPI_PROCESSES=$3
fi

if [ -n "$4" ]; then
    NODES=$4
fi

OMP_THREADS=1

$BASE_SCRIPT \
    -n $((NODES + 1)) \
    -np $MPI_PROCESSES \
    -nm "$NAME" \
    -t $BASE_TIME \
    -dw $DW \
    -omp_t $OMP_THREADS \
    --problem_size 128,64,32 \
    -m 