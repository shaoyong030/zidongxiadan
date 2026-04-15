import requests
import time
import threading
import os
from openclaw_task import run_pdd_to_taobao_task

# ================= 配置区 =================
TOKEN = "8709491629:AAGbFv7KIEGDa6owztxjPOdFfDP0N69nD0g"
PROXIES = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
SCHEDULE_INTERVAL = 3600  
# 🚀 这里的接口会根据下面尝试的结果自动修正
OPENCLAW_BASE = "http://127.0.0.1:18789" 

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
    send_message(chat_id, "🔧 嗅探到失败/崩溃异常！已全自动提交给后台 AI(我本人) 尝试接管修复中，请稍等...")
    def _run_fix():
        paths = ["/api/chat", "/chat", "/api/v1/chat", "/message"]
        for path in paths:
            try:
                payload = {
                    "message": text, 
                    "query": text,
                    "session_id": "main",
                    "agent_id": "main"
                }
                # AI修复可能需要挺长时间，给个180秒超时
                res = requests.post(f"{OPENCLAW_BASE}{path}", json=payload, timeout=180)
                if res.status_code == 200:
                    data = res.json()
                    ans = data.get("response") or data.get("data", {}).get("content") or data.get("text")
                    if ans:
                        send_message(chat_id, f"🛠️ **AI 自动自我修复报告** 🛠️：\n{ans}")
                        return
            except Exception as e:
                dlog(f"[AI修复请求] 访问 {path} 失败: {e}")
    # 使用新线程去让AI修复，不阻塞主线程
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

                if text == "1":
                    if task_thread and task_thread.is_alive(): send_message(chat_id, "⚠️ 运行中...")
                    else:
                        send_message(chat_id, "🚀 启动代发...")
                        task_thread = threading.Thread(target=task_wrapper, args=(chat_id,))
                        task_thread.start()
                
                elif text == "2":
                    if task_thread and task_thread.is_alive(): stop_event.set()

                elif "截图" in text:
                    os.system("screencapture -x /tmp/screen.png")
                    send_photo(chat_id, "/tmp/screen.png")

                elif text:
                    send_message(chat_id, f"💡 正在请求 OpenClaw AI...")
                    # 🚀 雷达寻路逻辑
                    success = False
                    # 尝试这些可能的路径
                    paths = ["/api/chat", "/chat", "/api/v1/chat", "/message"]
                    for path in paths:
                        try:
                            payload = {
                                "message": text, 
                                "query": text,
                                "session_id": "main",
                                "agent_id": "main"
                            }
                            res = requests.post(f"{OPENCLAW_BASE}{path}", json=payload, timeout=5)
                            dlog(f"DEBUG: 尝试路径 {path} -> 返回 {res.status_code}")
                            
                            if res.status_code == 200:
                                data = res.json()
                                ans = data.get("response") or data.get("data", {}).get("content") or data.get("text")
                                if ans:
                                    send_message(chat_id, f"🤖 OpenClaw ({path}) 回复：\n{ans}")
                                    success = True
                                    break
                        except:
                            continue
                    
                    if not success:
                        send_message(chat_id, "❌ 自动寻路失败。OpenClaw 接口可能未开放 API 访问，或路径极其特殊。")
                        
        time.sleep(1)

if __name__ == "__main__":
    start_bot()