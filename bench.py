import itertools
import subprocess
import time
from tqdm import tqdm


class Ffmpeg:
    def __init__(self, perf, repetitions):
        self.perf = perf
        self.repetitions = repetitions
        self.cmd = ["ffmpeg", "-y", "-f", "image2", "-i", "raw/life_%06d.pbm", "-vf", "scale=1080:1080",
                    "result.mp4"]
        self.quality_steps = [0, 10, 20, 30, 40, 50]
        self.fps = [0, 5, 10, 15, 25]
        # self.scale = [720, 1080, 2048]
        self.preset = ["veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]

    def bench(self):
        combos = [self.quality_steps, self.fps, self.preset]
        combos = list(itertools.product(*combos))
        print(combos)
        with open("ffmpeg.txt", "w") as f:
            print("Benching ffmpeg:")
            for element in tqdm(combos):
                for i in range(repetitions):
                    start = time.perf_counter()
                    result = subprocess.run(self.perf + self.cmd, capture_output=True)
                    end = time.perf_counter()
                    f.write("Time: {}\n".format(end - start))


# Config
repetitions = 1
perf = ["perf", "stat", "--field-separator", ",", "--event",
        "context-switches,cpu-migrations,energy-pkg,cache-misses,branch-misses"]
zips = ["7z", "a", "-aoa", "-t7z", "-m0=LZMA2", "-mx=1", "output.7z", "raw/*.pbm", "-r"]
ffmpeg = ["ffmpeg", "-y", "-f", "image2", "-r", "6", "-i", "raw/life_%06d.pbm", "-crf", "22", "-vf", "scale=1080:1080",
          "result.mp4"]

# Benching
print("Welcome to our Benchmark! We are doing {} repetitions per bench.".format(repetitions))
num_one = Ffmpeg(perf, repetitions)
num_one.bench()
# print("running 7z...")
# result = subprocess.run(perf+zips, capture_output=True)
# print(result.stdout.decode())
# print(result.stderr.decode())
