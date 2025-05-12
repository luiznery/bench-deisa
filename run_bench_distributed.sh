#!/bin/bash

#OAR -l host=1
#OAR -l walltime=1:00:00
#OAR -O outputs/OAR_bench_%jobid%.out
#OAR -E outputs/OAR_bench_%jobid%.err

cd ~/bench/
singularity exec ~/bench/docker/images/bench.sif bash ./scripts/launch_all.sh

# cd ~/bench/deisa/example/experiment
# singularity exec ~/bench/docker/images/bench.sif bash ./script.sh