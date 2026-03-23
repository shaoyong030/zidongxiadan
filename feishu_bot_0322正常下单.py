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

stop_event = threading.Event()
task_thread = None
admin_chat_id = None
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
    except: return None

def send_long_message(chat_id, text):
    parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for part in parts:
        send_message(chat_id, part)
        time.sleep(0.5)

def task_wrapper(chat_id):
    global task_thread
    try:
        stop_event.clear()
        detailed_log, final_report = run_pdd_to_taobao_task(stop_event)
        if detailed_log: send_long_message(chat_id, detailed_log)
        if final_report: send_message(chat_id, final_report)
    except Exception as e:
        send_message(chat_id, f"⚠️ 系统错误: {e}")
    finally:
        task_thread = None

def auto_scheduler():
    global task_thread, admin_chat_id
    while True:
        time.sleep(SCHEDULE_INTERVAL) 
        if admin_chat_id:
            if not (task_thread and task_thread.is_alive()):
                send_message(admin_chat_id, "⏰ [自动巡检] 开始执行...")
                task_thread = threading.Thread(target=task_wrapper, args=(admin_chat_id,))
                task_thread.start()

def start_bot():
    global task_thread, admin_chat_id
    print("\n" + "*"*50)
    print("🤖 [系统] 搬砖通讯兵 V64.2 (寻路修正版) 上线！")
    print("🚦 监听中：1下单 / 2停止 / 截图 / 其他指令问AI")
    print("*"*50 + "\n")
    
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
                if admin_chat_id is None: admin_chat_id = chat_id

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
