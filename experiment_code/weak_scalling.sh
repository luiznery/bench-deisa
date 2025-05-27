#!/bin/bash

cleanup() {
    echo -e "\nCtrl+C detected! Terminating all experiments..."
    pkill -P $$  # Kill all child processes of this script
    exit 1
}

trap cleanup SIGINT

BASE_SCRIPT="python run_experiment.py"
BASE_PD="/home/lmascare/bench/experiment_code/weak"
BASE_SI="$BASE_PD"
NAME="weak_$(date +%s)"
DW=1

BASE_TIME=6000 # 1 hour in seconds
# Keeps last value if no argument is provided
if [ -n "$1" ]; then
    BASE_TIME=$1
fi

NODE_COUNTS=(4)

PROBLEM_SIZES=(1 2)

for PROBLEM in "${PROBLEM_SIZES[@]}"; do
    SI_PATH="${BASE_SI}/${PROBLEM}/weak_${PROBLEM}.ini"
    PD_PATH="${BASE_PD}/${PROBLEM}/io_deisa.yml"

    $BASE_SCRIPT \
        -n 17 \
        -si "$SI_PATH" \
        -pd "$PD_PATH" \
        -nm "$NAME" \
        -t $BASE_TIME \
        -dw $DW &

    sleep 1  # Small delay to avoid collisions
done

wait
echo "All experiments completed."
