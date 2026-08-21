# GGUF Chat Template Multilingual Fix

修复 [Qwen3.8-27B-Uncensored-HauhauCS-Aggressive](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF) 模型在非英语场景下输出中途切换为英语的问题。

对应 HuggingFace Issue: [discussions/12](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/discussions/12)

## 问题描述

该模型经过 heretic/abliteration（去审查）处理，指令遵循能力被削弱。GGUF 内嵌的 `tokenizer.chat_template` 在 `enable_thinking=true`（默认）时注入纯英文的 `reasoning_instructions`，导致：

- 思考过程（Chain-of-Thought）强制使用英语
- 最终输出以用户语言开头，但 2-3 句后漂回英语
- 即使在 system prompt 中明确要求使用中文也无法阻止

## 根因

`tokenizer.chat_template` 中的 `reasoning_instructions` 机制：

```jinja
{%- if resolved_reasoning_effort == 'xhigh' %}
    {%- set reasoning_instructions = 'Reasoning effort is set to xhigh. Please think carefully through the task, validate key assumptions, consider plausible alternatives, and prioritize correctness, consistency, and clarity in the final answer.' %}
{%- elif resolved_reasoning_effort == 'low' %}
    {%- set reasoning_instructions = 'Reasoning effort is set to low. Keep your thinking brief and focused, moving directly to the conclusion without unnecessary elaboration.' %}
{%- endif %}
```

这段英文指令在每轮对话开头作为 system message 注入，对 abliterated 模型产生强烈的英文倾向。

## 修复方案

将 `reasoning_instructions` 替换为包含多语言规则的版本：

```jinja
{%- set _lang = "Always think and respond in the same language as the user's most recent input. Never switch to English or mix languages unless the user explicitly asks. " %}
{%- set reasoning_instructions = _lang %}
{%- if enable_thinking is undefined or enable_thinking is true %}
    {%- set _effort = reasoning_effort|default('xhigh') %}
    {%- if _effort == 'xhigh' %}
        {%- set reasoning_instructions = 'Think carefully, validate key assumptions, consider alternatives, prioritize correctness and clarity. ' ~ _lang %}
    {%- elif _effort == 'low' %}
        {%- set reasoning_instructions = 'Keep thinking brief and focused, move directly to conclusion. ' ~ _lang %}
    {%- endif %}
{%- endif %}
```

关键改动：

1. **语言指令始终注入** — 无论 `enable_thinking` 是否开启，`reasoning_instructions` 都会包含语言规则（原版仅在 thinking 开启时设置）
2. **用英文写指令** — 对 abliterated 模型，英文指令的遵循度高于中文指令
3. **显式禁止语言切换** — "Never switch to English or mix languages"

## 开箱即用操作方法

### 前置要求

- Python 3.8+
- 目标 GGUF 文件

### 步骤

1. **克隆本仓库**

```bash
git clone https://github.com/leoq54885-stack/gguf-chat-template-fix.git
cd gguf-chat-template-fix
```

2. **修改配置**

编辑 `gguf_patch_template.py`，修改以下路径：

```python
GGUF_PATH = r"你的GGUF文件路径.gguf"
NEW_TEMPLATE_PATH = r"./qwen38_fixed_template.jinja"
BACKUP_PATH = r"./original_chat_template_backup.txt"
```

3. **（可选）预览修改后的模板**

```bash
python test_template.py
```

4. **执行补丁**

```bash
python gguf_patch_template.py
```

脚本会：
- 自动备份原始模板到 `original_chat_template_backup.txt`
- 原地等长替换 GGUF 中的 `tokenizer.chat_template` 字段
- 写入后自动校验

5. **重新加载模型**

在你的推理前端（LM Studio / llama.cpp / KoboldCpp 等）中**完全卸载并重新加载模型**，确保新模板生效。

### 在 LM Studio 中的额外注意

LM Studio 可能用自己的 Prompt Template 覆盖 GGUF 内嵌模板。请确认：

- 模型设置中 Prompt Template 选择 **Default**（使用 GGUF 内嵌模板）
- 如果仍有问题，可以将 `qwen38_fixed_template.jinja` 的内容粘贴到 LM Studio 的自定义 Prompt Template 中

## 测试结果

### 环境

- 模型: Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P
- 前端: LM Studio
- 量化: Q4_K_P

### 修复前

```
木板冰凉地贴着我的脊背，凉意顺着肩胛骨一路渗进骨头里。我试着动一根手指，
却只换来手腕被 yanked back against the grain——no. 腕 straps were tight,
my hands splayed and pinned above me, fingers twitching uselessly against the
rough wood. My ankles were just as good for nothing;
```

中文输出中途混入大量英文，无法保持单一语言。

### 修复后

用户发送中文 + 图片，模型完整使用中文进行思考和输出：

- **思考过程**: 全中文（1分45秒）
- **最终输出**: 全中文短篇故事，无任何语言切换

输出示例（节选）：

> 《四重音》
>
> 在数据与梦境交界的地方，住着一个会唱歌的女孩。她叫初音，头发是海的颜色，长发能飘到很远很远的地方。
>
> 有时，她站在一片没有名字的花海里。夜色把花瓣染成蓝紫与雪白，风一吹，整片花田像海浪一样起伏...

## 自助修改指南

如果你想自定义语言规则或推理指令，编辑 `qwen38_fixed_template.jinja` 中的以下部分：

### 修改语言规则

找到 `_lang` 变量，修改为你需要的指令：

```jinja
{%- set _lang = "你的自定义语言规则 " %}
```

例如，强制使用日语：

```jinja
{%- set _lang = "Always think and respond in Japanese. Never switch to English. " %}
```

### 修改推理深度指令

找到 `_effort` 相关的分支，修改 `xhigh` / `low` 的指令文本：

```jinja
{%- if _effort == 'xhigh' %}
    {%- set reasoning_instructions = '你的xhigh指令 ' ~ _lang %}
{%- elif _effort == 'low' %}
    {%- set reasoning_instructions = '你的low指令 ' ~ _lang %}
{%- endif %}
```

### 添加 medium 推理深度

如果需要 `medium` 级别，在 `low` 分支后添加：

```jinja
{%- elif _effort == 'medium' %}
    {%- set reasoning_instructions = 'Balance thoroughness and efficiency. ' ~ _lang %}
```

### 字节长度限制

原地替换要求新模板字节数 <= 原始模板字节数（8952 字节）。脚本会自动检查并在末尾用空格填充。如果新模板超过原长度，脚本会报错中止。

运行以下命令检查字节数：

```bash
python -c "print(len(open('qwen38_fixed_template.jinja', encoding='utf-8').read().rstrip().encode('utf-8')))"
```

### 恢复原始模板

如果需要还原，将 `original_chat_template_backup.txt` 重命名为 `.jinja` 并重新运行 patch 脚本即可。

## 文件说明

| 文件 | 说明 |
|------|------|
| `gguf_patch_template.py` | 主补丁脚本，原地替换 GGUF 中的 chat_template |
| `gguf_meta_dump.py` | GGUF 元数据导出工具，用于查看和验证模板内容 |
| `verify_patch.py` | 补丁验证脚本，从 GGUF 中读取模板确认修改已生效 |
| `test_template.py` | Jinja 模板渲染测试，验证模板语法和输出格式 |
| `qwen38_fixed_template.jinja` | 修复后的 chat template |
| `original_chat_template.txt` | 原始模板备份（首次运行 patch 脚本时自动生成） |

## 适用范围

本方案针对 Qwen3.8 系列模型的 chat template 结构。其他使用类似 `reasoning_instructions` 机制的模型也可参考，但需要根据具体模板内容调整。

## 致谢

- [HauhauCS](https://huggingface.co/HauhauCS) - 模型作者
- HuggingFace Issue 中的所有反馈者 - 问题定位和修复思路
- [filia23424](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/discussions/12) - 根因分析
- [JimmyAe](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/discussions/12) - 语言规则方案

## License

MIT
