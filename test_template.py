import sys
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from jinja2 import Environment, BaseLoader
from jinja2.ext import loopcontrols

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qwen38_fixed_template.jinja")

with open(TEMPLATE_PATH, encoding="utf-8") as f:
    tpl_src = f.read()

env = Environment(loader=BaseLoader(), extensions=[loopcontrols])
env.policies["json.dumps_kwargs"] = {"ensure_ascii": False}

def raise_exception(msg):
    raise ValueError(msg)

env.globals["raise_exception"] = raise_exception
tpl = env.from_string(tpl_src)

print("=== 用例1: 无system, 单轮中文 ===")
print(tpl.render(messages=[{"role": "user", "content": "你好，介绍一下你自己"}],
                 add_generation_prompt=True))

print("=== 用例2: 有system + 多轮 + 历史思考 ===")
print(tpl.render(messages=[
    {"role": "system", "content": "你是一名小说家。请根据图片写一篇简体中文故事。"},
    {"role": "user", "content": "1+1等于几"},
    {"role": "assistant", "content": "等于2。", "reasoning_content": "简单算术。"},
    {"role": "user", "content": "再加3呢"},
], add_generation_prompt=True))

print("=== 用例2b: 检查注入的系统提示为中文 ===")
rendered = tpl.render(messages=[
    {"role": "system", "content": "你是一名小说家。请根据图片写一篇简体中文故事。"},
    {"role": "user", "content": "看图写故事"},
], add_generation_prompt=True)
assert "简短思考，永远使用中文。" in rendered
assert rendered.count("简短思考，永远使用中文。") == 1
assert "必须始终使用用户最近一次输入的语言进行思考和回答。" not in rendered
assert "Always think" not in rendered
assert "Think carefully" not in rendered
print(rendered.split("<|im_end|>", 1)[0] + "<|im_end|>")

print("=== 用例3: 关闭thinking ===")
print(tpl.render(messages=[{"role": "user", "content": "你好"}],
                 add_generation_prompt=True, enable_thinking=False))

print("=== 用例4: 带tools ===")
print(tpl.render(messages=[{"role": "user", "content": "今天天气"}],
                 tools=[{"name": "get_weather", "parameters": {"city": {"type": "string"}}}],
                 add_generation_prompt=True)[:1200])

print("=== 全部用例渲染成功 ===")
