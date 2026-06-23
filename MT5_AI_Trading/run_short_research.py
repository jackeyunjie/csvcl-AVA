import subprocess
import sys
from pathlib import Path

project_root = Path(r"D:\qoder\csvcl - AVA\MT5_AI_Trading")
python_path = project_root / "python"

env = {
    "PYTHONPATH": str(python_path),
}

cmd = [
    sys.executable,
    str(project_root / "mine_h1_regime_strategies.py"),
    "--direction", "short",
    "--out-prefix", str(project_root / "data" / "h1_regime_short"),
    "--top-regimes", "30",
    "--top-candidates", "50",
    "--min-trades", "20",
]

print(f"Running: {' '.join(cmd)}")
print(f"PYTHONPATH={env['PYTHONPATH']}")
print("-" * 60)

result = subprocess.run(cmd, capture_output=True, text=True, env={**subprocess.os.environ, **env})

print("STDOUT:")
print(result.stdout)
print("-" * 60)
print("STDERR:")
print(result.stderr)
print("-" * 60)
print(f"Return code: {result.returncode}")
