import requests
import time
import threading
from openclaw_task import run_pdd_to_taobao_task

# ================= 配置区 =================
TOKEN = "8709491629:AAGbFv7KIEGDa6owztxjPOdFfDP0N69nD0g"
PROXIES = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
SCHEDULE_INTERVAL = 3600 

stop_event = threading.Event()
task_thread = None
admin_chat_id = None
# =========================================

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, proxies=PROXIES, timeout=15)
    except Exception as e:
        print(f"❌ [消息] 推送失败: {e}")

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
        
        if detailed_log:
            send_long_message(chat_id, detailed_log)
            time.sleep(1) 
            
        if final_report:
            send_message(chat_id, final_report)
            
    except Exception as e:
        err_msg = f"⚠️ 系统发生致命错误: {e}"
        print(err_msg)
        send_message(chat_id, err_msg)
    finally:
        task_thread = None

def auto_scheduler():
    global task_thread, admin_chat_id
    while True:
        time.sleep(SCHEDULE_INTERVAL) 
        if admin_chat_id:
            if task_thread and task_thread.is_alive():
                print("\n⏳ [定时器] 巡检触发，但当前有任务正在运行，本次自动跳过。")
            else:
                print("\n⏰ [定时器] 巡检时间到！自动拉起任务...")
                send_message(admin_chat_id, "⏰ [自动巡检] 定时触发！开始后台核验...")
                task_thread = threading.Thread(target=task_wrapper, args=(admin_chat_id,))
                task_thread.start()

def start_bot():
    global task_thread, admin_chat_id
    print("\n" + "*"*50)
    print("🤖 [系统] 搬砖通讯兵 V53.0 (三步解密+收银台强校验版) 上线！")
    print(f"⏱️  [配置] 定时巡检间隔已设置为: {SCHEDULE_INTERVAL} 秒 (1小时)")
    print("🚦 [状态] 正在监听指令：1 (启动) / 2 (停止)")
    print("*"*50 + "\n")
    
    scheduler_thread = threading.Thread(target=auto_scheduler, daemon=True)
    scheduler_thread.start()
    
    offset = None
    while True:
        updates = get_updates(offset)
        if updates and updates.get("result"):
            for update in updates["result"]:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                
                if text == "1" and chat_id:
                    if admin_chat_id != chat_id:
                        admin_chat_id = chat_id
                        print(f"🔒 [系统] 已绑定主人账号ID: {chat_id}，定时战报将推送到该账号。")

                    if task_thread and task_thread.is_alive():
                        send_message(chat_id, "⚠️ 已经在搬砖了，完成后会自动发送日志和战报...")
                    else:
                        send_message(chat_id, "🚀 收到手动指令！开始全流程操作...")
                        task_thread = threading.Thread(target=task_wrapper, args=(chat_id,))
                        task_thread.start()
                        
                elif text == "2" and chat_id:
                    if task_thread and task_thread.is_alive():
                        send_message(chat_id, "🛑 收到拦截指令！正在安全退出当前任务...")
                        stop_event.set()
        time.sleep(1)

if __name__ == "__main__":
    start_bot()
