#!/bin/bash

#OAR -l host=1
#OAR -l walltime=1:00:00
#OAR -O outputs/OAR_bench_%jobid%.out
#OAR -E outputs/OAR_bench_%jobid%.err

singularity exec ~/bench/docker/images/bench.sif bash ./deisa/compile_deisa.sh

cd ~/bench/deisa/example/experiment
singularity exec ~/bench/docker/images/bench.sif bash ./script.sh