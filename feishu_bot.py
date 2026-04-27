import requests
import time
import threading
import os
from openclaw_task import run_pdd_to_taobao_task

# ================= 配置区 =================
TOKEN = "8709491629:AAGbFv7KIEGDa6owztxjPOdFfDP0N69nD0g"
PROXIES = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
SCHEDULE_INTERVAL = 3600

# 🚀 硬编码你的专属 Chat ID
ADMIN_CHAT_ID = "8693156373"

stop_event = threading.Event()
task_thread = None
# =========================================

def dlog(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, proxies=PROXIES, timeout=15)
    except Exception as e:
        dlog(f"❌ [消息] 推送失败: {e}")

def send_photo(chat_id, photo_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as f:
            requests.post(url, data={'chat_id': chat_id}, files={'photo': f}, proxies=PROXIES)
    except Exception as e:
        send_message(chat_id, f"❌ 图片发送失败: {e}")

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        res = requests.get(url, params={"timeout": 20, "offset": offset}, proxies=PROXIES, timeout=30)
        return res.json()
    except Exception as e:
        dlog(f"获取消息失败, 请检查网络/代理模块: {e}")
        return None

def send_long_message(chat_id, text):
    parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for part in parts:
        send_message(chat_id, part)
        time.sleep(0.5)

def trigger_ai_fix(chat_id, text):
    """使用 Gemini API 自动分析并修复错误"""
    send_message(chat_id, "🔧 嗅探到异常！正在调用 Gemini AI 自动分析修复...")
    def _run_fix():
        try:
            from auto_fixer import run_fix_cycle
            fixed = run_fix_cycle()
            if fixed:
                send_message(chat_id, "✅ [Gemini 自修复] 补丁已应用并重启，请留意后续运行。")
            else:
                send_message(chat_id, "🔍 [Gemini 分析] 已完成分析，详情已发送。无可执行补丁或无新错误。")
        except Exception as e:
            dlog(f"[Gemini修复] 执行异常: {e}")
            send_message(chat_id, f"⚠️ Gemini 自修复模块异常: {e}")
    threading.Thread(target=_run_fix, daemon=True).start()

def task_wrapper(chat_id):
    global task_thread
    try:
        stop_event.clear()
        detailed_log, final_report = run_pdd_to_taobao_task(stop_event)
        if detailed_log: send_long_message(chat_id, detailed_log)
        if final_report: send_message(chat_id, final_report)
        
        # 嗅探失败特征
        if detailed_log and ("❌" in detailed_log or "报错" in detailed_log or "崩溃" in detailed_log or "严重失败" in detailed_log):
            # 取最后面的一段日志（最靠近死点的地方）
            bug_context = detailed_log[-1200:]
            ai_prompt = f"【系统自动求助】你好，我是你的自动打单外围巡航系统。刚才的下单任务中出现了异常或失败！请根据这份最新的现场错误日志，自主分析并修改代码修复它（特别是防封、选址、或匹配模块）。日志片段如下：\n{bug_context}"
            trigger_ai_fix(chat_id, ai_prompt)
            
    except Exception as e:
        send_message(chat_id, f"⚠️ 系统严重崩溃: {e}")
        ai_prompt = f"【系统自动求助】你好，我是你的自动打单巡航系统。脚本发生了不可预期的运行时异常闪退！报错信息为: {e}。请自主修改代码修复它。"
        trigger_ai_fix(chat_id, ai_prompt)
    finally:
        task_thread = None

def auto_scheduler():
    global task_thread
    import datetime
    
    # 启动时先稍等5秒，错开与系统启动消息的重叠，确保系统安稳启动
    time.sleep(5)
    
    while True:
        # 限制时间段：17点到次日8点不自动执行下单和发货
        now = datetime.datetime.now()
        if now.hour >= 17 or now.hour < 8:
            send_message(ADMIN_CHAT_ID, f"⏸ [自动巡检] 当前时间 {now.strftime('%H:%M')} 在非工作时段(17:00-08:00)，跳过自动执行。若急需更新请手动发送1")
        else:
            if not (task_thread and task_thread.is_alive()):
                send_message(ADMIN_CHAT_ID, "⏰ [自动巡检] 触发执行...")
                task_thread = threading.Thread(target=task_wrapper, args=(ADMIN_CHAT_ID,))
                task_thread.start()
                
        # 每次巡检结束后，再等待设定的间隔时间（1小时）
        time.sleep(SCHEDULE_INTERVAL)

def auto_fixer_scheduler():
    """Gemini 自修复守护线程：每 10 分钟巡检错误报告"""
    time.sleep(30)  # 启动延迟，等系统稳定
    while True:
        try:
            from auto_fixer import run_fix_cycle
            run_fix_cycle()
        except Exception as e:
            dlog(f"[自修复守护] 异常: {e}")
        time.sleep(600)  # 10分钟一次

def start_bot():
    global task_thread
    print("\n" + "*"*50)
    print("🤖 [系统] 搬砖通讯兵 V64.2 (寻路修正版) 上线！")
    print("🚦 监听中：1下单 / 2停止 / 截图 / 其他指令问AI")
    print("*"*50 + "\n")
    
    # 🚀 核心修改：加上异常捕获防弹衣，防止 PM2 在启动瞬间因网络波动错杀进程
    try:
        send_message(ADMIN_CHAT_ID, "🟢 系统已启动，每小时自动巡检任务已激活并在后台运行。")
    except Exception as e:
        dlog(f"⚠️ 启动通知发送失败 (网络波动)，但系统将继续运行: {e}")
    
    threading.Thread(target=auto_scheduler, daemon=True).start()
    threading.Thread(target=auto_fixer_scheduler, daemon=True).start()
    dlog("🔧 [系统] Gemini 自修复守护线程已启动（10分钟巡检）")
    
    offset = None
    while True:
        updates = get_updates(offset)
        if updates and updates.get("result"):
            for update in updates["result"]:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                
                if not chat_id: continue

                HELP_TEXT = "📌 可用指令：\n0 - 查看指令列表\n1 - 启动下单\n2 - 停止\n3/修复 - 手动触发Gemini修复\n4/状态 - 查看修复工具状态\n日志/log - 查看修复历史"

                if text == "0":
                    send_message(chat_id, HELP_TEXT)

                elif text == "1":
                    if task_thread and task_thread.is_alive(): send_message(chat_id, "⚠️ 运行中...")
                    else:
                        send_message(chat_id, "🚀 启动代发...")
                        task_thread = threading.Thread(target=task_wrapper, args=(chat_id,))
                        task_thread.start()
                
                elif text == "2":
                    if task_thread and task_thread.is_alive(): stop_event.set()

                elif text == "3" or text == "修复":
                    send_message(chat_id, "🔧 手动触发 Gemini 自修复检查...")
                    trigger_ai_fix(chat_id, text)

                elif text == "4" or text == "状态":
                    try:
                        import json as _json
                        lines = []
                        # 1. 错误文件状态
                        err_path = "/Users/shaoyong/Desktop/zidongxiadan/latest_error.json"
                        if os.path.exists(err_path):
                            with open(err_path, 'r') as f:
                                err = _json.load(f)
                            status = "✅ 已处理" if err.get("processed") else "🔴 待修复"
                            lines.append(f"错误报告: {status} ({err.get('timestamp','未知')})")
                            if not err.get("processed"):
                                lines.append(f"  阶段: {err.get('action_phase','?')}")
                                lines.append(f"  错误: {str(err.get('error','?'))[:80]}")
                        else:
                            lines.append("错误报告: 📭 无")
                        # 2. 修复历史
                        log_path = "/Users/shaoyong/Desktop/zidongxiadan/fix_history.log"
                        if os.path.exists(log_path):
                            with open(log_path, 'r') as f:
                                count = sum(1 for _ in f)
                            lines.append(f"修复历史: 共 {count} 条记录")
                        else:
                            lines.append("修复历史: 暂无")
                        # 3. Gemini API
                        try:
                            import requests as _req
                            r = _req.get("https://generativelanguage.googleapis.com/v1beta/models?key=AIzaSyCpWi6fnXNW_AKcpVbZz-EwP92dhW1EKEQ", timeout=5)
                            lines.append(f"Gemini API: {'✅ 正常' if r.status_code == 200 else '❌ 异常 '+str(r.status_code)}")
                        except Exception as ge:
                            lines.append(f"Gemini API: ❌ 不可达 ({ge})")
                        # 4. PM2
                        import subprocess
                        pm2 = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5)
                        if pm2.returncode == 0:
                            procs = _json.loads(pm2.stdout)
                            for p in procs:
                                if "下单" in p.get("name", ""):
                                    lines.append(f"PM2 进程: {p['pm2_env']['status']} (重启{p['pm2_env']['restart_time']}次)")
                        send_message(chat_id, "📊 修复工具状态:\n" + "\n".join(lines))
                    except Exception as e:
                        send_message(chat_id, f"状态检查异常: {e}")

                elif text == "日志" or text == "log":
                    try:
                        log_path = "/Users/shaoyong/Desktop/zidongxiadan/fix_history.log"
                        if os.path.exists(log_path):
                            with open(log_path, 'r') as f:
                                lines = f.readlines()[-20:]
                            send_message(chat_id, "📋 最近修复日志:\n" + "".join(lines))
                        else:
                            send_message(chat_id, "暂无修复日志。")
                    except Exception as e:
                        send_message(chat_id, f"读取日志失败: {e}")

                elif text:
                    send_message(chat_id, "❓ 未知指令，发送 0 查看可用指令列表")
                        
        time.sleep(1)

if __name__ == "__main__":
    start_bot()