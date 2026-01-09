
import sys
import os

print("STDOUT WORKING", flush=True)
print("STDERR WORKING", file=sys.stderr, flush=True)

try:
    with open("debug_test.txt", "w") as f:
        f.write("FILE WORKING")
    print(f"File created at {os.path.abspath('debug_test.txt')}", flush=True)
except Exception as e:
    print(f"File write failed: {e}", file=sys.stderr, flush=True)
