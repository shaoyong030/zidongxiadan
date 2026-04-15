import re

file_path = '/Users/shaoyong/Desktop/zidongxiadan/openclaw_task.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Increase wait_for timeout on the iframe step
content = re.sub(
    r"wait_for\(timeout=3000\)",
    r"wait_for(timeout=10000)",
    content
)

# Increase Region click timeout from 3000 to 8000
content = re.sub(
    r"first\.click\(force=True, timeout=3000\)",
    r"first.click(force=True, timeout=8000)",
    content
)

# Increase wait inside name click from 2000 to 8000
content = re.sub(
    r"name_input\.click\(timeout=2000\)",
    r"name_input.click(timeout=8000)",
    content
)

# Increase wait inside phone click from 2000 to 8000
content = re.sub(
    r"phone_input\.click\(timeout=2000\)",
    r"phone_input.click(timeout=8000)",
    content
)

# Increase wait inside addr_input click from 2000 to 8000
content = re.sub(
    r"addr_input\.click\(timeout=2000\)",
    r"addr_input.click(timeout=8000)",
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Timeouts expanded!")
