import os

file_path = '/Users/shaoyong/Desktop/zidongxiadan/openclaw_task.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                                if not is_rmb_checked():
                                    dlog("   ∟ [动作] ⚠️ Playwright点击失效，启动JS强点！")
                                    rmb_option.evaluate('''node => {
                                        let input = node.querySelector('input[type="checkbox"], input[type="radio"]');
                                        if (input && !input.checked) input.click();
                                    }''')
                                time.sleep(1)
                                
                            if is_rmb_checked():
                                dlog("   ∟ [状态] ✅ 【人民币】勾选成功。")"""

replacement = """                                if not is_rmb_checked():
                                    dlog("   ∟ [动作] ⚠️ Playwright点击失效，启动JS强点！")
                                    rmb_option.evaluate('''node => {
                                        let input = node.querySelector('input[type="checkbox"], input[type="radio"]');
                                        if (input && !input.checked) input.click();
                                    }''')
                                time.sleep(3)
                                
                            if is_rmb_checked():
                                dlog("   ∟ [状态] ✅ 【人民币】勾选成功。")
                                time.sleep(3)"""

counts = content.count(target)
print("Found target blocks:", counts)

if counts > 0:
    new_content = content.replace(target, replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced!")
else:
    print("Target not found.")

