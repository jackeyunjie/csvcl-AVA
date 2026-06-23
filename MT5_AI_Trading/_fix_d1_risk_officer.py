import dis
import marshal
from pathlib import Path

pyc = Path('python/ai_engine/__pycache__/d1_risk_officer.cpython-312.pyc')
with open(pyc, 'rb') as f:
    header = f.read(16)
    code = marshal.load(f)

# Try to decompile using available tools
try:
    import uncompyle6
    uncompyle6.main.decompile_code(code, out=sys.stdout)
except ImportError:
    pass

try:
    import decompyle3
    decompyle3.main.decompile_code(code, out=sys.stdout)
except ImportError:
    pass

# Last resort: use dis to show bytecode
print("=== DISASSEMBLY ===")
dis.dis(code)
