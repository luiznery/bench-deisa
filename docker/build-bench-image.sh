# Build docker images
docker build --pull --rm -f 'bench/Dockerfile' -t 'bench:latest' 'bench'

# Export the docker images to a .tar file
docker save bench:latest -o images/bench.tar

# Convert the images to singularity images
singularity build images/bench.sif docker-archive://images/bench.tar
