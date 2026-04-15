import os
import re

file_path = '/Users/shaoyong/Desktop/zidongxiadan/openclaw_task.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update iframe wait strategy: we wait for EITHER textarea OR input with these placeholders
content = re.sub(
    r"address_context\.locator\('textarea, input#fullName'\)\.first\.wait_for\(timeout=3000\)",
    r"address_context.locator('textarea, input#fullName, input[placeholder*=\"25个字符\"]').first.wait_for(timeout=3000)",
    content
)

# 2. Prevent mistakenly treating the detailed address textarea as smart_box. 
# We only treat it as smart_box if it's NOT the detailed address box. Or we only treat it as smart box if there is a '解析' or '智能' button or the placeholder is strictly '粘贴'
content = content.replace(
    r"smart_box = address_context.locator('textarea').first",
    r"smart_box = address_context.locator('textarea:not([placeholder*=\"详细地址\"])').first"
)

# 3. Update region clicker to support new placeholder
content = content.replace(
    r"address_context.locator('.cndzk-entrance-division-header-click, .ant-select-selector').first.click",
    r"address_context.locator('.cndzk-entrance-division-header-click, .ant-select-selector, input[placeholder*=\"省/市/区\"], span[title*=\"省/市/区\"], .next-select').first.click"
)
content = content.replace(
    r"address_context.locator('.cndzk-entrance-division-header-click, .ant-select-selector').first.evaluate",
    r"address_context.locator('.cndzk-entrance-division-header-click, .ant-select-selector, input[placeholder*=\"省/市/区\"], span[title*=\"省/市/区\"], .next-select').first.evaluate"
)

# 4. Update Name Locator
content = content.replace(
    r"name_input = address_context.locator('input#fullName, input[placeholder*=\"姓名\"]').first",
    r"name_input = address_context.locator('input#fullName, input[placeholder*=\"姓名\"], input[placeholder*=\"5个字\"], input[placeholder*=\"长度不超过\"]').first"
)

# 5. Update Phone Locator
content = content.replace(
    r"phone_input = address_context.locator('input#mobile, input[placeholder*=\"手机\"]').first",
    r"phone_input = address_context.locator('input#mobile, input[placeholder*=\"手机\"], input[placeholder*=\"必须填一项\"]').first"
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Locators patched!")
