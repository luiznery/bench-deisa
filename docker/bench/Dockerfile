FROM ubuntu:24.04

RUN apt-get update && apt-get upgrade -y && apt-get install -y wget python3-pip curl gfortran build-essential libopenmpi-dev cmake

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Install PDI
ENV PDIV=1.8.3
ENV PDI_DIR=/pdi

ENV PDI_URL=https://github.com/pdidev/pdi/archive/refs/tags/$PDIV.tar.gz

WORKDIR /pdi

RUN curl -L $PDI_URL | tar --strip-components=1 -xzv && cmake -DBUILD_DEISA_PLUGIN=ON \
-DBUILD_PYTHON=ON -DBUILD_PYCALL_PLUGIN=ON -DCMAKE_INSTALL_PREFIX=./install \
-S . -B build

RUN make -C build -j $(nproc)
RUN make install -C build 
ENV PATH="/pdi/install/bin:${PATH}"
ENV LD_LIBRARY_PATH=/pdi/install/lib
# ENV PYTHONPATH=~/bench/deisa/

WORKDIR /venv/
COPY requirements.txt  /venv/

RUN pip install -r requirements.txt --break-system-packages

# Disable Ray's data collection
#RUN ray disable-usage-stats

