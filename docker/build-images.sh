# Build docker images
#docker build --pull --rm -f 'docker/analytics/Dockerfile' -t 'bench-analytics:latest' 'docker/analytics'
docker build --pull --rm -f 'docker/simulation/Dockerfile' -t 'bench-simulation:latest' 'docker/simulation'

# Export the docker images to a .tar file
#docker save bench-analytics:latest -o docker/images/bench-analytics.tar
docker save bench-simulation:latest -o docker/images/bench-simulation.tar

# Convert the images to singularity images
#singularity build docker/images/bench-analytics.sif docker-archive://docker/images/bench-analytics.tar
singularity build docker/images/bench-simulation.sif docker-archive://docker/images/bench-simulation.tar
