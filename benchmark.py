import csv
import os
import random
import subprocess
import sys

from ctypes import *


class Benchmark:
    def __init__(self, perf, repetitions, training_percentage):
        self.perf = perf
        self.repetitions = repetitions
        self.time = ["/usr/bin/time", "-f", "%U,%S,%e", "-o", "time.tmp"]
        ###
        self.time_format = ["user", "sys", "elapsed"]
        self.energy_format = ["package", "core"]
        self.perf_format = self.perf[-1].split(",")
        ###
        self.training_percentage = training_percentage
        self.sampling = 100

        self.training = dict()
        self.control = dict()
        self.predicted = dict()
        """
        Stores all results. Format:
        arguments -> list of runs (one element per run)
        one run: {time, energy, perf}
        """
        self.output = dict()

        random.seed()

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
            # time to dict
            time = time.split(",")
            [float(i) for i in time]
            time = dict(zip(self.time_format, time))
            # energy to dict
            energy = dict(zip(self.energy_format, [package_energy, core_energy]))
            # save results
            self.output.setdefault(element, []).append(time | energy | self._extract_perf(result.stderr.decode()))
            with open('{}.out'.format(type(self).__name__), "a") as out_file, \
                    open('{}.err'.format(type(self).__name__), "a") as err_file:
                out_file.write(result.stdout.decode())
                err_file.write(result.stderr.decode())
            # clear
            os.remove("time.tmp")

    def _extract_perf(self, stderr):
        cleaned_perf = dict()
        # determine number of perf elements
        num_of_perf = len(self.perf_format)
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

    def split_results(self):
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
                    val_str = [str(i) for i in list(bench.values())]
                    string_value = string_value + ",".join(val_str) + ","
                    export.append(string_value[:-1])
                csv_w.writerow(export)

    def import_from_file(self):
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
                    energy_dict = dict(zip(self.energy_format, [int(i) for i in b[:len(self.energy_format)]]))
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

    def _convert_ints_to_key(self, csv_key: list) -> tuple:
        csv_key = [int(i) for i in csv_key]
        key_list = list()
        metrics = self.get_metrics()
        for idx, val in enumerate(csv_key):
            key_list.append(metrics[idx][val])
        return tuple(key_list)

    def train_llsp(self):
        # read out some informations
        num_metrics = len(list(self.training.keys())[0])
        num_targets = len(self.time_format) + len(self.energy_format) + len(self.perf_format)

        # connect c-file
        so_file = "helper.so"
        my_functions = CDLL(so_file)
        my_functions.predict.restype = c_double
        # init llsp
        my_functions.initialize(c_size_t(num_metrics))
        # start training
        for key, value in self.training.items():
            metric = (c_double * num_metrics)(*list(key))
            for rep in value:
                target = c_double(rep["elapsed"])
                my_functions.add(metric, target)
        # solving
        if my_functions.solve() != 1:
            print("Prediction failed")
            sys.exit(2)
        # if solving works, start predicting
        for key, value in self.control.items():
            metric = (c_double * num_metrics)(*list(key))
            prediction = my_functions.predict(metric)
            new_key = self._convert_ints_to_key(key)
            self.predicted.setdefault(new_key, dict())["elapsed"] = prediction
        # remove everything
        my_functions.dispose()
        print(self.predicted)
