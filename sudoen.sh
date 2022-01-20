sh -c 'echo -1 >/proc/sys/kernel/perf_event_paranoid'
chmod +r /sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/energy_uj
chmod +r /sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/intel-rapl:0:0/energy_uj
