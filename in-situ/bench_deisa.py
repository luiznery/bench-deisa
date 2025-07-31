###################################################################################################
# Copyright (c) 2020-2022 Centre national de la recherche scientifique (CNRS)
# Copyright (c) 2020-2022 Commissariat a l'énergie atomique et aux énergies alternatives (CEA)
# Copyright (c) 2020-2022 Institut national de recherche en informatique et en automatique (Inria)
# Copyright (c) 2020-2022 Université Paris-Saclay
# Copyright (c) 2020-2022 Université de Versailles Saint-Quentin-en-Yvelines
#
# SPDX-License-Identifier: MIT
#
###################################################################################################

from deisa import Deisa
import os
import sys
import dask
import dask.array as da
from dask.distributed import performance_report
import time
from distributed.diagnostics import MemorySampler
from pprint import pformat
import matplotlib.pyplot as plt

# Initialize Deisa
if len(sys.argv) < 4:
    raise Exception("[Analytics] Number of dask workers not set. Usage: python3 bench_deisa.py <n_dask_workers> <scheduler_file_name> <output_dir>")
else:
    nb_workers = int(sys.argv[1])
    scheduler_file_name=str(sys.argv[2])
    output_dir = str(sys.argv[3])
    print(f"[Analytics] parameters: dask workers - {nb_workers}, schedueler_file - {scheduler_file_name}, output_dir - {output_dir}", flush=True)

deisa = Deisa(scheduler_file_name=scheduler_file_name, 
              nb_workers=nb_workers,
              use_ucx=False)

print("[Analytics] deisa initialized",flush=True)

print("[Analytics] getting client", flush=True)
client = deisa.get_client()
# Get client
print("[Analytics] getting deisa array", flush=True)
arrays = deisa.get_deisa_arrays()

print("[Analytics] arrays received", flush=True)

# Select data
gt = arrays["global_t"][:, :, :, :, :]
mx = len(gt[0, 0, 0, 0, :])
my = len(gt[0, 0, 0, :, 0])
mz = len(gt[0, 0, :, 0, 0])

mt = len(gt[:, 0, 0, 0, 0])

assert isinstance(mx, int)
assert isinstance(my, int)
assert isinstance(mz, int)
print("[Analytics] X-dim =", mx, flush=True)
print("[Analytics] Y-dim =", my, flush=True)
print("[Analytics] Z-dim =", mz, flush=True)
z_pos = int(mz / 3)
print("[Analytics] getting slice at z =", z_pos, flush=True)

print("[Analytics] arrays global_t shape:", gt.shape, flush=True)

# Check contract
# arrays.check_contract()

# Construct a lazy task graph
id = 0
iu = 2
iv = 3
iw = 4
ms = MemorySampler()

with performance_report(filename=f"{output_dir}dask-report.html"), dask.config.set(
    array_optimize=None
), ms.sample("collection 1"):
    print(f"[Analytics] starting computation at {time.time()}", flush=True)
    
    def Derivee(F, dx):
        """
        First derivative along axis=0 (time) of a 3D field F[t, x, y]:
        F  : dask array of shape (nt, nx, ny)
        dx : spacing along that axis
        Returns a dask array of shape (nt-4, nx, ny).
        """
        c0 = 2.0 / 3.0
        return c0/dx * (
            F[3:-1, :, :] - F[1:-3, :, :]
            - (F[4:, :, :] - F[:-4, :, :]) / 8.0
        )

    # print(f"[Analytics] Derivee function defined at {time.time()}", flush=True)
    # deriv = Derivee(slice, dx=1.0)
    # mean_deriv = deriv.mean()
    # print(f"[Analytics] Derivative computed at {time.time()}", flush=True)
    

    # print(f"[Analytics] slice shape: {slice.shape}", flush=True)
    ts = time.time()
    # sum over the iterations and compute the mean over axis y
    sum_over_iterations = gt[:, 0, z_pos, :, 0].sum(axis=0).mean(axis=0)
    res1 = sum_over_iterations.compute()
    te = time.time()
    print(f"[Analytics] time ekin: {te-ts}")
    print(f"[Analytics] res1: {res1}", flush=True)

    ts = time.time()
    # sum over the iterations
    # res2 = gt[:, 0, z_pos, 0, 0].compute()
    te = time.time()
    print(f"[Analytics] time sum over xy: {te-ts}")
    # print(f"[Analytics] sum over iterations: {res2}", flush=True)

    ts = time.time()
    # res4 = fourier_amplitudes.compute()
    te = time.time()
    print(f"[Analytics] time fourier: {te-ts}")


# diagnostics info
l1 = client.run(lambda dask_worker: dask_worker.transfer_outgoing_log)
l2 = client.run(lambda dask_worker: dask_worker.transfer_incoming_log)

with open(f"{output_dir}outgoing.txt", "w") as f1, open(f"{output_dir}incoming.txt", "w") as f2, open(
    f"{output_dir}results.txt", "w"
) as f3:
    f1.write(pformat(l1))
    f2.write(pformat(l2))
    # print(f"{res2=}", file=f3)

res = ms.plot(align=True)
if isinstance(res, plt.Axes):
    res = res.get_figure()

res.savefig(f"{output_dir}plot.png")

print("[Analytics] Done ", flush=True)
# deisa.wait_for_last_bridge_and_shutdown()
client.close()
