import itertools
import os
import subprocess
import sys

from tqdm import tqdm


class Benchmark:
    def __init__(self, perf, repetitions):
        self.perf = perf
        self.repetitions = repetitions
        self.time = ["/usr/bin/time", "-f", "%U,%S,%e", "-o", "time.tmp"]
        self.time_format = ["user", "sys", "elapsed"]
        """
        Stores all results. Format:
        arguments -> list of runs (one element per run)
        one run: [time, {"package": package_energy, "core": core_energy}, perf]
        """
        self.output = dict()

    def bench(self):
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
                [time, {"package": package_energy, "core": core_energy}, self.extract_perf(result.stderr.decode())])
            # clear
            os.remove("time.tmp")

    def extract_perf(self, stderr):
        cleaned_perf = dict()
        # determine number of perf elements
        num_of_perf = len(self.perf[-1].split(","))
        # cut output
        perf_only = stderr.splitlines()[-num_of_perf:]
        # remove empty elements
        for ele in perf_only:
            value = [x for x in ele.split(",") if x]
            key = value.pop(1)
            cleaned_perf[key] = value
        return cleaned_perf


class Ffmpeg(Benchmark):
    def __init__(self, perf, repetitions):
        super().__init__(perf, repetitions)
        self.cmd = ["ffmpeg", "-y", "-f", "image2", "-i", "raw/life_%06d.pbm", "-vf", "scale=1080:1080", "result.mp4"]
        self.quality_steps = ["0", "10", "20", "30", "40", "50"]
        self.fps = ["1", "5", "10", "15", "25"]
        # self.scale = [720, 1080, 2048]
        self.preset = ["veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]

    def bench(self):
        combos = [self.quality_steps, self.fps, self.preset]
        combos = list(itertools.product(*combos))
        print("Benching ffmpeg:")
        for element in tqdm(combos):
            full_cmd = self.cmd + ["-crf", element[0]] + ["-r", element[1]] + ["-preset", element[2]]
            self.run_subprocess(element, full_cmd)


class Zip(Benchmark):
    def __init__(self, perf, repetitions):
        super().__init__(perf, repetitions)
        self.cmd = ["7z", "a", "-aoa", "-t7z"]
        self.cmd_two = ["output.7z", "raw/*.pbm", "-r"]
        self.x = ["0", "1", "3", "5", "7", "9"]  # 0=copy. should be same time with every compression method
        self.mt = ["on", "off"]
        self.algo = ["lzma", "lzma2", "bzip2", "deflate"]

    def bench(self):
        combos = [self.x, self.mt, self.algo]
        combos = list(itertools.product(*combos))
        print("Benching 7zip:")
        for element in tqdm(combos):
            full_cmd = self.cmd + ["-mx=" + element[0]] + ["-mmt=" + element[1]] + ["-m0=" + element[2]] + self.cmd_two
            self.run_subprocess(element, full_cmd)


class Openssl(Benchmark):
    def __init__(self, perf, repetitions):
        super().__init__(perf, repetitions)
        self.cmd_enc = ["openssl", "enc", "-pass", "pass:1234", "-out", "encrypted.data"]
        self.cmd_dec = ["openssl", "enc", "-d", "-pass", "pass:1234"]
        self.salt = ["-salt", "-nosalt"]
        self.base64 = ["", "-a"]
        self.pbkdf2 = ["", "-pbkdf2"]
        self.enc = ["-aes-128-cbc", "-aes-128-ecb", "-aes-192-cbc", "-aes-192-ecb", "-aes-256-cbc", "-aes-256-ecb"]
        self.sizes = ["10", "100", "1000", "10000"]

    def bench(self):
        combos = [self.enc, self.base64, self.salt, self.pbkdf2]
        combos = list(itertools.product(*combos))
        print("Benching Openssl:")
        for size in self.sizes:
            subprocess.run(["dd", "if=/dev/zero", "of=" + size + ".file", "bs=1M", "count=" + size])
            for element in tqdm(combos):
                # We must remove empty elements. Else it will fail
                full_cmd = self.cmd_enc + [x for x in list(element) if x] + ["-in", size + ".file"]
                self.run_subprocess(element, full_cmd)


if __name__ == '__main__':
    try:
        # Config
        repetitions = 5
        benchs = list()
        ext = [".file", ".7z", ".data", ".mp4", ".tmp"]
        perf = ["perf", "stat", "--field-separator", ",", "--event",
                "context-switches,cpu-migrations,cache-misses,branch-misses"]
        # Benching
        print("Welcome to our Benchmark! We are doing {} repetitions per bench.".format(repetitions))
        # benchs.append(Ffmpeg(perf, repetitions))
        # benchs.append(Zip(perf, repetitions))
        benchs.append(Openssl(perf, repetitions))
        for b in benchs:
            b.bench()
    except KeyboardInterrupt:
        print('Received Keyboard Interrupt')
        print('Cleaning up before exit...')
        for file in os.listdir():
            if file.endswith(tuple(ext)):
                os.remove(file)
        print('Bye :)')
        sys.exit(0)
