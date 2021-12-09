#!/usr/bin/python3

import subprocess
import time

# quality, scale, fps, threads and number of files can be limited
perf = ["perf", "stat", "--field-separator", ",", "--event", "context-switches,cpu-migrations,energy-pkg,cache-misses,branch-misses"]
zips = ["7z", "a", "-aoa", "-t7z", "-m0=LZMA2", "-mx=1", "output.7z", "raw/*.pbm", "-r"]
ffmpeg = ["ffmpeg", "-y" ,"-f", "image2", "-r", "6", "-i", "raw/life_%06d.pbm", "-q:v", "2", "-vf", "scale=1080:1080", "result.mp4"]
print(*ffmpeg)
print("running ffmpeg...")
start = time.perf_counter()
result = subprocess.run(perf+ffmpeg, capture_output=True)
end = time.perf_counter()
#print(result.stdout.decode())
#print(result.stderr.decode())
#print("running 7z...")
#result = subprocess.run(perf+zips, capture_output=True)
#print(result.stdout.decode())
#print(result.stderr.decode())
print(end-start)
