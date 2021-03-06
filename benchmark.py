import csv
import os
import random
import subprocess
import sys
from ctypes import *

import matplotlib.pyplot as plt
from tqdm import tqdm


class Benchmark:
    def __init__(self, perf, repetitions, intel=False, one_hot=False):
        self.training_percentage = None
        self.sampling = 100
        self.repetitions = repetitions
        self.intel = intel
        self.one_hot = one_hot
        random.seed()
        # time
        self.time = ["/usr/bin/time", "-f", "%U,%S,%e", "-o", "time.tmp"]
        self.time_format = ["user", "sys", "elapsed"]
        # normal energy
        self.energy_format = ["energy-pkg", "energy-cores"]
        # perf for energy works on intel
        self.perf_energy = ["perf", "stat", "--field-separator", ",", "-e", "energy-pkg,energy-cores"]
        if self.intel:
            self.perf = self.perf_energy + perf
        else:
            self.perf = perf
        self.perf_format = self.perf[-1].split(",")
        # dicts for results
        self.output = dict()
        self.training = dict()
        self.control = dict()
        self.predicted = dict()
        # intel rapl files
        self.intel_rapl = {"package": "/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/energy_uj",
                           "core": "/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/intel-rapl:0:0/energy_uj",
                           "max_energy": "/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/max_energy_range_uj"}
        self._internal_checks()

    def bench(self) -> None:
        """
        This function needs to be implemented. When called, it should start with the benchmark specific bench.
        Please use run_subprocess to execute it.
        """
        raise NotImplementedError

    def get_metrics(self) -> list:
        """
        This function needs to be implemented. Returns all metrics as a list of lists.
        """
        raise NotImplementedError

    @staticmethod
    def get_one_hot() -> list:
        raise NotImplementedError

    def _internal_checks(self):
        if len(self.get_metrics()) != len(self.get_one_hot()):
            sys.exit("Length of get_metrics() does not match length of get_one_hot().")

    def run_subprocess(self, element: list, full_cmd: list):
        """
        This function executes command for you. It measures time, energy and perf for you.
        :param element: metric as a list. Used as key in output
        :type element: list
        :param full_cmd: the command to execute as a list
        :type full_cmd: list
        """
        for i in range(self.repetitions):
            # read energy before running
            with open(self.intel_rapl["package"], "r") as package, open(self.intel_rapl["core"], "r") as core:
                package_energy = int(package.readline().rstrip())
                core_energy = int(core.readline().rstrip())
            # execute command
            result = subprocess.run(self.perf + self.time + full_cmd, capture_output=True)
            # read energy again
            with open(self.intel_rapl["package"], "r") as package, open(self.intel_rapl["core"], "r") as core, open(
                    self.intel_rapl["max_energy"], "r") as max_en:
                max_energy = int(max_en.readline().rstrip())
                package_energy = (int(package.readline().rstrip()) - package_energy + max_energy) % max_energy
                core_energy = (int(core.readline().rstrip()) - core_energy + max_energy) % max_energy
            # read time
            with open("time.tmp", "r") as time_file:
                time = time_file.readline().rstrip()
            # time to dict
            time = time.split(",")
            [float(i) for i in time]
            time = dict(zip(self.time_format, time))
            # extract perf
            perf_dict = self._extract_perf(result.stderr.decode())
            # energy to dict
            if self.intel:
                energy = dict(zip(self.energy_format, [perf_dict.pop("energy-pkg"), perf_dict.pop("energy-cores")]))
            else:
                energy = dict(zip(self.energy_format, [package_energy, core_energy]))
            # save results
            self.output.setdefault(element, []).append(time | energy | perf_dict)
            with open('{}.out'.format(type(self).__name__), "a") as out_file, \
                    open('{}.err'.format(type(self).__name__), "a") as err_file:
                out_file.write(result.stdout.decode())
                err_file.write(result.stderr.decode())
            # clear
            os.remove("time.tmp")

    def _extract_perf(self, stderr) -> dict:
        cleaned_perf = dict()
        # determine number of perf elements
        if self.intel:
            num_of_perf = len(self.perf_format) + len(self.energy_format)
        else:
            num_of_perf = len(self.perf_format)
        # cut output
        perf_only = stderr.splitlines()[-num_of_perf:]
        # remove empty elements
        for ele in perf_only:
            value = ele.split(",")
            key = value.pop(2)
            if "energy" not in key:
                cleaned_perf[key] = int(value[0])
            else:
                cleaned_perf[key] = float(value[0])
            perf_sampling = value[3].split(".")
            if int(perf_sampling[0]) < self.sampling:
                self.sampling = int(perf_sampling[0])
        return cleaned_perf

    def split_results(self, training_percentage: int) -> None:
        self.training_percentage = training_percentage
        for key, value in self.output.items():
            if self.one_hot:
                predictor_key = self._convert_keys_one_hot(key)
            else:
                predictor_key = self._convert_keys_to_int(key)
            # go through repetitions
            for bench in value:
                if random.randint(1, 100) <= self.training_percentage:
                    self.training.setdefault(predictor_key, []).append(bench)
                else:
                    self.control.setdefault(predictor_key, []).append(bench)

    def export_to_file(self) -> None:
        with open('{}.res'.format(type(self).__name__), "w") as export_file:
            csv_w = csv.writer(export_file, delimiter='#')
            for key, value in self.output.items():
                export = list()
                string_keys = [str(i) for i in self._convert_keys_to_int(key)]
                export.append(','.join(string_keys))
                for bench in value:
                    string_value = ""
                    val_str = [str(i) for i in list(bench.values())]
                    string_value = string_value + ",".join(val_str) + ","
                    export.append(string_value[:-1])
                csv_w.writerow(export)

    def import_from_file(self) -> None:
        with open('{}.res'.format(type(self).__name__), "r") as import_file:
            csv_r = csv.reader(import_file, delimiter='#')
            for idx, line in enumerate(csv_r):
                key = line.pop(0)
                key = self._convert_ints_to_key(key.split(','))
                value = line
                value_list = list()
                for bench in value:
                    b = bench.split(',')
                    time_dict = dict(zip(self.time_format, [float(i) for i in b[:len(self.time_format)]]))
                    del b[:len(self.time_format)]
                    energy_dict = dict(zip(self.energy_format, [float(i) for i in b[:len(self.energy_format)]]))
                    del b[:len(self.energy_format)]
                    perf_dict = dict(zip(self.perf_format, [int(i) for i in b]))
                    # NOTE: 3.9+ ONLY
                    value_list.append(time_dict | energy_dict | perf_dict)
                self.output[key] = value_list

    def _convert_keys_to_int(self, key: tuple) -> tuple:
        csv_key = list()
        metrics = self.get_metrics()
        for idx, val in enumerate(key):
            ele = metrics[idx].index(val)
            csv_key.append(ele)
        return tuple(csv_key)

    def _convert_keys_one_hot(self, key: tuple) -> tuple:
        csv_key = list()
        metrics = self.get_metrics()
        one_hot = self.get_one_hot()
        for idx, val in enumerate(key):
            if one_hot[idx]:
                arr = [0] * len(metrics[idx])
                pos = metrics[idx].index(val)
                arr[pos] = 1
                csv_key += arr
            else:
                try:
                    csv_key.append(int(val))
                except ValueError:
                    csv_key.append(metrics[idx].index(val))
        return tuple(csv_key)

    def _convert_ints_to_key(self, csv_key: list) -> tuple:
        csv_key = [int(i) for i in csv_key]
        key_list = list()
        metrics = self.get_metrics()
        for idx, val in enumerate(csv_key):
            key_list.append(metrics[idx][val])
        return tuple(key_list)

    def train_llsp(self) -> None:
        # +1 for dummy
        num_metrics = len(list(self.training.keys())[0]) + 1

        # connect c-file
        so_file = "helper.so"
        my_functions = CDLL(so_file)
        my_functions.predict.restype = c_double
        my_functions.solve.restype = c_int

        for param in self.time_format + self.energy_format + self.perf_format:
            # init llsp
            my_functions.initialize(c_size_t(num_metrics))
            # start training
            for key, value in self.training.items():
                dummy_key = [1] + list(key)
                metric = (c_double * num_metrics)(*dummy_key)
                for rep in value:
                    target = c_double(rep[param])
                    my_functions.add(metric, target)
            # solving
            if my_functions.solve() != 1:
                sys.exit("Prediction failed! llsp returned: {}. Expected: 1.".format(my_functions.solve()))
            # if solving works, start predicting
            for key, value in self.output.items():
                if self.one_hot:
                    dummy_key = [1] + list(self._convert_keys_one_hot(key))
                else:
                    dummy_key = [1] + list(self._convert_keys_to_int(key))
                metric = (c_double * num_metrics)(*dummy_key)
                prediction = my_functions.predict(metric)
                self.predicted.setdefault(key, dict())[param] = prediction
            # remove everything
            my_functions.dispose()

    def plot(self) -> None:
        for param in tqdm(self.time_format + self.energy_format + self.perf_format):
            plt.style.use('ggplot')
            fig, ax = plt.subplots()
            x_axes, y_axes, min_axes, max_axes, metrics = (list() for i in range(5))
            for idx, metric in enumerate(list(self.predicted.keys())):
                value = self.predicted[metric]
                metrics.append(",".join(metric))
                x_axes.append(idx)
                y_axes.append(value[param])
                min_axes.append(self._get_min_max(metric, param)[0])
                max_axes.append(self._get_min_max(metric, param)[1])
            ax.plot(x_axes, y_axes, 'o-', label="predicted values")
            ax.fill_between(x_axes, min_axes, max_axes, color='tab:blue', alpha=0.8,
                            label="measured min to max corridor")
            fig.legend(loc="upper center")
            ax.set_ylabel(param)
            ax.set_xticks(x_axes)
            ax.set_xticklabels(metrics, rotation='vertical', fontsize=12)
            fig.tight_layout()
            plt.rcParams["figure.autolayout"] = True
            fig.set_size_inches(0.2 * len(metrics), 6)
            fig.savefig("pics/{}_{}.svg".format(type(self).__name__, param))
            plt.close()

    def _get_min_max(self, metric: tuple, key: str) -> tuple:
        """
        Returns the min and max value for given metric and key as a tuple.
        :param metric: The metric you are interested in
        :type metric: tuple
        :param key: The key you are interested in
        :type key: str
        :return: (min, max)
        :rtype: tuple
        """
        all_values = list()
        bench = self.output[metric]
        for rep in bench:
            all_values.append(rep[key])
        return min(all_values), max(all_values)
