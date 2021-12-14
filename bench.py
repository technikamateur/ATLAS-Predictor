import itertools
import subprocess
import time
from tqdm import tqdm


class Benchmark:
    def __init__(self, perf, repetitions):
        self.perf = perf
        self.repetitions = repetitions

    def bench(self):
        raise NotImplementedError


class Ffmpeg(Benchmark):
    def __init__(self, perf, repetitions):
        super().__init__(perf, repetitions)
        self.cmd = ["ffmpeg", "-y", "-f", "image2", "-i", "raw/life_%06d.pbm", "-vf", "scale=1080:1080",
                    "result.mp4"]
        self.quality_steps = [0, 10, 20, 30, 40, 50]
        self.fps = [0, 5, 10, 15, 25]
        # self.scale = [720, 1080, 2048]
        self.preset = ["veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]

    def bench(self):
        combos = [self.quality_steps, self.fps, self.preset]
        combos = list(itertools.product(*combos))
        with open("ffmpeg.txt", "w") as f:
            print("Benching ffmpeg:")
            f.write("Run,Time,quality,fps,preset")
            for element in tqdm(combos):
                full_cmd = self.cmd + ["-crf", element[0]] + ["-r", element[1]] + ["-preset", element[2]]
                for i in range(repetitions):
                    start = time.perf_counter()
                    result = subprocess.run(self.perf + full_cmd, capture_output=True)
                    end = time.perf_counter()
                    f.write("Time: {}\n".format(end - start))


class Zip(Benchmark):
    def __init__(self, perf, repetitions):
        super().__init__(perf, repetitions)
        self.cmd = ["7z", "a", "-aoa", "-t7z", "-m0=LZMA2", "-mx=1", "output.7z", "raw/*.pbm", "-r"]
        self.x = [0, 1, 3, 5, 7, 9]  # 0=copy. should be same time with every compression method
        self.mt = ["on", "off"]
        self.algo = ["lzma", "lzma2", "bzip2", "deflate"]

    def bench(self):
        combos = [self.x, self.mt, self.algo]
        combos = list(itertools.product(*combos))
        with open("7zip.txt", "w") as f:
            print("Benching 7zip:")
            f.write("Run,Time,x,mt,algo")
            for element in tqdm(combos):
                full_cmd = self.cmd + ["-mx=" + element[0]] + ["-mt="+ element[1]] + ["-m0=" + element[2]]
                for i in range(repetitions):
                    start = time.perf_counter()
                    result = subprocess.run(self.perf + full_cmd, capture_output=True)
                    end = time.perf_counter()
                    f.write("Time: {}\n".format(end - start))


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
