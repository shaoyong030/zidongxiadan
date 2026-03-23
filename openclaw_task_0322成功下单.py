import pandas as pd
from playwright.sync_api import sync_playwright
import time
import re
import pyperclip
import os  # 🚀 新增：调用 Mac 原生系统命令

def run_pdd_to_taobao_task(stop_event):
    log_buffer = []
    
    # 🚀 全局日志引擎升级：自动添加时间戳
    def dlog(msg):
        t_str = time.strftime('%H:%M:%S')
        if msg.startswith('\n'):
            out = f"\n[{t_str}] {msg.lstrip()}"
        else:
            out = f"[{t_str}] {msg}"
        print(out)
        log_buffer.append(out)

    dlog("\n" + "="*50)
    dlog("🎬 [系统启动] 全链路闭环 V66.3 (Mac原生隔离·标签绝对不关版)")
    dlog("="*50)

    stats = {"already_green": 0, "logistics_updated": 0, "already_merged": 0, "newly_merged": 0, "newly_placed": 0}
    processed_sns = set() 
    merged_sns = None 
    already_checked_logistics = set()
    seen_green_sns = set() 
    seen_merged_sns = set() 
    all_seen_pdd_sns = set()

    try:
        df = pd.read_excel('/Users/shaoyong/Desktop/zidongxiadan/商品下单链接映射表.xlsx')
        mapping_dict = dict(zip(df['拼多多商品ID'].astype(str), df['淘宝下单链接']))
        dlog(f"✅ [初始化] Excel映射表加载成功，共 {len(mapping_dict)} 个商品。")
    except Exception as e:
        dlog(f"❌ [初始化] Excel加载失败: {e}")
        return "\n".join(log_buffer), ""

    with sync_playwright() as p:
        try:
            dlog("🔄 [初始化] 正在探测 9222 端口是否存活...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            pdd_page = context.new_page()
            tb_page = context.new_page()
            dlog("✅ [初始化] 成功接管已存在的浏览器分身！")
        except:
            dlog("⚠️ [初始化] 端口未开启！正在呼叫 Mac 系统原生唤醒 Chrome...")
            try:
                # 🚀 引擎 2 终极进化：使用 Mac 原生 open 指令，彻底切断父子进程血缘！
                os.system('open -n -a "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir="/tmp/pdd_taobao_auto_profile"')
                
                dlog("⏳ 等待浏览器启动 (4秒)...")
                time.sleep(4) 
                
                # 浏览器作为完全独立的 App 启动后，再连接进去
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0]
                pdd_page = context.new_page()
                tb_page = context.new_page()
                dlog("✅ [初始化] 原生独立分身拉起并接管成功！")
            except Exception as e:
                dlog(f"❌ [致命错误] 浏览器拉起彻底失败，请检查: {e}")
                return "\n".join(log_buffer), ""

        while True:
            if stop_event.is_set(): break

            pdd_page.bring_to_front()
            pdd_page.goto("https://mms.pinduoduo.com/orders/list?tab=1")
            
            try:
                pdd_page.wait_for_selector('tr[data-testid="beast-core-table-body-tr"]', state='visible', timeout=15000)
            except: pass
            time.sleep(2.5)
            
            order_rows = pdd_page.locator('tr[data-testid="beast-core-table-body-tr"]').all()
            dlog(f"\n📊 [扫描] 当前页面发现 {len(order_rows)} 个数据块...")
            
            action, tb_id, current_sn, target_tb_link = "", "", "", ""

            for index, row in enumerate(order_rows):
                try: txt = row.locator('xpath=..').inner_text().replace('\n', ' ')
                except: txt = row.inner_text().replace('\n', ' ')

                sn_match = re.search(r'\d{6}-\d{15,}', txt)
                sn = sn_match.group() if sn_match else f"UNKNOWN-{int(time.time()*1000)}"
                all_seen_pdd_sns.add(sn)
                
                pdd_id_match = re.search(r'ID:\s*(\d+)', txt)
                pdd_id = pdd_id_match.group(1) if pdd_id_match else "未提取到ID"

                if "绿色" in txt and "待发货" in txt and sn not in seen_green_sns:
                    seen_green_sns.add(sn); stats["already_green"] += 1
                elif "合并" in txt and sn not in seen_merged_sns:
                    seen_merged_sns.add(sn); stats["already_merged"] += 1

                if sn in processed_sns: continue

                dlog(f"  👉 [判定] 分析订单: {sn} | ID: {pdd_id}")

                if "绿色" in txt and "待发货" in txt:
                    tb_match = re.search(r'27\d{17}', txt)
                    if tb_match:
                        tid = tb_match.group()
                        if tid not in already_checked_logistics:
                            dlog(f"     ∟ 命中[逻辑1]: 标绿待查物流 ({tid})")
                            action, tb_id, current_sn = "LOGISTICS", tid, sn; break
                elif "合并" in txt:
                    dlog(f"     ∟ 命中[逻辑2]: 已有合并备注，忽略")
                    processed_sns.add(sn); continue
                else:
                    if merged_sns is None:
                        dlog(f"     ∟ 首次遇到白单，跳往合并中心拉取名单...")
                        pdd_page.goto("https://mms.pinduoduo.com/orders/merge"); time.sleep(3)
                        merged_sns = set(re.findall(r'\d{6}-\d{15,}', pdd_page.content()))
                        action = "REFRESH_DOM"; break 
                    
                    if sn in merged_sns:
                        dlog(f"     ∟ 命中[逻辑3]: 该单在合并名单中，准备添加备注")
                        action, current_sn = "MARK_MERGE", sn; break
                    else:
                        dlog(f"     ∟ 命中[逻辑4]: 纯新白单！检查 Excel 映射...")
                        if pdd_id in mapping_dict:
                            target_tb_link = mapping_dict[pdd_id]
                            dlog(f"     ∟ 匹配成功！准备下单。")
                            action, current_sn = "PLACE_ORDER", sn; break
                        else:
                            dlog(f"     ∟ 匹配失败！Excel 里没有此 ID。")
                            processed_sns.add(sn); continue

            if action == "REFRESH_DOM": continue 
            if not action: break

            # ==========================================
            # 执行区 1：自动下单 
            # ==========================================
            if action == "PLACE_ORDER":
                dlog(f"\n🛒 [执行] 开始全自动淘宝下单: {current_sn}")
                try:
                    current_order_block = pdd_page.locator(f'tbody:has-text("{current_sn}")').last
                    current_order_block.locator('a:has-text("查看")').first.click(force=True); time.sleep(1)
                    phone_btn = current_order_block.locator('a:has-text("查看手机号")')
                    if phone_btn.count() > 0: phone_btn.first.click(force=True); time.sleep(1.5)

                    copy_btn = current_order_block.locator('a:has-text("复制完整信息")')
                    if copy_btn.count() > 0:
                        pyperclip.copy("") 
                        copy_btn.first.click(force=True); time.sleep(1)
                    else:
                        dlog("   ∟ [失败] ❌ 未找到【复制完整信息】按钮。"); processed_sns.add(current_sn); continue

                    raw_info = pyperclip.paste().replace('\n', ' ').replace('\r', ' ').strip()
                    phone_match = re.search(r'(1[3-9]\d{9}|0\d{2,3}-\d{7,8})', raw_info)
                    
                    if phone_match:
                        buyer_phone = phone_match.group(1)
                        buyer_name = raw_info[:phone_match.start()].strip()
                        buyer_address = raw_info[phone_match.end():].strip()
                    else:
                        parts = [p.strip() for p in raw_info.split() if p.strip()]
                        if len(parts) >= 3: buyer_name, buyer_phone, buyer_address = parts[0], parts[1], " ".join(parts[2:])
                        else: buyer_name, buyer_phone, buyer_address = "未识别", "18600000000", raw_info

                    buyer_name = re.sub(r'[,，\s]+', ' ', buyer_name).strip()
                    name_tag = re.search(r'\[.*?\]|\(.*?\)|【.*?】', buyer_name)
                    if name_tag:
                        buyer_address += " " + name_tag.group()
                        buyer_name = re.sub(r'\[.*?\]|\(.*?\)|【.*?】', '', buyer_name).strip()
                    if not buyer_name: buyer_name = "拼多多客户"
                    buyer_address = re.sub(r'[,，]+', ' ', buyer_address).strip()
                    if not str(buyer_phone).startswith('1'): buyer_phone = "18600000000"

                    dlog(f"   ∟ [提取成功] 姓名:{buyer_name} | 电话:{buyer_phone} | 地址:{buyer_address[:10]}...")

                    tb_page.bring_to_front()
                    tb_page.goto(target_tb_link); time.sleep(3)

                    try:
                        tb_page.get_by_text("立即购买").first.click(force=True); time.sleep(4)
                    except Exception as e:
                        dlog(f"   ∟ [失败] ❌ 淘宝点击立即购买失败: {e}"); processed_sns.add(current_sn); continue

                    try:
                        new_addr_btn = tb_page.get_by_text("使用新地址").first
                        new_addr_btn.wait_for(state="visible", timeout=8000)
                        new_addr_btn.click(force=True); time.sleep(2)
                    except: pass

                    address_filled_success = False 
                    
                    try:
                        address_frame = tb_page.frame_locator('iframe').last
                        address_textarea = address_frame.locator('.cndzk-entrance-associate-area-textarea').first
                        
                        smart_text = f"{buyer_name} {buyer_phone} {buyer_address}"
                        
                        dlog("   ∟ [动作] 自动填入地址信息并触发智能解析...")
                        address_textarea.focus()
                        address_textarea.fill(smart_text)
                        time.sleep(0.5)
                        
                        tb_page.keyboard.type(" ", delay=50) 
                        time.sleep(2)
                        
                        try:
                            address_frame.locator('button:has-text("填入"), button:has-text("解析")').first.click(timeout=1500)
                            time.sleep(2) 
                        except: pass
                            
                        region_text = address_frame.locator('.cndzk-entrance-division-header-click-input').inner_text()
                        if "请选择" in region_text:
                            dlog("   ∟ [警告] ⚠️ 发现地址栏未选全，启动强行修补...")
                            address_frame.locator('.cndzk-entrance-division-header-click').first.click(force=True)
                            time.sleep(1) 
                            
                            addr_parts = [p.strip() for p in buyer_address.split() if p.strip()]
                            for part in addr_parts[:4]: 
                                if len(part) >= 8 or any(c in part for c in ['路', '号', '弄', '室', '栋', '巷']): break 
                                try:
                                    address_frame.locator(f'li:has-text("{part}")').first.click(timeout=800)
                                    time.sleep(0.5)
                                except:
                                    try:
                                        short = part.replace("省","").replace("市","").replace("区","").replace("县","").replace("自治区","")
                                        if short: 
                                            address_frame.locator(f'li:has-text("{short}")').first.click(timeout=800)
                                            time.sleep(0.5)
                                    except: pass 
                                        
                            if address_frame.locator('.cndzk-entrance-division-box-content').is_visible():
                                try:
                                    address_frame.locator('li:has-text("暂不选择")').first.click(timeout=800)
                                    time.sleep(0.5)
                                except: 
                                    try:
                                        first_opt = address_frame.locator('li.cndzk-entrance-division-box-content-tag').first
                                        if first_opt.is_visible():
                                            first_opt.click(timeout=800)
                                            time.sleep(0.5)
                                    except: pass

                        address_frame.locator('#fullName').first.fill(buyer_name)
                        address_frame.locator('#mobile').first.fill(buyer_phone)
                        time.sleep(1)

                        dlog("   ∟ [动作] 点击保存地址...")
                        save_btn = address_frame.locator('button.next-btn-primary:has-text("保存")').first
                        try: save_btn.click(force=True)
                        except: save_btn.evaluate("node => node.click()")
                        time.sleep(2) 
                        
                        try:
                            confirm_btn = address_frame.locator('button:has-text("确认"), button:has-text("确定")').first
                            if confirm_btn.is_visible():
                                dlog("   ∟ [动作] 发现淘宝地址纠错弹窗，强行点击确认！")
                                confirm_btn.click(force=True)
                                time.sleep(2)
                        except: pass
                        
                        if address_frame.locator('.cndzk-entrance-associate-area-textarea').is_visible():
                            dlog("   ∟ [失败] ❌ 终极地址保存异常，拦截提交！放弃该单！")
                            processed_sns.add(current_sn); continue 
                        else:
                            address_filled_success = True

                    except Exception as e:
                        dlog(f"   ∟ [报错] 填写地址发生异常: {e}"); processed_sns.add(current_sn); continue

                    if not address_filled_success: continue

                    dlog("   ∟ [动作] 🚀 提交订单...")
                    submit_btn = tb_page.get_by_text("提交订单").first
                    try: submit_btn.click(force=True)
                    except: submit_btn.evaluate("node => node.click()")
                        
                    dlog("   ∟ [动作] 👀 强制停留 8 秒等待跳转支付宝...")
                    time.sleep(8) 

                    dlog("   ∟ [动作] 🔍 前往【已买到的宝贝】抓取新单号...")
                    tb_page.goto("https://buyertrade.taobao.com/trade/itemlist/list_bought_items.htm")
                    time.sleep(4) 
                    
                    tb_order_id = tb_page.evaluate(r'''() => {
                        const elements = Array.from(document.querySelectorAll('*'));
                        const pendingEl = elements.find(el => el.innerText && el.innerText.trim() === '等待买家付款');
                        if (!pendingEl) return '下单未成功';
                        
                        let parent = pendingEl;
                        for(let i=0; i<8; i++) { if(parent.parentElement) parent = parent.parentElement; }
                        
                        const match = parent.innerText.match(/订单号[^\d]*(\d{15,25})/);
                        return match ? match[1] : '单号提取失败';
                    }''')
                    
                    if tb_order_id in ["下单未成功", "单号提取失败"]:
                        dlog(f"   ∟ [失败] ❌ 警告：未找到待付款的新订单！停止回填。")
                        processed_sns.add(current_sn); continue
                    else:
                        dlog(f"   ∟ [成功] ✅ 成功抓取到待付款淘宝订单号: {tb_order_id}")

                        dlog("   ∟ [动作] 返回拼多多回填单号并标记绿色...")
                        pdd_page.bring_to_front()
                        time.sleep(1)
                        try:
                            current_order_block = pdd_page.locator(f'tbody:has-text("{current_sn}")').last
                            remark_btn = current_order_block.locator('a:has-text("添加备注"), a:has-text("修改备注")').first
                            remark_btn.click(force=True); time.sleep(1.5)
                            
                            pdd_page.locator('textarea.note-textarea').first.fill(str(tb_order_id))
                            time.sleep(1)
                            
                            green_btn = pdd_page.locator('div[data-tracking-click-viewid="el_web_mark_shared"]:has-text("绿色")').first
                            try: green_btn.click(force=True)
                            except: green_btn.evaluate("node => node.click()")
                            time.sleep(1)
                            
                            pdd_page.locator('button').filter(has_text="保存").last.click(force=True)
                            dlog("   ∟ [成功] 🏆 【任务大满贯】闭环打通！")
                            processed_sns.add(current_sn); stats["newly_placed"] += 1
                        except Exception as e:
                            dlog(f"   ∟ [报错] 回填备注异常: {e}"); processed_sns.add(current_sn)
                except Exception as e:
                    dlog(f"   ∟ [报错] 自动下单崩溃: {e}"); processed_sns.add(current_sn)

            # ==========================================
            # 执行区 2：物流回填 (V43.0 完美轰炸 + 锚点锁定修复)
            # ==========================================
            elif action == "LOGISTICS":
                dlog(f"\n📦 [执行] 开始查物流并回填: {current_sn}")
                tb_page.bring_to_front()
                tb_page.goto(f"https://buyertrade.taobao.com/trade/itemlist/list_bought_items.htm?order_sn={tb_id}")
                time.sleep(4)
                
                order_box = tb_page.locator(f"#shopOrderContainer_{tb_id}")
                if order_box.count() > 0:
                    status_text = order_box.locator(".shopInfoStatus--InnfaPAJ").inner_text()
                    if "已发货" in status_text:
                        try:
                            logistics_btn = order_box.locator('div.tbpc_boughtlist_orderItem_order_op:has-text("查看物流")').first
                            if logistics_btn.count() > 0:
                                logistics_btn.hover(); time.sleep(3) 

                                popover = tb_page.locator('.logisticPopoverContent--MaLWhCj9, .ant-popover-inner-content').last
                                if popover.is_visible():
                                    comp = popover.locator('.popoverHeader--imJbTf0J span').first.inner_text().strip()
                                    sn = popover.locator('.expressId--zegtKfpq').inner_text().strip()
                                    
                                    if comp and sn and not sn.startswith("6000"):
                                        dlog(f"   ∟ [成功] 抓取到物流: {comp} {sn}")
                                        pdd_page.bring_to_front()
                                        
                                        current_order_block = pdd_page.locator(f'tbody:has-text("{current_sn}")').last
                                        ship_btn = current_order_block.locator('div[data-tracking-click-viewid="ele_single_order_ship_button"] button').last
                                        
                                        if ship_btn.count() > 0:
                                            ship_btn.scroll_into_view_if_needed()
                                            ship_btn.click(force=True)
                                            dlog("   ∟ [动作] 已点击第一层【发货】")
                                            time.sleep(2.5)
                                            
                                            pdd_page.fill('#trackingNumber input', sn)
                                            pdd_page.locator('#shippingId input').click()
                                            pdd_page.locator('#shippingId input').fill(comp[:2])
                                            time.sleep(1)
                                            pdd_page.keyboard.press("Enter")
                                            time.sleep(1)
                                            
                                            pdd_page.locator('button[data-tracking-click-viewid="ele_confirm_shipment_shared"]').last.click(force=True)
                                            dlog("   ∟ [动作] 已点击蓝色【确认发货】")
                                            
                                            dlog("   ∟ [监控] 启动 10 秒扫描，捕捉二次弹窗...")
                                            kill_success = False
                                            for i in range(10):
                                                time.sleep(1)
                                                result = pdd_page.evaluate('''() => {
                                                    let attrBtns = document.querySelectorAll('button[data-tracking-click-viewid="makesure"]');
                                                    if (attrBtns.length > 0) {
                                                        attrBtns[attrBtns.length - 1].click();
                                                        return 'ATTR';
                                                    }
                                                    let allBtns = Array.from(document.querySelectorAll('button'));
                                                    for (let j = allBtns.length - 1; j >= 0; j--) {
                                                        if (allBtns[j].innerText && allBtns[j].innerText.includes('继续发货')) {
                                                            allBtns[j].click();
                                                            return 'TEXT';
                                                        }
                                                    }
                                                    return 'NONE';
                                                }''')
                                                
                                                if result != 'NONE':
                                                    dlog(f"   ∟ [突破] 💥 弹窗击杀成功 (触发模式: {result})！耗时 {i+1} 秒。")
                                                    kill_success = True
                                                    break
                                                    
                                            if not kill_success:
                                                dlog("   ∟ [状态] 10 秒内未检测到弹窗。")
                                            
                                            dlog(f"   ∟ [完成] 订单物流回填完毕。")
                                            processed_sns.add(current_sn)
                                            stats["logistics_updated"] += 1
                                            time.sleep(2)
                                        else: 
                                            dlog("   ∟ [跳过] 找不到拼多多的发货按钮。")
                                            already_checked_logistics.add(tb_id)
                                    else: 
                                        dlog("   ∟ [跳过] 物流信息提取异常(或为虚拟单号)。")
                                        already_checked_logistics.add(tb_id)
                                else: 
                                    dlog("   ∟ [跳过] 淘宝物流弹窗未能正确显示。")
                                    already_checked_logistics.add(tb_id)
                            else: 
                                dlog("   ∟ [跳过] 未找到淘宝的【查看物流】按钮。")
                                already_checked_logistics.add(tb_id)
                        except Exception as e: 
                            dlog(f"   ∟ [报错] 查询物流过程出错: {e}")
                            already_checked_logistics.add(tb_id)
                    else: 
                        dlog(f"   ∟ [跳过] 淘宝该订单当前状态为: 【{status_text}】，暂未发货。")
                        already_checked_logistics.add(tb_id)
                else: 
                    dlog(f"   ∟ [跳过] 在淘宝列表中找不到该单号 ({tb_id})。")
                    already_checked_logistics.add(tb_id)
                continue

            elif action == "MARK_MERGE":
                dlog(f"\n📝 [执行] 订单 {current_sn} 添加合并备注...")
                
                current_order_block = pdd_page.locator(f'tbody:has-text("{current_sn}")').last
                current_order_block.locator('a:has-text("备注")').first.click(force=True); time.sleep(1.5)
                
                pdd_page.locator('textarea.note-textarea').fill("合并发货")
                pdd_page.locator('button:has-text("保存")').last.click()
                processed_sns.add(current_sn); stats["newly_merged"] += 1

        # 🚀 降维修复：仅关闭本脚本创建的两个专属操作标签
        try: tb_page.close(); pdd_page.close()
        except: pass
        
        # 🚀 终极保险：强行拔网线（断开连接），绝对阻止 Playwright 销毁浏览器实体！
        try: browser.disconnect() 
        except: pass
        
        status_note = "(手动停止)" if stop_event.is_set() else ""
        true_total_pdd = len(all_seen_pdd_sns)
        
        final_report = f"""本次任务 {status_note}，
待发货列表订单  {true_total_pdd}  单，已下单标绿{stats['already_green']}单，更新物流{stats['logistics_updated']}单；
备注已标记合并无需下单共{stats['already_merged']}单；

其余处理：
命中合并发货{stats['newly_merged']}单，已补全备注；
成功去淘宝下单{stats['newly_placed']}单，已回填单号并标绿。"""
        
        return "\n".join(log_buffer), final_report