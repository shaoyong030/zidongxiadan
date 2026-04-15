import re

file_path = '/Users/shaoyong/Desktop/zidongxiadan/openclaw_task.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to inject the verification logic right before "address_filled_success = False" block
verification_code = """
                    address_filled_success = False 
                    dlog("   ∟ [动作] 检查已有地址是否匹配...")
                    try:
                        matched = tb_page.evaluate(f'''(buyer) => {{
                            let name = buyer.name;
                            let phone = buyer.phone;
                            let phoneLast4 = phone.length > 4 ? phone.substring(phone.length - 4) : phone;
                            
                            // 查找可能包含地址信息的区块
                            let allBlocks = Array.from(document.querySelectorAll('div, li')).filter(el => 
                                el.innerText && el.innerText.includes(name) && el.innerText.includes(phoneLast4) &&
                                el.innerText.length < 300 && el.children.length > 0
                            );
                            
                            if (allBlocks.length > 0) {{
                                // 找到最深层但也包含这些信息的节点，或者直接点击外层
                                let target = allBlocks[allBlocks.length - 1]; // 通常最后的都是最具体的元素
                                // 尝试从所有的 allBlocks 中找到一个包含 '修改' 或类似特征的卡片
                                let card = allBlocks.find(el => el.className && typeof el.className === 'string' && (el.className.toLowerCase().includes('address') || el.className.toLowerCase().includes('item')));
                                if (card) target = card;
                                
                                target.click();
                                let inner = target.querySelector('div, span');
                                if (inner) inner.click();
                                return true;
                            }}
                            return false;
                        }}''', {'name': buyer_name, 'phone': buyer_phone})
                        
                        if matched:
                            dlog("   ∟ [成功] ✅ 找到匹配的已有地址，已自动选中。")
                            address_filled_success = True
                            time.sleep(1.5)
                    except Exception as e:
                        dlog(f"   ∟ [提醒] 匹配已有地址失败，准备新增: {e}")
                        
                    if not address_filled_success:
"""

# Replace the initial setup
content = re.sub(
    r"(\s+)(address_filled_success = False\s*\n\s+try:\n\s+new_addr_btn = tb_page\.locator\('text=使用新地址'\)\.first)",
    lambda m: m.group(1) + verification_code.lstrip() + "                        try:\n                            new_addr_btn = tb_page.locator('text=使用新地址').first",
    content
)

# Replace the smart box locator
content = re.sub(
    r"smart_box = address_context\.locator\('textarea:not\(\[placeholder\*=\\\"详细地址\\\"\]\)'\)\.first",
    r"smart_box = address_context.locator('textarea[placeholder*=\"识别\"], textarea[placeholder*=\"粘贴\"], textarea[placeholder*=\"智能\"], .smart-address-textarea').first",
    content
)

# Ensure IFRAME fallback doesn't ruin the page (e.g. if the fallback happens, don't use tb_page for order remarks)
# Look for "except:\n                            address_context = tb_page"
# Change to "except:\n                            address_context = tb_page\n                            dlog('警告: 使用页面上下文')""
# Wait, actually, let's make sure the detail fields don't accidentally match the order remarks field.
# The order remark is `<textarea placeholder="选填，请先和商家协商一致再填写">` (or similar).
# Actually, the fix for smart box might be enough.
content = re.sub(
    r"(except:\s+)(address_context = tb_page)",
    r"\1\2\n                            if tb_page.locator('text=使用新地址').is_visible(): dlog('   ∟ [警告] 新增地址弹窗可能未打开！')",
    content
)

# And another important thing: After filling or at the end of the address block, we should re-verify if the selected address matches before submit!
# Let's insert a check before `if not address_filled_success:`
# Actually wait, `if not address_filled_success: continue` is right before `dlog("   ∟ [动作] 检查是否需要勾选支付币种...")`
# Let's modify the submission section to add a double-verification step.
final_check = """
                    # ========================================================================
                    # 提交前双重确认地址
                    # ========================================================================
                    dlog("   ∟ [动作] 提交订单前，最后确认地址是否匹配...")
                    try:
                        checked_matched = tb_page.evaluate(f'''(buyer) => {{
                            let name = buyer.name;
                            let phoneLast4 = buyer.phone.substring(buyer.phone.length - 4);
                            // 在“确认订单信息”之前的核心区域查找选中的地址
                            // 或者干脆全屏找有没有高亮的/当前显示的地址
                            let text = document.body.innerText;
                            if (text.includes(name) && text.includes(phoneLast4)) return true;
                            return false;
                        }}''', {'name': buyer_name, 'phone': buyer_phone})
                        
                        if not checked_matched:
                            dlog("   ∟ [严重失败] ❌ 最终准备提交的订单地址中，找不到目标买家姓名和手机号尾号！放弃提交。")
                            processed_sns.add(current_sn)
                            continue
                        else:
                            dlog("   ∟ [成功] ✅ 地址最终匹配无误，继续提交。")
                    except: pass
                    # ========================================================================

"""
# Find the check for `if not address_filled_success:` and insert after it
content = re.sub(
    r"(\s+)(if not address_filled_success:\s*\n\s+processed_sns\.add\(current_sn\)\s*\n\s+continue)",
    lambda m: m.group(0) + "\n" + m.group(1) + final_check.strip().replace("\n", "\n" + m.group(1)),
    content
)


with open('openclaw_task_patched.py', 'w', encoding='utf-8') as f:
    f.write(content)

