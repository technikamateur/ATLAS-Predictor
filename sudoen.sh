sh -c 'echo -1 >/proc/sys/kernel/perf_event_paranoid'
chmod +r /sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/energy_uj
chmod +r /sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/intel-rapl:0:0/energy_uj
chmod +r /sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/max_energy_range_uj
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export LD_LIBRARY_PATH=$SCRIPT_DIR