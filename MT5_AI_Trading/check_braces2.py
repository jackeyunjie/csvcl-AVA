import re

with open('mql5/Experts/AI_Trading_Bridge.mq5','r',encoding='utf-8') as f:
    lines = f.readlines()

open_count = 0
close_count = 0

for line in lines:
    # Remove comments
    if '//' in line:
        line = line[:line.index('//')]
    
    # Remove string contents
    cleaned = ''
    in_str = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            in_str = not in_str
            i += 1
            continue
        if not in_str:
            cleaned += ch
        i += 1
    
    open_count += cleaned.count('{')
    close_count += cleaned.count('}')

print(f"Braces: {{{open_count}, }}{close_count}")
if open_count == close_count:
    print("BALANCED")
else:
    print(f"UNBALANCED by {close_count - open_count}")
