FROM ubuntu:24.04

# Update package lists and install required dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
  wget \
  python3-pip \
  curl \
  gfortran \
  build-essential \
  libopenmpi-dev \
  cmake \
  libkokkos-dev \
  libyaml-dev \
  pkg-config \
  nodejs \
  npm

# Set python alternative
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Install Pyright globally via npm
RUN npm install -g pyright

# Install PDI
ENV PDIV=1.8.3
ENV PDI_DIR=/pdi
ENV PDI_URL=https://github.com/pdidev/pdi/archive/refs/tags/$PDIV.tar.gz

WORKDIR /pdi

# Download, extract, configure and build PDI with DEISA and PyCall plugins
RUN curl -L $PDI_URL | tar --strip-components=1 -xzv && \
    cmake -DBUILD_DEISA_PLUGIN=ON \
          -DBUILD_PYTHON=ON \
          -DBUILD_PYCALL_PLUGIN=ON \
          -DCMAKE_INSTALL_PREFIX=./install \
          -S . -B build

RUN make -C build -j $(nproc)
RUN make install -C build 

# Update environment variables
ENV PATH="/pdi/install/bin:${PATH}"
ENV LD_LIBRARY_PATH=/pdi/install/lib

WORKDIR /venv/
COPY requirements.txt /venv/

# Install Python packages from requirements.txt (make sure it includes distributed, dask, bokeh, pytest, etc.)
RUN pip install -r requirements.txt --break-system-packages
