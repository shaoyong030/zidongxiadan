"""
Gemini 自动修复守护模块
功能：监控 latest_error.json → 调 Gemini 分析 → 生成修复补丁 → 应用 → 重启 PM2
"""
import json
import os
import time
import re
import requests
import subprocess
import datetime

# ====== 配置 ======
GEMINI_API_KEY = "AIzaSyCpWi6fnXNW_AKcpVbZz-EwP92dhW1EKEQ"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

PROJECT_DIR = "/Users/shaoyong/Desktop/zidongxiadan"
ERROR_FILE = os.path.join(PROJECT_DIR, "latest_error.json")
MAIN_SCRIPT = os.path.join(PROJECT_DIR, "openclaw_task.py")
FIX_LOG_FILE = os.path.join(PROJECT_DIR, "fix_history.log")

# Telegram 通知（复用现有配置）
TG_TOKEN = "8709491629:AAGbFv7KIEGDa6owztxjPOdFfDP0N69nD0g"
TG_CHAT_ID = "8693156373"
TG_PROXIES = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}


def tg_notify(text):
    """通过 Telegram 发送通知"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": text[:4000]},
            proxies=TG_PROXIES, timeout=15
        )
    except:
        pass


def log_fix(msg):
    """记录修复日志"""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(FIX_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_error_report():
    """读取错误报告，返回 dict 或 None"""
    if not os.path.exists(ERROR_FILE):
        return None
    try:
        with open(ERROR_FILE, "r", encoding="utf-8") as f:
            report = json.load(f)
        # 检查是否已处理过（通过 processed 标记）
        if report.get("processed"):
            return None
        return report
    except:
        return None


def extract_relevant_code(error_msg, action_phase):
    """根据错误阶段提取相关代码片段（不发送全部 1300 行）"""
    try:
        with open(MAIN_SCRIPT, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except:
        return "无法读取源码"

    # 根据 action_phase 定位关键代码区域
    phase_markers = {
        "LOGISTICS": "执行区 2：物流回填",
        "PLACE_ORDER": "执行区 1：普通单笔自动下单",
        "PLACE_ORDER_ADDRESS": "执行区 1：普通单笔自动下单",
        "MERGE_ADDRESS": "执行区 0：购物车合单引擎",
        "MARK_GREEN_MERGED": "执行区 0.5：回填已成功合单",
    }

    marker = phase_markers.get(action_phase, "")
    start_line = 0
    end_line = min(100, len(lines))

    if marker:
        for i, line in enumerate(lines):
            if marker in line:
                start_line = max(0, i - 5)
                end_line = min(len(lines), i + 120)
                break

    # 同时搜索错误消息中提到的选择器或关键词
    error_str = str(error_msg).lower()
    extra_lines = []
    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in ["selector", "locator", "fill", "click"] 
               if kw in error_str):
            extra_lines.append((i, line.rstrip()))

    code_block = "".join(lines[start_line:end_line])
    # 限制长度防止 token 爆炸
    if len(code_block) > 8000:
        code_block = code_block[:8000] + "\n... (truncated)"

    return f"[行 {start_line+1}-{end_line}]\n{code_block}"


def call_gemini(error_report, code_snippet):
    """调用 Gemini API 分析错误并生成修复方案"""
    prompt = f"""你是一个 Python 自动化脚本的维护专家。以下脚本使用 Playwright 操控浏览器，在拼多多商家后台和淘宝之间自动下单和同步物流。

## 错误报告
- 时间: {error_report.get('timestamp', '未知')}
- 错误阶段: {error_report.get('action_phase', '未知')}
- 错误信息: {error_report.get('error', '未知')}
- 堆栈: {error_report.get('traceback', '无')}
- 上下文: {error_report.get('extra_context', '无')}

## 最近日志
{error_report.get('recent_log', '无')[-2000:]}

## 相关源码
{code_snippet}

## 要求
1. 分析错误的根本原因（通常是页面选择器失效、UI改版、或时序问题）
2. 如果可以修复，输出精确的修复方案，格式如下：

```fix
FILE: openclaw_task.py
FIND:
<要替换的原始代码，必须完全精确匹配>
REPLACE:
<替换后的新代码>
```

3. 如果无法确定修复方案（比如需要查看页面实际DOM），只输出分析结论，不要输出 fix 块。
4. 只修复报错的部分，不要改动其他功能。修复要保守，优先增加容错和重试。
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4000}
    }

    try:
        resp = requests.post(GEMINI_URL, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text
        else:
            log_fix(f"Gemini API 返回异常: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        log_fix(f"Gemini API 调用失败: {e}")
        return None


def apply_fix(gemini_response):
    """从 Gemini 响应中提取修复补丁并应用"""
    # 解析 ```fix 块
    fix_blocks = re.findall(
        r'```fix\s*\n(.*?)```',
        gemini_response,
        re.DOTALL
    )

    if not fix_blocks:
        return False, "Gemini 未给出可执行的修复方案"

    applied = 0
    for block in fix_blocks:
        # 解析 FIND 和 REPLACE
        find_match = re.search(r'FIND:\s*\n(.*?)(?=\nREPLACE:)', block, re.DOTALL)
        replace_match = re.search(r'REPLACE:\s*\n(.*?)$', block, re.DOTALL)

        if not find_match or not replace_match:
            continue

        find_text = find_match.group(1).rstrip('\n')
        replace_text = replace_match.group(1).rstrip('\n')

        if not find_text.strip():
            continue

        try:
            with open(MAIN_SCRIPT, "r", encoding="utf-8") as f:
                content = f.read()

            if find_text not in content:
                log_fix(f"⚠️ FIND 块未匹配到源码，跳过此补丁")
                continue

            # 备份
            backup_path = MAIN_SCRIPT + f".bak_{int(time.time())}"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(content)

            # 应用
            new_content = content.replace(find_text, replace_text, 1)
            with open(MAIN_SCRIPT, "w", encoding="utf-8") as f:
                f.write(new_content)

            applied += 1
            log_fix(f"✅ 补丁 #{applied} 已应用，备份: {os.path.basename(backup_path)}")

        except Exception as e:
            log_fix(f"❌ 补丁应用失败: {e}")

    if applied > 0:
        return True, f"成功应用 {applied} 个补丁"
    return False, "补丁匹配失败，未应用任何修改"


def mark_error_processed(result_msg):
    """标记错误已处理"""
    try:
        with open(ERROR_FILE, "r", encoding="utf-8") as f:
            report = json.load(f)
        report["processed"] = True
        report["fix_result"] = result_msg
        report["fix_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(ERROR_FILE, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except:
        pass


def restart_pm2():
    """重启 PM2 自动下单进程"""
    try:
        result = subprocess.run(
            ["pm2", "restart", "自动下单"],
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0
    except:
        return False


def run_fix_cycle():
    """执行一次完整的检测-修复循环"""
    report = read_error_report()
    if not report:
        return False

    log_fix(f"🔍 发现新错误报告！阶段: {report.get('action_phase')} | 错误: {report.get('error', '')[:80]}")

    # 提取相关代码
    code = extract_relevant_code(report.get("error", ""), report.get("action_phase", ""))

    # 调 Gemini
    log_fix("🤖 正在调用 Gemini 分析...")
    analysis = call_gemini(report, code)

    if not analysis:
        msg = "❌ Gemini API 无响应，本次跳过"
        log_fix(msg)
        mark_error_processed(msg)
        tg_notify(f"🔧 [自修复] {msg}")
        return False

    log_fix(f"📋 Gemini 分析完成，长度: {len(analysis)} 字符")

    # 尝试应用修复
    applied, fix_msg = apply_fix(analysis)

    if applied:
        log_fix(f"🔧 {fix_msg}，正在重启 PM2...")
        restarted = restart_pm2()
        status = "并已重启" if restarted else "但 PM2 重启失败"
        final_msg = f"🛠️ [自修复成功]\n阶段: {report.get('action_phase')}\n错误: {report.get('error', '')[:100]}\n{fix_msg}{status}"
    else:
        # 即使没有可执行补丁，也把分析发给 TG
        final_msg = f"🔍 [自修复分析]\n阶段: {report.get('action_phase')}\n错误: {report.get('error', '')[:100]}\n\nGemini 分析:\n{analysis[:1500]}"

    log_fix(final_msg[:200])
    mark_error_processed(final_msg[:500])
    tg_notify(final_msg)
    return applied


# ====== 独立运行入口 ======
if __name__ == "__main__":
    print("🔧 [自修复守护] 已启动，每 10 分钟巡检一次...")
    while True:
        try:
            run_fix_cycle()
        except Exception as e:
            log_fix(f"守护进程自身异常: {e}")
        time.sleep(600)  # 10分钟巡检一次
