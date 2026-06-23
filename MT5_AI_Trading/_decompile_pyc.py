import marshal
import dis
import types
from pathlib import Path

def extract_from_pyc(pyc_path, output_path):
    with open(pyc_path, 'rb') as f:
        header = f.read(16)  # Python 3.12 header
        code = marshal.load(f)
    
    # Try to reconstruct source from code object
    # This is a best-effort approach for Python 3.12
    
    lines = []
    lines.append(f"# Decompiled from {pyc_path}")
    lines.append(f"# Python version: 3.12")
    lines.append("")
    
    # Extract constants (string literals, etc.)
    def extract_constants(co):
        result = []
        for const in co.co_consts:
            if isinstance(const, str) and '\n' in const:
                result.append(const)
            elif isinstance(const, types.CodeType):
                result.extend(extract_constants(const))
        return result
    
    constants = extract_constants(code)
    
    # Write what we can extract
    lines.append("# Constants found in bytecode:")
    for i, const in enumerate(constants[:20]):  # Limit to first 20
        lines.append(f"# Const {i}:")
        for line in const.split('\n')[:10]:  # First 10 lines
            lines.append(f"#   {line}")
    
    Path(output_path).write_text('\n'.join(lines), encoding='utf-8')
    print(f"Extracted constants to {output_path}")
    return constants

# Extract from hermass_state_ops
constants = extract_from_pyc('__pycache__/hermass_state_ops.cpython-312.pyc', '_extracted_constants.txt')
print(f"Found {len(constants)} string constants")
