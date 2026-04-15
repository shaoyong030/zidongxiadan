import re
with open('feishu_bot.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace(
    '''            except Exception as e:
                pass''',
    '''            except Exception as e:
                dlog(f"[AI修复请求] 访问 {path} 失败: {e}")'''
)

with open('feishu_bot.py', 'w', encoding='utf-8') as f:
    f.write(c)

