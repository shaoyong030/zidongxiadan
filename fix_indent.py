import re

with open('openclaw_task.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # If the line has more than 20 spaces followed by '# 提交前双重确认地址' or similar
    if line.startswith(' ' * 40):
        new_lines.append(line[20:])
    elif line.startswith(' ' * 20) and not line.startswith(' ' * 40):
        # wait, let's just strip exactly 20 spaces from all those over-indented lines inside that block
        # better:
        pass
        
    # An easier heuristic: ANY line that starts with exactly 40 spaces in this file is wrong, 
    # it should be 20 spaces because our block was deeply indented artificially
    # wait, the code is Python, indentation matters.
    # What if I just look for lines starting with '                                        '
    # 40 spaces = ' ' * 40
    if line.startswith(' ' * 40):
        new_lines.append(line[20:])
    elif line.startswith(' ' * 44):
        new_lines.append(line[20:])
    elif line.startswith(' ' * 48):
        new_lines.append(line[20:])
    else:
        # Wait, if I just do string replacement:
        new_lines.append(line)

with open('test_fixed.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
