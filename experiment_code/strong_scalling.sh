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
BASE_TIME=600
DW=1

NODE_COUNTS=(16 8 4 2 1)

for NODES in "${NODE_COUNTS[@]}"; do
    SI_PATH="${BASE_SI}/${NODES}/strong_${NODES}.ini"
    PD_PATH="${BASE_PD}/${NODES}/io_deisa.yml"

    $BASE_SCRIPT \
        -nb $((NODES + 1)) \
        -si "$SI_PATH" \
        -pd "$PD_PATH" \
        -nm "$NAME" \
        -t $BASE_TIME \
        -dw $DW &

    sleep 1  # Small delay to avoid collisions
done

wait
echo "All experiments completed."
