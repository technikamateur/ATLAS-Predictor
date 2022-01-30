import csv
import random
import subprocess


class Benchmark:
    def __init__(self, perf, repetitions, training_percentage):
        self.perf = perf
        self.repetitions = repetitions
        self.time = ["/usr/bin/time", "-f", "%U,%S,%e", "-o", "time.tmp"]
        self.time_format = ["user", "sys", "elapsed"]
        self.training_percentage = training_percentage
        self.sampling = 100

        self.training = dict()
        self.control = dict()
        """
        Stores all results. Format:
        arguments -> list of runs (one element per run)
        one run: [time, {"package": package_energy, "core": core_energy}, perf]
        """
        self.output = dict()

        random.seed()

    def bench(self):
        raise NotImplementedError

    def get_metrics(self):
        raise NotImplementedError

    def run_subprocess(self, element, full_cmd):
        for i in range(self.repetitions):
            # read energy before running
            with open("/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/energy_uj", "r") as package, open(
                    "/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/intel-rapl:0:0/energy_uj", "r") as core:
                package_energy = int(package.readline().rstrip())
                core_energy = int(core.readline().rstrip())
            # execute command
            result = subprocess.run(self.perf + self.time + full_cmd, capture_output=True)
            # read energy again
            with open("/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/energy_uj", "r") as package, open(
                    "/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/intel-rapl:0:0/energy_uj", "r") as core:
                package_energy = int(package.readline().rstrip()) - package_energy
                core_energy = int(core.readline().rstrip()) - core_energy
            # read time
            with open("time.tmp", "r") as time_file:
                time = time_file.readline().rstrip()
            time = time.split(",")
            [float(i) for i in time]
            time = dict(zip(self.time_format, time))
            # save results
            self.output.setdefault(element, []).append(
                [time, {"package": package_energy, "core": core_energy}, self._extract_perf(result.stderr.decode())])
            with open('{}.out'.format(type(self).__name__), "a") as out_file, \
                    open('{}.err'.format(type(self).__name__), "a") as err_file:
                out_file.write(result.stdout.decode())
                err_file.write(result.stderr.decode())
            # clear
            os.remove("time.tmp")

    def _extract_perf(self, stderr):
        cleaned_perf = dict()
        # determine number of perf elements
        num_of_perf = len(self.perf[-1].split(","))
        # cut output
        perf_only = stderr.splitlines()[-num_of_perf:]
        # remove empty elements
        for ele in perf_only:
            value = [x for x in ele.split(",") if x]
            key = value.pop(1)
            cleaned_perf[key] = value[0]
            if int(value[2]) < self.sampling:
                self.sampling = int(value[2])
        return cleaned_perf

    def split(self):
        for key, value in self.output.items():
            predictor_key = self._convert_keys_to_int(key)
            # go through repetitions
            for bench in value:
                if random.randint(1, 100) <= self.training_percentage:
                    self.training.setdefault(predictor_key, []).append(bench)
                else:
                    self.control.setdefault(predictor_key, []).append(bench)

    def export_to_file(self):
        with open('{}.res'.format(type(self).__name__), "w") as export_file:
            csv_w = csv.writer(export_file, delimiter='#')
            for key, value in self.output.items():
                export = list()
                string_keys = [str(i) for i in self._convert_keys_to_int(key)]
                export.append(','.join(string_keys))
                for bench in value:
                    string_value = ""
                    for e in bench:
                        val_str = [str(i) for i in list(e.values())]
                        string_value = string_value + ",".join(val_str) + ","
                    export.append(string_value[:-1])
                csv_w.writerow(export)

    def _convert_keys_to_int(self, key: list) -> list:
        csv_key = list()
        metrics = self.get_metrics()
        # make all metrics numeric
        for idx, val in enumerate(key):
            try:
                ele = int(val)
            except ValueError:
                ele = metrics[idx].index(val)
            csv_key.append(ele)
        return csv_key
