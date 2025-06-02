[Analytics] parameters: dask workers - 3, schedueler_file - /home/lmascare/bench/experiment_result/weak_1748763071:4:16:5/scheduler.json, output_dir - /home/lmascare/bench/experiment_result/weak_1748763071:4:16:5/
[Analytics] deisa initialized
[Analytics] getting client
[Analytics] getting deisa array
[Analytics] arrays received
[Analytics] X-dim = 4096
[Analytics] Y-dim = 2048
[Analytics] Z-dim = 32
[Analytics] getting slice at z = 10
[Analytics] starting computation at 1748763360.3138745
Traceback (most recent call last):
  File "/home/lmascare/bench/in-situ/bench_deisa.py", line 120, in <module>
    res2 = ekin_persisted.compute()
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/dask/base.py", line 376, in compute
    (result,) = compute(self, traverse=False, **kwargs)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/dask/base.py", line 662, in compute
    results = schedule(dsk, keys, **kwargs)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/lmascare/bench/deisa/deisa/deisa.py", line 554, in deisa_ext_task
    return f.result()  # type: ignore
^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/distributed/client.py", line 2235, in _gather
    raise exc
^^^
concurrent.futures._base.CancelledError: ndarray-0a05e7359c50bf20945132c2b670d4a4
