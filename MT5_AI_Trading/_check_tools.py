import sys

tools = ['decompyle3', 'uncompyle6', 'pycdc']
for tool in tools:
    try:
        __import__(tool)
        print(f'{tool}: available')
    except ImportError:
        print(f'{tool}: not found')

# Also try to use py_compile to get source from .pyc
import marshal
from pathlib import Path

pyc = Path('python/ai_engine/__pycache__/d1_risk_officer.cpython-312.pyc')
with open(pyc, 'rb') as f:
    header = f.read(16)
    code = marshal.load(f)

print(f'\nCode object: {type(code)}')
print(f'Code filename: {code.co_filename}')
print(f'Code names: {code.co_names[:10]}...')
