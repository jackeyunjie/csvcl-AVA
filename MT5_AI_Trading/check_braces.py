f=open('mql5/Experts/AI_Trading_Bridge.mq5','r',encoding='utf-8');c=f.read();f.close()
lines=c.split('\n')

# 精确统计：排除字符串和注释中的括号
open_count=0
close_count=0
for line in lines:
    if '//' in line:
        line=line[:line.index('//')]
    cleaned=''
    in_str=False
    for ch in line:
        if ch=='"':
            in_str=not in_str
            continue
        if not in_str:
            cleaned+=ch
    open_count+=cleaned.count('{')
    close_count+=cleaned.count('}')

print(f"代码块 {{={open_count}, }}={close_count}")
if open_count==close_count:
    print("OK: 括号平衡")
else:
    print(f"ERROR: 差 {close_count-open_count} 个}}")
