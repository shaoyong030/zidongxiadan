import pandas as pd
from playwright.sync_api import sync_playwright
import time
import re
import pyperclip
import os 

def run_pdd_to_taobao_task(stop_event):
    log_buffer = []
    
    def dlog(msg):
        t_str = time.strftime('%H:%M:%S')
        if msg.startswith('\n'):
            out = f"\n[{t_str}] {msg.lstrip()}"
        else:
            out = f"[{t_str}] {msg}"
        print(out)
        log_buffer.append(out)

    dlog("\n" + "="*50)
    dlog("🎬 [系统启动] 全链路闭环 V75.0 (无痕合单备注+JS级穿透提交版)")
    dlog("="*50)

    # 移除了 newly_merged 的统计，因为废弃了"合并发货"的文字备注
    stats = {"already_green": 0, "logistics_updated": 0, "already_merged": 0, "newly_placed": 0}
    processed_sns = set() 
    merged_sns = None 
    merge_success_map = {} 
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
                os.system('open -n -a "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir="/tmp/pdd_taobao_auto_profile"')
                dlog("⏳ 等待浏览器启动 (4秒)...")
                time.sleep(4) 
                
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
            
            qty_col_idx = -1
            buyer_col_idx = -1
            try:
                col_indices = pdd_page.evaluate('''() => {
                    let ths = document.querySelectorAll('th');
                    let q_idx = -1, b_idx = -1;
                    for(let i=0; i<ths.length; i++) {
                        if(ths[i].innerText.includes('数量')) q_idx = i;
                        if(ths[i].innerText.includes('买家')) b_idx = i;
                    }
                    return {qty: q_idx, buyer: b_idx};
                }''')
                qty_col_idx = col_indices.get('qty', -1)
                buyer_col_idx = col_indices.get('buyer', -1)
            except: pass

            order_rows = pdd_page.locator('tr[data-testid="beast-core-table-body-tr"]').all()
            dlog(f"\n📊 [扫描] 当前大盘发现 {len(order_rows)} 个数据块...")

            risky_buyers = set()
            for row in order_rows:
                try: txt = row.locator('xpath=..').inner_text().replace('\n', ' ')
                except: txt = row.inner_text().replace('\n', ' ')
                
                if "此订单需要平台人工审核，请暂时不要发货" in txt:
                    buyer_name = ""
                    if buyer_col_idx != -1:
                        try: buyer_name = row.locator(f'td:nth-child({buyer_col_idx + 1})').inner_text().strip()
                        except: pass
                    if not buyer_name:
                        match = re.search(r'([A-Za-z0-9\u4e00-\u9fa5_]+\*\*\*)', txt)
                        if match: buyer_name = match.group(1)
                    if buyer_name: risky_buyers.add(buyer_name)

            if risky_buyers:
                dlog(f"   ∟ [动态风控] ⚠️ 发现高危买家名单: {risky_buyers}，将精准拦截其所有新单及合单！")

            action, tb_id, current_sn, target_tb_link, current_quantity = "", "", "", "", 1

            for index, row in enumerate(order_rows):
                try: txt = row.locator('xpath=..').inner_text().replace('\n', ' ')
                except: txt = row.inner_text().replace('\n', ' ')

                sn_match = re.search(r'\d{6}-\d{15,}', txt)
                sn = sn_match.group() if sn_match else f"UNKNOWN-{int(time.time()*1000)}"
                all_seen_pdd_sns.add(sn)
                
                pdd_id_match = re.search(r'ID:\s*(\d+)', txt)
                pdd_id = pdd_id_match.group(1) if pdd_id_match else "未提取到ID"

                current_buyer = "未知买家"
                if buyer_col_idx != -1:
                    try: current_buyer = row.locator(f'td:nth-child({buyer_col_idx + 1})').inner_text().strip()
                    except: pass
                if current_buyer == "未知买家" or not current_buyer:
                    match = re.search(r'([A-Za-z0-9\u4e00-\u9fa5_]+\*\*\*)', txt)
                    if match: current_buyer = match.group(1)

                if "绿色" in txt and "待发货" in txt and sn not in seen_green_sns:
                    seen_green_sns.add(sn); stats["already_green"] += 1
                elif "合并" in txt and sn not in seen_merged_sns:
                    seen_merged_sns.add(sn); stats["already_merged"] += 1

                if sn in processed_sns: continue

                dlog(f"  👉 [判定] 分析订单: {sn} | 买家: {current_buyer}")

                if "绿色" in txt and "待发货" in txt:
                    tb_match = re.search(r'27\d{17}', txt)
                    if tb_match:
                        tid = tb_match.group()
                        if tid not in already_checked_logistics:
                            dlog(f"     ∟ 命中[逻辑1]: 标绿待查物流 ({tid})")
                            action, tb_id, current_sn = "LOGISTICS", tid, sn; break
                
                elif sn in merge_success_map:
                    dlog(f"     ∟ 命中[逻辑2]: 购物车合单成功，为该子订单回填并打绿标！")
                    action, tb_id, current_sn = "MARK_GREEN_MERGED", merge_success_map[sn], sn; break

                elif "合并" in txt:
                    dlog(f"     ∟ 命中[逻辑3]: 已有历史合并备注，忽略")
                    processed_sns.add(sn); continue
                else:
                    if current_buyer in risky_buyers:
                        dlog(f"     ∟ [跳过] 🛡️ 防守机制触发：买家【{current_buyer}】处于风控期。")
                        continue 

                    if merged_sns is None:
                        dlog(f"     ∟ 首次遇到白单，跳往合并中心执行【购物车合单引擎】...")
                        action = "PROCESS_MERGE_PAGE"; break 
                    
                    if sn in merged_sns:
                        # 🚀 V75.0 核心逻辑修改：如果单号在合并名单中，但上一轮合单没买成功，直接屏蔽过滤，不打任何备注
                        dlog(f"     ∟ [跳过] 该单虽在合并名单中，但未下单成功，将其列入过滤黑名单。")
                        processed_sns.add(sn)
                        continue
                    else:
                        dlog(f"     ∟ 命中[逻辑4]: 纯新白单！单买发车...")
                        if pdd_id in mapping_dict:
                            target_tb_link = mapping_dict[pdd_id]
                            extracted_qty = 1
                            if qty_col_idx != -1:
                                try:
                                    qty_text = row.locator(f'td:nth-child({qty_col_idx + 1})').inner_text()
                                    match = re.search(r'\d+', qty_text)
                                    if match: extracted_qty = int(match.group())
                                except: pass

                            dlog(f"     ∟ 匹配成功！准备单笔下单，需拍数量: {extracted_qty}。")
                            action, current_sn, current_quantity = "PLACE_ORDER", sn, extracted_qty; break
                        else:
                            dlog(f"     ∟ 匹配失败！Excel 里没有此 ID。")
                            processed_sns.add(sn); continue

            if not action: break

            # ==========================================
            # 执行区 0：购物车合单引擎 (MERGE_ENGINE) 
            # ==========================================
            if action == "PROCESS_MERGE_PAGE":
                dlog("\n🔗 [执行] 进入合并中心，全自动处理加购合单...")
                pdd_page.goto("https://mms.pinduoduo.com/orders/merge")
                time.sleep(4)
                merged_sns = set() 

                order_rows = pdd_page.locator('tr').all()
                merge_groups = []
                current_group = None

                for row in order_rows:
                    try: txt = row.inner_text().replace('\n', ' ')
                    except: continue

                    if "买家信息" in txt or "合并发货" in txt:
                        if current_group and len(current_group['items']) > 0: merge_groups.append(current_group)
                        current_group = {'header_row': row, 'items': []}
                    else:
                        sn_match = re.search(r'\d{6}-\d{15,}', txt)
                        if sn_match and current_group is not None:
                            sn = sn_match.group()
                            merged_sns.add(sn)
                            pdd_id_match = re.search(r'ID:\s*(\d+)', txt)
                            qty_match = re.search(r'\s+(\d+)\s+\d+\.\d{2}', txt)
                            qty = int(qty_match.group(1)) if qty_match else 1
                            current_group['items'].append({'sn': sn, 'pdd_id': pdd_id_match.group(1) if pdd_id_match else None, 'qty': qty})
                if current_group and len(current_group['items']) > 0: merge_groups.append(current_group)

                dlog(f"   ∟ [扫描] 合并页面共解析出 {len(merge_groups)} 组待合订单。")

                for group in merge_groups:
                    header_row = group['header_row']
                    try:
                        view_btn = header_row.locator('a:has-text("查看")').first
                        if view_btn.is_visible(): view_btn.click(force=True); time.sleep(1)

                        phone_btn = header_row.locator('a:has-text("查看手机号")').first
                        if phone_btn.is_visible(): phone_btn.click(force=True); time.sleep(1.5)

                        pyperclip.copy("")
                        clip_text = ""
                        copy_btns = header_row.locator('a:has-text("复制")').all()
                        for btn in copy_btns:
                            try: btn.click(force=True); time.sleep(1)
                            except: pass
                            clip_text = pyperclip.paste().replace('\n', ' ').replace('\r', ' ').strip()
                            if "省" in clip_text or "市" in clip_text or "区" in clip_text or "县" in clip_text:
                                break
                        raw_info = clip_text

                    except Exception as e:
                        dlog(f"   ∟ [警告] 提取合单买家信息失败，跳过: {e}"); continue

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

                    if buyer_name in risky_buyers:
                        dlog(f"   ∟ [风控拦截] 组内买家【{buyer_name}】在高危名单，放弃该组合单！")
                        continue

                    valid = True
                    for item in group['items']:
                        if not item['pdd_id'] or item['pdd_id'] not in mapping_dict:
                            dlog(f"   ∟ [跳过] 合单中有商品未映射 (ID: {item['pdd_id']})")
                            valid = False; break
                    if not valid: continue

                    dlog(f"   ∟ [购物车] 开始合单加购，买家:{buyer_name} | 共 {len(group['items'])} 件商品")
                    tb_page.bring_to_front()

                    for item in group['items']:
                        tb_page.goto(mapping_dict[item['pdd_id']])
                        time.sleep(3)
                        
                        qty = item['qty']
                        if qty > 1:
                            try:
                                qty_input = tb_page.locator('input.countValue, input.tb-text, input.count, input[title="请输入购买量"]').first
                                if qty_input.is_visible(): qty_input.fill(str(qty)); time.sleep(1)
                                else:
                                    for _ in range(qty - 1):
                                        plus_btn = tb_page.locator('.countValuePlus, .increase, .tb-increase, .mui-amount-btn-increase, a[title="增加数量"], button.plus, span.plus, a:has-text("+")').first
                                        if plus_btn.is_visible(): plus_btn.click(force=True); time.sleep(0.5)
                            except: pass

                        try:
                            cart_selector = 'a:has-text("加入购物车"), button:has-text("加入购物车"), .add-cart, .icon-taobaojiarugouwuche-xianxing, .EmphasizeButtonList--CXEuu6Sg > div:first-child'
                            tb_page.locator(cart_selector).first.click(force=True)
                            time.sleep(2.5) 
                        except Exception as e:
                            dlog(f"   ∟ [报错] 加入购物车失败: {e}"); valid = False; break

                    if not valid: continue

                    tb_page.goto("https://cart.taobao.com/cart.htm")
                    time.sleep(4)

                    dlog("   ∟ [动作] 在购物车中智能勾选新加商品...")
                    try:
                        try:
                            select_all = tb_page.locator('label:has-text("全选") input[type="checkbox"]').first
                            if select_all.is_visible() and select_all.is_checked():
                                select_all.uncheck(force=True)
                                time.sleep(0.5)
                        except: pass
                        
                        all_boxes = tb_page.locator('input[type="checkbox"]').all()
                        for box in all_boxes:
                            try:
                                if box.is_checked(): box.uncheck(force=True)
                            except: pass
                        time.sleep(1)

                        item_boxes = tb_page.locator('div[class*="cartStatus--"] input[type="checkbox"], div.trade-cart-item-status input[type="checkbox"]').all()
                        target_num = len(group['items'])
                        clicked = 0
                        
                        for i in range(min(target_num, len(item_boxes))):
                            try:
                                item_boxes[i].check(force=True); clicked += 1; time.sleep(0.6)
                            except:
                                try: item_boxes[i].click(force=True); clicked += 1; time.sleep(0.5)
                                except: pass
                                
                        dlog(f"   ∟ [成功] 已物理勾选 {clicked} 件商品。")
                    except Exception as e:
                        dlog(f"   ∟ [报错] 购物车勾选过程执行异常: {e}")
                        
                    time.sleep(3)

                    dlog("   ∟ [动作] 点击结算按钮...")
                    try:
                        settle_selector = 'div:has-text("结算").btn--QDjHtErD, div.trade-cart-btn-submit > div.btn--QDjHtErD, #J_Go, a:has-text("结算")'
                        tb_page.locator(settle_selector).last.click(force=True)
                        time.sleep(4)
                    except Exception as e:
                        dlog(f"   ∟ [报错] 购物车点击结算失败: {e}")
                        try:
                            tb_page.evaluate('''() => {
                                let btns = Array.from(document.querySelectorAll('div, button, a'));
                                let settleBtn = btns.find(el => el.innerText && el.innerText.trim() === '结算' && (el.className.includes('btn--') || el.className.includes('submit')));
                                if(settleBtn) settleBtn.click();
                            }''')
                            time.sleep(4)
                        except: continue

                    address_filled_success = False 
                    try:
                        new_addr_btn = tb_page.locator('text=使用新地址').first
                        if new_addr_btn.is_visible(timeout=8000):
                            new_addr_btn.click(force=True); time.sleep(2)
                    except: pass

                    try:
                        try:
                            address_context = tb_page.frame_locator('iframe').last
                            address_context.locator('button:has-text("保存")').wait_for(timeout=2000)
                        except:
                            address_context = tb_page

                        smart_btn = address_context.locator('button:has-text("填入"), button:has-text("解析")').first
                        
                        if smart_btn.is_visible():
                            dlog("   ∟ [动作] 发现智能解析框，使用标准填充...")
                            smart_box = address_context.locator('textarea').first
                            smart_box.fill(f"{buyer_name} {buyer_phone} {buyer_address}")
                            time.sleep(0.5)
                            smart_btn.click(force=True)
                            time.sleep(2)
                        else:
                            dlog("   ∟ [动作] 未发现解析按钮，启动正则手动强力填表...")
                            address_context.locator('input#fullName, input[placeholder*="姓名"]').first.fill(buyer_name)
                            address_context.locator('input#mobile, input[placeholder*="手机"]').first.fill(buyer_phone)
                            
                            detail_addr = buyer_address
                            region_match = re.match(r'^(.*?省|.*?自治区|上海市?|北京市?|天津市?|重庆市?)(.*?市|.*?自治州|.*?地区|.*?盟)?(.*?区|.*?县|.*?市|.*?旗)?(.*)$', buyer_address.replace(' ', ''))
                            if region_match and region_match.group(4):
                                detail_addr = region_match.group(4)
                            
                            detail_box = address_context.locator('textarea#addressDetail, textarea[placeholder*="详细地址"], .cndzk-entrance-associate-area-textarea').last
                            detail_box.fill(detail_addr)
                            time.sleep(1)

                        try:
                            region_text = address_context.locator('.cndzk-entrance-division-header-click-input, .ant-select-selection-item').first.inner_text(timeout=2000)
                        except: region_text = "请选择"
                        
                        if "请选择" in region_text or not region_text.strip():
                            dlog("   ∟ [警告] 地区未全选，启动正则强行补全下拉框...")
                            address_context.locator('.cndzk-entrance-division-header-click, .ant-select-selector').first.click(force=True)
                            time.sleep(1)
                            
                            region_match = re.match(r'^(.*?省|.*?自治区|上海市?|北京市?|天津市?|重庆市?)(.*?市|.*?自治州|.*?地区|.*?盟)?(.*?区|.*?县|.*?市|.*?旗)?', buyer_address.replace(' ', ''))
                            parts_to_click = []
                            if region_match:
                                parts_to_click = [p for p in region_match.groups() if p]
                            else:
                                parts_to_click = [p.strip() for p in buyer_address.split() if p.strip()][:3]
                                
                            for part in parts_to_click:
                                if not part: continue
                                try:
                                    address_context.locator(f'li:has-text("{part}")').first.click(timeout=1000)
                                    time.sleep(0.5)
                                except:
                                    short = re.sub(r'[省市县区自治区]', '', part)
                                    if short and len(short) >= 2:
                                        try: address_context.locator(f'li:has-text("{short}")').first.click(timeout=1000); time.sleep(0.5)
                                        except: pass
                            
                            try: address_context.locator('li:has-text("暂不选择")').first.click(timeout=800); time.sleep(0.5)
                            except: 
                                try:
                                    first_opt = address_context.locator('li.cndzk-entrance-division-box-content-tag').first
                                    if first_opt.is_visible(): first_opt.click(timeout=800); time.sleep(0.5)
                                except: pass

                        address_context.locator('input#fullName, input[placeholder*="姓名"]').first.fill(buyer_name)
                        address_context.locator('input#mobile, input[placeholder*="手机"]').first.fill(buyer_phone)
                        time.sleep(1)

                        dlog("   ∟ [动作] 点击保存地址...")
                        save_btn = address_context.locator('button.next-btn-primary:has-text("保存"), button:has-text("保存")').first
                        try: save_btn.click(force=True)
                        except: save_btn.evaluate("node => node.click()")
                        time.sleep(2) 
                        
                        try:
                            confirm_btn = address_context.locator('button:has-text("确认"), button:has-text("确定")').first
                            if confirm_btn.is_visible():
                                confirm_btn.click(force=True)
                                time.sleep(2)
                        except: pass
                        
                        if address_context.locator('input#fullName').is_visible():
                            dlog("   ∟ [失败] ❌ 终极地址保存异常，表单仍停留，拦截提交！放弃该组合单！")
                        else:
                            address_filled_success = True

                    except Exception as e:
                        dlog(f"   ∟ [报错] 地址填写模块发生崩溃: {e}")

                    # 失败则直接continue跳过，不加备注
                    if not address_filled_success: 
                        continue

                    dlog("   ∟ [动作] 🚀 准备点击新版提交订单...")
                    # 🚀 V75.0 终极修复：使用底层JS同时对准内外层节点狂暴点击，抗击React渲染延迟
                    submit_success = False
                    for _ in range(4):
                        click_result = tb_page.evaluate('''() => {
                            let btnContainer = Array.from(document.querySelectorAll('div')).find(el => 
                                el.className && typeof el.className === 'string' && el.className.includes('btn--') && 
                                el.innerText && el.innerText.includes('提交订单')
                            );
                            if (btnContainer) {
                                let inner = btnContainer.querySelector('div');
                                if (inner) inner.click();
                                btnContainer.click();
                                return 'CLICKED_NEW_DIV';
                            }
                            let allNodes = Array.from(document.querySelectorAll('*'));
                            let textNode = allNodes.find(el => el.innerText && el.innerText.trim().startsWith('提交订单') && el.children.length === 0);
                            if (textNode) {
                                textNode.click();
                                if (textNode.parentElement) textNode.parentElement.click();
                                return 'CLICKED_LEAF_NODE';
                            }
                            return 'NOT_FOUND';
                        }''')
                        
                        if click_result != 'NOT_FOUND':
                            dlog(f"   ∟ [底层] 成功触发提交 ({click_result})")
                            submit_success = True
                            break
                        time.sleep(1.5)
                        
                    if not submit_success:
                        dlog("   ∟ [失败] ❌ 尝试多次仍未找到提交按钮，放弃该合单！")
                        continue

                    time.sleep(8) 
                    dlog("   ∟ [动作] 🔍 前往【已买到的宝贝】抓取合单新单号...")
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
                        dlog(f"   ∟ [失败] ❌ 警告：未找到合单待付款的新订单！")
                        continue
                    else:
                        dlog(f"   ∟ [成功] ✅ 成功生成合单淘宝总单号: {tb_order_id}")
                        for item in group['items']:
                            merge_success_map[item['sn']] = tb_order_id 

                continue 

            # ==========================================
            # 执行区 0.5：回填已成功合单的子订单 
            # ==========================================
            elif action == "MARK_GREEN_MERGED":
                dlog(f"\n🏷️ [执行] 为已购物车结算的合单只填单号并打绿标: {current_sn}")
                try:
                    current_order_block = pdd_page.locator(f'tbody:has-text("{current_sn}")').last
                    remark_btn = current_order_block.locator('a:has-text("添加备注"), a:has-text("修改备注")').first
                    remark_btn.click(force=True); time.sleep(1.5)
                    
                    # 🚀 V75.0 绝对纯净回填，不加“合并发货”等任何冗余文字
                    pdd_page.locator('textarea.note-textarea').first.fill(str(tb_id))
                    time.sleep(1)
                    
                    green_btn = pdd_page.locator('div[data-tracking-click-viewid="el_web_mark_shared"]:has-text("绿色")').first
                    try: green_btn.click(force=True)
                    except: green_btn.evaluate("node => node.click()")
                    time.sleep(1)
                    
                    pdd_page.locator('button').filter(has_text="保存").last.click(force=True)
                    dlog("   ∟ [成功] 子订单闭环打通！")
                    processed_sns.add(current_sn); stats["newly_placed"] += 1
                    del merge_success_map[current_sn] 
                except Exception as e:
                    dlog(f"   ∟ [报错] 合单子订单回填异常: {e}"); processed_sns.add(current_sn)
                continue


            # ==========================================
            # 执行区 1：普通单笔自动下单 
            # ==========================================
            elif action == "PLACE_ORDER":
                dlog(f"\n🛒 [执行] 开始普通全自动淘宝下单: {current_sn}")
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

                    if current_quantity > 1:
                        dlog(f"   ∟ [动作] 检测到需下单数量为 {current_quantity}，开始调整淘宝数量...")
                        try:
                            qty_input = tb_page.locator('input.countValue, input.tb-text, input.count, input[title="请输入购买量"]').first
                            if qty_input.is_visible():
                                qty_input.fill(str(current_quantity))
                                time.sleep(1)
                            else:
                                for _ in range(current_quantity - 1):
                                    plus_btn = tb_page.locator('.countValuePlus, .increase, .tb-increase, .mui-amount-btn-increase, a[title="增加数量"], button.plus, span.plus, a:has-text("+")').first
                                    if plus_btn.is_visible(): plus_btn.click(force=True); time.sleep(0.5)
                        except: pass

                    try:
                        tb_page.get_by_text("立即购买").first.click(force=True); time.sleep(4)
                    except Exception as e:
                        dlog(f"   ∟ [失败] ❌ 淘宝点击立即购买失败: {e}"); processed_sns.add(current_sn); continue

                    address_filled_success = False 
                    try:
                        new_addr_btn = tb_page.locator('text=使用新地址').first
                        if new_addr_btn.is_visible(timeout=8000):
                            new_addr_btn.click(force=True); time.sleep(2)
                    except: pass

                    try:
                        try:
                            address_context = tb_page.frame_locator('iframe').last
                            address_context.locator('button:has-text("保存")').wait_for(timeout=2000)
                        except:
                            address_context = tb_page

                        smart_btn = address_context.locator('button:has-text("填入"), button:has-text("解析")').first
                        
                        if smart_btn.is_visible():
                            dlog("   ∟ [动作] 发现智能解析框，使用标准填充...")
                            smart_box = address_context.locator('textarea').first
                            smart_box.fill(f"{buyer_name} {buyer_phone} {buyer_address}")
                            time.sleep(0.5)
                            smart_btn.click(force=True)
                            time.sleep(2)
                        else:
                            dlog("   ∟ [动作] 未发现解析按钮，启动正则手动强力填表...")
                            address_context.locator('input#fullName, input[placeholder*="姓名"]').first.fill(buyer_name)
                            address_context.locator('input#mobile, input[placeholder*="手机"]').first.fill(buyer_phone)
                            
                            detail_addr = buyer_address
                            region_match = re.match(r'^(.*?省|.*?自治区|上海市?|北京市?|天津市?|重庆市?)(.*?市|.*?自治州|.*?地区|.*?盟)?(.*?区|.*?县|.*?市|.*?旗)?(.*)$', buyer_address.replace(' ', ''))
                            if region_match and region_match.group(4):
                                detail_addr = region_match.group(4)
                            
                            detail_box = address_context.locator('textarea#addressDetail, textarea[placeholder*="详细地址"], .cndzk-entrance-associate-area-textarea').last
                            detail_box.fill(detail_addr)
                            time.sleep(1)

                        try:
                            region_text = address_context.locator('.cndzk-entrance-division-header-click-input, .ant-select-selection-item').first.inner_text(timeout=2000)
                        except: region_text = "请选择"
                        
                        if "请选择" in region_text or not region_text.strip():
                            dlog("   ∟ [警告] 地区未全选，启动正则强行补全下拉框...")
                            address_context.locator('.cndzk-entrance-division-header-click, .ant-select-selector').first.click(force=True)
                            time.sleep(1)
                            
                            region_match = re.match(r'^(.*?省|.*?自治区|上海市?|北京市?|天津市?|重庆市?)(.*?市|.*?自治州|.*?地区|.*?盟)?(.*?区|.*?县|.*?市|.*?旗)?', buyer_address.replace(' ', ''))
                            parts_to_click = []
                            if region_match:
                                parts_to_click = [p for p in region_match.groups() if p]
                            else:
                                parts_to_click = [p.strip() for p in buyer_address.split() if p.strip()][:3]
                                
                            for part in parts_to_click:
                                if not part: continue
                                try:
                                    address_context.locator(f'li:has-text("{part}")').first.click(timeout=1000)
                                    time.sleep(0.5)
                                except:
                                    short = re.sub(r'[省市县区自治区]', '', part)
                                    if short and len(short) >= 2:
                                        try: address_context.locator(f'li:has-text("{short}")').first.click(timeout=1000); time.sleep(0.5)
                                        except: pass
                            
                            try: address_context.locator('li:has-text("暂不选择")').first.click(timeout=800); time.sleep(0.5)
                            except: 
                                try:
                                    first_opt = address_context.locator('li.cndzk-entrance-division-box-content-tag').first
                                    if first_opt.is_visible(): first_opt.click(timeout=800); time.sleep(0.5)
                                except: pass

                        address_context.locator('input#fullName, input[placeholder*="姓名"]').first.fill(buyer_name)
                        address_context.locator('input#mobile, input[placeholder*="手机"]').first.fill(buyer_phone)
                        time.sleep(1)

                        dlog("   ∟ [动作] 点击保存地址...")
                        save_btn = address_context.locator('button.next-btn-primary:has-text("保存"), button:has-text("保存")').first
                        try: save_btn.click(force=True)
                        except: save_btn.evaluate("node => node.click()")
                        time.sleep(2) 
                        
                        try:
                            confirm_btn = address_context.locator('button:has-text("确认"), button:has-text("确定")').first
                            if confirm_btn.is_visible():
                                confirm_btn.click(force=True)
                                time.sleep(2)
                        except: pass
                        
                        if address_context.locator('input#fullName').is_visible():
                            dlog("   ∟ [失败] ❌ 终极地址保存异常，表单仍停留，拦截提交！放弃该单！")
                            processed_sns.add(current_sn)
                        else:
                            address_filled_success = True

                    except Exception as e:
                        dlog(f"   ∟ [报错] 地址填写模块发生崩溃: {e}")
                        processed_sns.add(current_sn)

                    if not address_filled_success: continue

                    dlog("   ∟ [动作] 🚀 准备点击新版提交订单...")
                    submit_success = False
                    for _ in range(4):
                        click_result = tb_page.evaluate('''() => {
                            let btnContainer = Array.from(document.querySelectorAll('div')).find(el => 
                                el.className && typeof el.className === 'string' && el.className.includes('btn--') && 
                                el.innerText && el.innerText.includes('提交订单')
                            );
                            if (btnContainer) {
                                let inner = btnContainer.querySelector('div');
                                if (inner) inner.click();
                                btnContainer.click();
                                return 'CLICKED_NEW_DIV';
                            }
                            let allNodes = Array.from(document.querySelectorAll('*'));
                            let textNode = allNodes.find(el => el.innerText && el.innerText.trim().startsWith('提交订单') && el.children.length === 0);
                            if (textNode) {
                                textNode.click();
                                if (textNode.parentElement) textNode.parentElement.click();
                                return 'CLICKED_LEAF_NODE';
                            }
                            return 'NOT_FOUND';
                        }''')
                        
                        if click_result != 'NOT_FOUND':
                            dlog(f"   ∟ [底层] 成功触发提交 ({click_result})")
                            submit_success = True
                            break
                        time.sleep(1.5)
                        
                    if not submit_success:
                        dlog("   ∟ [失败] ❌ 尝试多次仍未找到提交按钮，放弃该单！")
                        processed_sns.add(current_sn)
                        continue
                        
                    time.sleep(8) 
                    dlog("   ∟ [动作] 🔍 抓取新单号...")
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
                        dlog(f"   ∟ [失败] ❌ 警告：未找到待付款的新订单！停止回填。"); processed_sns.add(current_sn); continue
                    else:
                        dlog(f"   ∟ [成功] ✅ 成功抓取到待付款淘宝订单号: {tb_order_id}")
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
            # 执行区 2：物流回填
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

        try: tb_page.close(); pdd_page.close()
        except: pass
        
        try: browser.disconnect() 
        except: pass
        
        status_note = "(手动停止)" if stop_event.is_set() else ""
        true_total_pdd = len(all_seen_pdd_sns)
        
        final_report = f"""本次任务 {status_note}，
大盘检测订单  {true_total_pdd}  单，已下单标绿{stats['already_green']}单，更新物流{stats['logistics_updated']}单；
发现历史已合并共{stats['already_merged']}单；

其余处理：
成功去淘宝下单(含购物车合单与单买){stats['newly_placed']}单，已回填单号并标绿。"""
        
        return "\n".join(log_buffer), final_report