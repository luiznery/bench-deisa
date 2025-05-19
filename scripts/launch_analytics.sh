#!/bin/bash

set -xeu

OPWD=$PWD

# set NDASKWORKERS, NMPI, SCHEFILE
source $PWD/scripts/env.sh

EXPERIMENT_DIR=$PWD/experiment
cd $EXPERIMENT_DIR

python3 $OPWD/in-situ/bench_deisa.py $NDASKWORKERS $SCHEFILE 2>analytics.e&

PYTHON_PID=$!

SIM_EXE=$OPWD/simulation/build/main
S_INI=$OPWD/simulation/setup.ini
PDI_DEISA_YML=$OPWD/simulation/io_deisa.yml

# $SIM_EXE $S_INI $IO_DEISA
pdirun mpirun -np $NMPI $SIM_EXE $S_INI $PDI_DEISA_YML --kokkos-map-device-id-by=mpi_rank 

wait $PYTHON_PID
cd $OPWD
set +xeu
