import itertools
import os
import subprocess
from tqdm import tqdm


class Benchmark:
    def __init__(self, perf, repetitions):
        self.perf = perf
        self.repetitions = repetitions
        self.time = ["/usr/bin/time", "-o", "time.txt"]
        self.output = dict()

    def bench(self):
        raise NotImplementedError


class Ffmpeg(Benchmark):
    def __init__(self, perf, repetitions):
        super().__init__(perf, repetitions)
        self.cmd = ["ffmpeg", "-y", "-f", "image2", "-i", "raw/life_%06d.pbm", "-vf", "scale=1080:1080",
                    "result.mp4"]
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
            for i in range(repetitions):
                result = subprocess.run(self.perf + self.time + full_cmd, capture_output=True)
                with open("time.txt", "r") as time_file:
                    lines = time_file.readlines()
                    lines = [line.rstrip() for line in lines]
                self.output.setdefault(element, []).append(
                    [lines[0], lines[1], result.stdout.decode(), result.stderr.decode()])
                os.remove("time.txt")


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
            for i in range(repetitions):
                result = subprocess.run(self.perf + self.time + full_cmd, capture_output=True)
                with open("time.txt", "r") as time_file:
                    lines = time_file.readlines()
                    lines = [line.rstrip() for line in lines]
                self.output.setdefault(element, []).append(
                    [lines[0], lines[1], result.stdout.decode(), result.stderr.decode()])
                os.remove("time.txt")


# Config
repetitions = 5
benchs = list()
perf = ["perf", "stat", "--field-separator", ",", "--event",
        "context-switches,cpu-migrations,energy-pkg,cache-misses,branch-misses"]
# Benching
print("Welcome to our Benchmark! We are doing {} repetitions per bench.".format(repetitions))
benchs.append(Ffmpeg(perf, repetitions))
benchs.append(Zip(perf, repetitions))
for b in benchs:
    b.bench()
# print(result.stdout.decode())
# print(result.stderr.decode())
