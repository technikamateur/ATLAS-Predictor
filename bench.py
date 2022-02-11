import argparse
import itertools
import os
import subprocess
import sys

from tqdm import tqdm

from benchmark import Benchmark


def clean_up(ext: tuple):
    for file in os.listdir():
        if file.endswith(ext):
            os.remove(file)


class Ffmpeg(Benchmark):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd = ["ffmpeg", "-y", "-f", "image2", "-i", "raw/life_%06d.pbm", "-vf", "scale=1080:1080"]
        self.quality_steps = ["0", "10", "20", "30", "40", "50"]
        self.fps = ["1", "5", "10", "15", "25"]
        # self.scale = [720, 1080, 2048]
        self.preset = ["veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]

    def bench(self):
        combos = list(itertools.product(*self.get_metrics()))
        print("Benching ffmpeg:")
        for element in tqdm(combos):
            full_cmd = self.cmd + ["-crf", element[0]] + ["-r", element[1]] + ["-preset", element[2]] + ["result.mp4"]
            self.run_subprocess(element, full_cmd)

    def get_metrics(self):
        return [self.quality_steps, self.fps, self.preset]


class Zip(Benchmark):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd = ["7z", "a", "-aoa", "-t7z"]
        self.cmd_two = ["output.7z", "raw/*.pbm", "-r"]
        self.x = ["0", "1", "3", "5", "7", "9"]
        self.mt = ["on", "off"]
        self.algo = ["lzma", "lzma2", "bzip2", "deflate"]

    def bench(self):
        combos = list(itertools.product(*self.get_metrics()))
        print("Benching 7zip:")
        for element in tqdm(combos):
            full_cmd = self.cmd + ["-mx=" + element[0]] + ["-mmt=" + element[1]] + ["-m0=" + element[2]] + self.cmd_two
            self.run_subprocess(element, full_cmd)

    def get_metrics(self):
        return [self.x, self.mt, self.algo]


class Openssl(Benchmark):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd_enc = ["openssl", "enc", "-pass", "pass:1234", "-out", "encrypted.data"]
        self.cmd_dec = ["openssl", "enc", "-d", "-pass", "pass:1234"]
        self.salt = ["-salt", "-nosalt"]
        self.base64 = ["", "-a"]
        self.pbkdf2 = ["", "-pbkdf2"]
        self.enc = ["-aes-128-cbc", "-aes-128-ecb", "-aes-192-cbc", "-aes-192-ecb", "-aes-256-cbc", "-aes-256-ecb"]
        self.sizes = ["10", "100", "1000", "10000"]

    def bench(self):
        combos = list(itertools.product(*self.get_metrics()[:-1]))
        print("Benching Openssl:")
        for size in self.sizes:
            subprocess.run(["dd", "if=/dev/zero", "of=" + size + ".file", "bs=1M", "count=" + size])
            for element in tqdm(combos):
                # We must remove empty elements. Else it will fail
                full_cmd = self.cmd_enc + [x for x in list(element) if x] + ["-in", size + ".file"]
                self.run_subprocess(element + (size,), full_cmd)

    def get_metrics(self):
        return [self.enc, self.base64, self.salt, self.pbkdf2, self.sizes]


if __name__ == '__main__':
    # argparse
    parser = argparse.ArgumentParser(description="The benchmark of your choice :)")
    parser.add_argument('-r', '--repetitions', type=int, required=True,
                        help='Specifies the number of times a benchmark should be or has been repeated.')
    parser.add_argument('--intel', action='store_true', help='Set this flag if running on Intel platform')

    subparsers = parser.add_subparsers(dest='bench', title='subcommands',
                                       help='Somewhere you have to start. Bench or import files')
    parser_bench = subparsers.add_parser('bench')
    parser_bench.add_argument('-e', '--export', action='store_true',
                              help='You can export your results and import them later')

    parser_import = subparsers.add_parser('import')
    parser_import.add_argument('-t', '--training', type=int, choices=range(101), required=True,
                               help='A value between 1 and 100. Used to use a part of benched data as trainings data')
    parser_import.add_argument('-g', '--graphs', action='store_true',
                               help='You will get beautiful graphs :)')

    args = parser.parse_args()

    # check for permissions first
    if not os.access('/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/energy_uj', os.R_OK):
        sys.exit("No permissions. Please run \"sudoen.sh\" first.")
    # check Python version
    MIN_PYTHON = (3, 9)
    if sys.version_info < MIN_PYTHON:
        sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

    ###

    repetitions = args.repetitions
    benchs = list()
    ext = (".file", ".7z", ".data", ".mp4", ".tmp")
    perf = ["perf", "stat", "--field-separator", ",", "--event",
            "context-switches,cpu-migrations,cache-misses,branch-misses"]

    try:
        # Benching
        benchs.append(Ffmpeg(perf, repetitions, intel=args.intel))
        benchs.append(Zip(perf, repetitions, intel=args.intel))
        benchs.append(Openssl(perf, repetitions, intel=args.intel))
        if args.bench == 'bench':
            print("Welcome to our Benchmark! We are doing {} repetitions per metric.".format(repetitions))
            for b in benchs:
                b.bench()
                if b.sampling < 100:
                    print("Warning: sampling was {}".format(b.sampling))
                if args.export:
                    print("Exporting...")
                    b.export_to_file()
                    print("Hint: modifying perf, time, energy or the get_metrics makes the exported data useless.")
        elif args.bench == 'import':
            print("As configured, {}% of the results will be used as trainings data.".format(args.training))
            for b in benchs:
                b.import_from_file()
                b.split_results(args.training)
                b.train_llsp()
                if args.graphs:
                    print("Generating Graphs...")
                    b.plot()
        else:
            print('You have neither bench nor import specified. Nothing to do...')
            sys.exit(0)
        clean_up(ext)
    except KeyboardInterrupt:
        print('Received Keyboard Interrupt')
        print('Cleaning up before exit...')
        clean_up(ext)
        print('Bye :)')
        sys.exit(0)
