import re

def main():
    with open('openclaw_task.py', 'r') as f:
        content = f.read()

    # 1. Replace currency logic
    new_currency_logic = """                        try:
                            currency_el = tb_page.locator('text="人民币"').last
                            if currency_el.is_visible(timeout=2000):
                                currency_el.click(force=True)
                                checked = True
                            else:
                                checked = False
                        except:
                            checked = False"""

    old_currency_regex = r"checked = tb_page\.evaluate\('''(?:[^']|'(?!''))*'''\)"

    content = re.sub(old_currency_regex, new_currency_logic, content)

    # 2. Fix indentation
    # Find the try block for PROCESS_MERGE_PAGE
    pattern1 = re.compile(r"(                    try:\n                        address_context = tb_page.frame_locator\('iframe'\).last.*?(?=                    if not address_filled_success:\n                        processed_sns.add\(current_sn\)\n                        continue))", re.DOTALL)
    
    match1 = pattern1.search(content)
    if match1:
        block = match1.group(1)
        indented_block = "\n".join(["    " + line if line else line for line in block.split('\n')])
        indented_block = "                    if not address_filled_success:\n" + indented_block[4:] # remove extra 4 spaces from first line '                    try:' to keep it as '                        try:'
        content = content[:match1.start()] + indented_block + content[match1.end():]
        print("Fixed PROCESS_MERGE_PAGE address block.")

    # Find the try block for PLACE_ORDER
    # Wait, the pattern is the same because the code is identical.
    # The search might match the second one now.
    match2 = pattern1.search(content)
    if match2:
        block = match2.group(1)
        indented_block = "\n".join(["    " + line if line else line for line in block.split('\n')])
        indented_block = "                    if not address_filled_success:\n" + indented_block[4:] 
        content = content[:match2.start()] + indented_block + content[match2.end():]
        print("Fixed PLACE_ORDER address block.")

    with open('openclaw_task_fixed.py', 'w') as f:
        f.write(content)
    print("Done writing openclaw_task_fixed.py")

if __name__ == '__main__':
    main()
