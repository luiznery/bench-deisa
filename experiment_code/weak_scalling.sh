#!/bin/bash

cleanup() {
    echo -e "\nCtrl+C detected! Terminating all experiments..."
    pkill -P $$  # Kill all child processes of this script
    exit 1
}

trap cleanup SIGINT

BASE_SCRIPT="python strong_scalling.py"
BASE_PD="/home/lmascare/bench/experiment_code/weak"
BASE_SI="$BASE_PD"
NAME="weak_$(date +%s)"
BASE_TIME=900
DW=1

PROBLEM_SIZES=(1 2)

for PROBLEM in "${PROBLEM_SIZES[@]}"; do
    SI_PATH="${BASE_SI}/${PROBLEM}/weak_${PROBLEM}.ini"
    PD_PATH="${BASE_PD}/${PROBLEM}/io_deisa.yml"

    $BASE_SCRIPT \
        -nb 17 \
        -si "$SI_PATH" \
        -pd "$PD_PATH" \
        -nm "$NAME" \
        -t $BASE_TIME \
        -dw $DW &

    sleep 1  # Small delay to avoid collisions
done

wait
echo "All experiments completed."
