import re

file_path = '/Users/shaoyong/Desktop/zidongxiadan/openclaw_task.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update iframe wait strategy
content = re.sub(
    r"address_context\.locator\('textarea, input#fullName'\)\.first\.wait_for",
    r"address_context.locator('textarea, input#fullName, input[placeholder*=\"25个\"], input[placeholder*=\"必须填一项\"]').first.wait_for",
    content
)

# 2. Prevent mistakenly treating the detailed address textarea as smart_box.
content = re.sub(
    r"smart_box = address_context\.locator\('textarea'\)\.first",
    r"smart_box = address_context.locator('textarea:not([placeholder*=\"详细地址\"])').first",
    content
)

# 3. Update region clicker
content = re.sub(
    r"address_context\.locator\('.cndzk-entrance-division-header-click, \.ant-select-selector'\)\.first\.click",
    r"address_context.locator('.cndzk-entrance-division-header-click, .ant-select-selector, input[placeholder*=\"省/市/区\"], span[title*=\"省/市/区\"], .next-select').first.click",
    content
)
content = re.sub(
    r"address_context\.locator\('.cndzk-entrance-division-header-click, \.ant-select-selector'\)\.first\.evaluate",
    r"address_context.locator('.cndzk-entrance-division-header-click, .ant-select-selector, input[placeholder*=\"省/市/区\"], span[title*=\"省/市/区\"], .next-select').first.evaluate",
    content
)

# 4. Update Name Locator
content = re.sub(
    r"name_input = address_context\.locator\('input#fullName, input\[placeholder\*=\"姓名\"\]'\)\.first",
    r"name_input = address_context.locator('input#fullName, input[placeholder*=\"姓名\"], input[placeholder*=\"25个字\"], input[placeholder*=\"长度不超过\"]').first",
    content
)

# 5. Update Phone Locator
content = re.sub(
    r"phone_input = address_context\.locator\('input#mobile, input\[placeholder\*=\"手机\"\]'\)\.first",
    r"phone_input = address_context.locator('input#mobile, input[placeholder*=\"手机\"], input[placeholder*=\"必须填一项\"]').first",
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Regex patch applied.")
