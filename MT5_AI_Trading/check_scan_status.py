import os, glob, time, subprocess

# 检查报告文件
reports = glob.glob('reports/*.csv')
print('=== 报告文件 ===')
for r in sorted(reports):
    mtime = os.path.getmtime(r)
    size = os.path.getsize(r)
    print(f'  {os.path.basename(r)}: {size} bytes, {time.strftime("%H:%M:%S", time.localtime(mtime))}')

# 检查Python进程
result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], capture_output=True, text=True)
lines = [l for l in result.stdout.strip().split('\n') if 'python.exe' in l]
print(f'\n=== Python进程 ({len(lines)}个) ===')
for l in lines:
    print(f'  {l.strip()}')

# 检查是否有run_strategy_scan在运行
result2 = subprocess.run(['wmic', 'process', 'where', 'name="python.exe"', 'get', 'CommandLine,ProcessId'], 
                        capture_output=True, text=True)
print('\n=== Python命令行 ===')
for line in result2.stdout.strip().split('\n'):
    if 'run_strategy_scan' in line.lower() or 'strategy_miner' in line.lower():
        print(f'  {line.strip()[:120]}')
