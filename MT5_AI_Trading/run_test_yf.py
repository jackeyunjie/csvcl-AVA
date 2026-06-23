import subprocess
import sys

result = subprocess.run(
    [sys.executable, "test_yf.py"],
    capture_output=True,
    text=True,
    cwd=r"d:\qoder\csvcl - AVA\MT5_AI_Trading"
)
print("=== STDOUT ===")
print(result.stdout)
print("=== STDERR ===")
print(result.stderr)
print("=== RETURN CODE ===")
print(result.returncode)
