import os
import re

file_path = '/Users/shaoyong/Desktop/zidongxiadan/openclaw_task.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                    address_filled_success = False 
                    try:
                        new_addr_btn = tb_page.locator('text=使用新地址').first
                        if new_addr_btn.is_visible(timeout=8000):
                            new_addr_btn.click(force=True); time.sleep(2)
                    except: pass

                    try:
                        address_context = tb_page.frame_locator('iframe').last
                        try:
                            address_context.locator('textarea, input#fullName').first.wait_for(timeout=5000)
                        except:
                            address_context = tb_page

                        smart_box = address_context.locator('textarea').first
                        if smart_box.is_visible():
                            dlog("   ∟ [动作] 发现智能输入框，打入地址并触发解析...")
                            smart_box.focus()
                            smart_box.fill(f"{buyer_name} {buyer_phone} {buyer_address}")
                            time.sleep(0.5)
                            tb_page.keyboard.press("Space")
                            time.sleep(1.5)
                            
                            try: 
                                address_context.locator('button:has-text("填入"), button:has-text("解析")').first.click(timeout=1000)
                                time.sleep(1.5)
                            except: pass

                        try: region_text = address_context.locator('.cndzk-entrance-division-header-click-input, .ant-select-selection-item').first.inner_text(timeout=2000)
                        except: region_text = "请选择"
                        
                        if "请选择" in region_text or not region_text.strip():
                            dlog("   ∟ [警告] 地区未全选，启动 JS 强行下拉补全...")
                            try:
                                address_context.locator('.cndzk-entrance-division-header-click, .ant-select-selector').first.click(force=True)
                                time.sleep(1)
                                
                                region_match = re.match(r'^(.*?省|.*?自治区|上海市?|北京市?|天津市?|重庆市?)(.*?市|.*?自治州|.*?地区|.*?盟)?(.*?区|.*?县|.*?市|.*?旗)?', buyer_address.replace(' ', ''))
                                if region_match: parts_to_click = [p for p in region_match.groups() if p]
                                else: parts_to_click = [p.strip() for p in buyer_address.split() if p.strip()][:3]
                                    
                                for part in parts_to_click:
                                    if not part: continue
                                    try:
                                        address_context.locator(f'li:has-text("{part}")').first.click(timeout=1500)
                                        time.sleep(0.5)
                                    except:
                                        short = re.sub(r'[省市县区自治区]', '', part)
                                        if short and len(short) >= 2:
                                            try: address_context.locator(f'li:has-text("{short}")').first.click(timeout=1500); time.sleep(0.5)
                                            except: pass
                                
                                try: address_context.locator('li:has-text("暂不选择")').first.click(timeout=800); time.sleep(0.5)
                                except: 
                                    try: address_context.locator('li.cndzk-entrance-division-box-content-tag').first.click(timeout=800); time.sleep(0.5)
                                    except: pass
                            except Exception as e:
                                dlog(f"   ∟ [报错] 下拉框补全失败: {e}")

                        address_context.locator('input#fullName, input[placeholder*="姓名"]').first.fill(buyer_name)
                        address_context.locator('input#mobile, input[placeholder*="手机"]').first.fill(buyer_phone)
                        
                        detail_addr = buyer_address
                        region_match = re.match(r'^(.*?省|.*?自治区|上海市?|北京市?|天津市?|重庆市?)(.*?市|.*?自治州|.*?地区|.*?盟)?(.*?区|.*?县|.*?市|.*?旗)?(.*)$', buyer_address.replace(' ', ''))
                        if region_match and region_match.group(4):
                            detail_addr = region_match.group(4)
                        try:
                            address_context.locator('textarea#addressDetail, textarea[placeholder*="详细地址"]').first.fill(detail_addr)
                        except: pass
                        time.sleep(1)

                        dlog("   ∟ [动作] 点击保存地址...")
                        save_btn = address_context.locator('button.next-btn-primary:has-text("保存"), button:has-text("保存")').first
                        try: save_btn.click(force=True)
                        except: save_btn.evaluate("node => node.click()")
                        time.sleep(2) 
                        
                        try:
                            confirm_btn = address_context.locator('button:has-text("确认"), button:has-text("确定")').first
                            if confirm_btn.is_visible():
                                dlog("   ∟ [动作] 出现地址纠错弹窗，点击确认！")
                                confirm_btn.click(force=True)
                                time.sleep(2)
                        except: pass
                        
                        try:
                            if address_context.locator('input#fullName').first.is_visible():
                                time.sleep(2)
                                if address_context.locator('input#fullName').first.is_visible():
                                    dlog("   ∟ [失败] ❌ 终极地址保存异常，表单被系统拦截卡住。")
                                else: address_filled_success = True
                            else: address_filled_success = True
                        except:
                            address_filled_success = True

                    except Exception as e:
                        dlog(f"   ∟ [报错] 地址模块严重崩溃: {e}")
                        processed_sns.add(current_sn)

                    if not address_filled_success:
                        processed_sns.add(current_sn)
                        continue"""

replace = """                    address_filled_success = False 
                    try:
                        new_addr_btn = tb_page.locator('text=使用新地址').first
                        if new_addr_btn.is_visible(timeout=5000):
                            new_addr_btn.click(force=True, timeout=2000); time.sleep(2)
                    except: pass

                    try:
                        address_context = tb_page.frame_locator('iframe').last
                        try:
                            address_context.locator('textarea, input#fullName').first.wait_for(timeout=3000)
                        except:
                            address_context = tb_page

                        smart_box = address_context.locator('textarea').first
                        if smart_box.is_visible():
                            dlog("   ∟ [动作] 发现智能输入框，打入地址并触发解析...")
                            try:
                                smart_box.click(timeout=2000)
                                time.sleep(0.1)
                                smart_box.fill("", timeout=1500)
                                smart_box.type(f"{buyer_name} {buyer_phone} {buyer_address}", delay=20, timeout=4000)
                                time.sleep(0.5)
                                tb_page.keyboard.press("Space")
                                time.sleep(1.5)
                                address_context.locator('button:has-text("填入"), button:has-text("解析")').first.click(timeout=2000)
                                time.sleep(1.5)
                            except: pass

                        try: region_text = address_context.locator('.cndzk-entrance-division-header-click-input, .ant-select-selection-item').first.inner_text(timeout=2000)
                        except: region_text = "请选择"
                        
                        if "请选择" in region_text or not region_text.strip():
                            dlog("   ∟ [警告] 地区未全选，启动 JS 强行下拉补全...")
                            try:
                                try:
                                    address_context.locator('.cndzk-entrance-division-header-click, .ant-select-selector').first.click(force=True, timeout=3000)
                                except:
                                    address_context.locator('.cndzk-entrance-division-header-click, .ant-select-selector').first.evaluate("node => node.click()", timeout=2000)
                                time.sleep(1)
                                
                                region_match = re.match(r'^(.*?省|.*?自治区|上海市?|北京市?|天津市?|重庆市?)(.*?市|.*?自治州|.*?地区|.*?盟)?(.*?区|.*?县|.*?市|.*?旗)?', buyer_address.replace(' ', ''))
                                if region_match: parts_to_click = [p for p in region_match.groups() if p]
                                else: parts_to_click = [p.strip() for p in buyer_address.split() if p.strip()][:3]
                                    
                                for part in parts_to_click:
                                    if not part: continue
                                    try:
                                        address_context.locator(f'li:has-text("{part}")').first.click(timeout=1500)
                                        time.sleep(0.5)
                                    except:
                                        short = re.sub(r'[省市县区自治区]', '', part)
                                        if short and len(short) >= 2:
                                            try: address_context.locator(f'li:has-text("{short}")').first.click(timeout=1500); time.sleep(0.5)
                                            except: pass
                                
                                try: address_context.locator('li:has-text("暂不选择")').first.click(timeout=800); time.sleep(0.5)
                                except: 
                                    try: address_context.locator('li.cndzk-entrance-division-box-content-tag').first.click(timeout=800); time.sleep(0.5)
                                    except: pass
                            except Exception as e:
                                dlog(f"   ∟ [报错] 下拉框补全失败: {e}")

                        try:
                            # 强化React防吞字补录
                            name_input = address_context.locator('input#fullName, input[placeholder*="姓名"]').first
                            name_input.click(timeout=2000)
                            name_input.fill("", timeout=1500)
                            name_input.type(buyer_name, delay=20, timeout=3000)
                        except Exception as e:
                            dlog(f"   ∟ [报错] 姓名输入超时: {e}")
                            
                        try:
                            phone_input = address_context.locator('input#mobile, input[placeholder*="手机"]').first
                            phone_input.click(timeout=2000)
                            phone_input.fill("", timeout=1500)
                            phone_input.type(buyer_phone, delay=20, timeout=3000)
                        except: pass
                        
                        detail_addr = buyer_address
                        region_match = re.match(r'^(.*?省|.*?自治区|上海市?|北京市?|天津市?|重庆市?)(.*?市|.*?自治州|.*?地区|.*?盟)?(.*?区|.*?县|.*?市|.*?旗)?(.*)$', buyer_address.replace(' ', ''))
                        if region_match and region_match.group(4):
                            detail_addr = region_match.group(4)
                        try:
                            addr_input = address_context.locator('textarea#addressDetail, textarea[placeholder*="详细地址"]').first
                            addr_input.click(timeout=2000)
                            addr_input.fill("", timeout=1500)
                            addr_input.type(detail_addr, delay=20, timeout=3000)
                        except: pass
                        time.sleep(1)

                        dlog("   ∟ [动作] 点击保存地址...")
                        save_btn = address_context.locator('button.next-btn-primary:has-text("保存"), button:has-text("保存")').first
                        try: save_btn.click(force=True, timeout=4000)
                        except: 
                            try: save_btn.evaluate("node => node.click()", timeout=2000)
                            except: pass
                        time.sleep(2) 
                        
                        try:
                            confirm_btn = address_context.locator('button:has-text("确认"), button:has-text("确定")').first
                            if confirm_btn.is_visible(timeout=1500):
                                dlog("   ∟ [动作] 出现地址纠错弹窗，点击确认！")
                                confirm_btn.click(force=True, timeout=2000)
                                time.sleep(2)
                        except: pass
                        
                        try:
                            if address_context.locator('input#fullName').first.is_visible(timeout=2000):
                                time.sleep(1.5)
                                if address_context.locator('input#fullName').first.is_visible(timeout=1000):
                                    dlog("   ∟ [失败] ❌ 终极地址保存异常，表单被系统拦截卡住。")
                                    try:
                                        err_text = address_context.locator('.next-form-item-help, .error-msg, .cndzk-entrance-division-error').first.inner_text(timeout=1000)
                                        if err_text: dlog(f"   ∟ [拦截详情] {err_text}")
                                    except: pass
                                else: address_filled_success = True
                            else: address_filled_success = True
                        except:
                            address_filled_success = True

                    except Exception as e:
                        dlog(f"   ∟ [报错] 地址模块严重崩溃: {e}")
                        processed_sns.add(current_sn)

                    if not address_filled_success:
                        processed_sns.add(current_sn)
                        continue"""

counts = content.count(target)
print("Find count:", counts)

if counts > 0:
    new_content = content.replace(target, replace)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced!")
else:
    print("Target not found exactly.")
