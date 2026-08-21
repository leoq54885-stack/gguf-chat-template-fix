# GGUF Chat Template Multilingual Fix

A fix for the multilingual output issue in [Qwen3.8-27B-Uncensored-HauhauCS-Aggressive](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF), where the model switches to English mid-response when using non-English inputs.

**This fix specifically targets the issue reported in [HuggingFace Discussions #12](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/discussions/12).** It has only been tested against this particular model. Other models with similar `reasoning_instructions` mechanisms may benefit, but no guarantees are made.

## The Problem

This model is processed with heretic/abliteration (uncensoring), which weakens instruction-following capability. The GGUF's embedded `tokenizer.chat_template` injects a pure English `reasoning_instructions` preamble at the start of every conversation when `enable_thinking=true` (the default). This causes:

- Chain-of-thought reasoning forced into English
- Final response starts in the user's language but drifts back to English after 2-3 sentences
- System prompts explicitly requesting another language are ignored

## Root Cause

The `reasoning_instructions` in the original `tokenizer.chat_template`:

```jinja
{%- if resolved_reasoning_effort == 'xhigh' %}
    {%- set reasoning_instructions = 'Reasoning effort is set to xhigh. Please think carefully through the task, validate key assumptions, consider plausible alternatives, and prioritize correctness, consistency, and clarity in the final answer.' %}
{%- elif resolved_reasoning_effort == 'low' %}
    {%- set reasoning_instructions = 'Reasoning effort is set to low. Keep your thinking brief and focused, moving directly to the conclusion without unnecessary elaboration.' %}
{%- endif %}
```

This English preamble is injected as a system message at the beginning of every conversation, strongly pulling both the chain-of-thought and output language toward English on an abliterated model.

## The Fix

Replace `reasoning_instructions` with a version that enforces multilingual behavior:

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

Key changes:

1. **Language rule always injected** — `reasoning_instructions` is initialized to `_lang` unconditionally, not only when thinking is enabled. The original only set it inside the `enable_thinking` block.
2. **Instructions in English** — On an abliterated model, English instructions are followed more reliably than instructions in the target language.
3. **Explicit language lock** — "Never switch to English or mix languages" prevents mid-response drift.

## Quick Start

### Prerequisites

- Python 3.8+
- The target GGUF file

### Steps

1. **Clone this repo**

```bash
git clone https://github.com/leoq54885-stack/gguf-chat-template-fix.git
cd gguf-chat-template-fix
```

2. **Patch your GGUF**

You can pass the GGUF path as a command-line argument:

```bash
python gguf_patch_template.py /path/to/your_model.gguf
```

Or edit the path at the top of `gguf_patch_template.py`:

```python
GGUF_PATH = r"/path/to/your_model.gguf"
```

The script will:
- Back up the original template to `original_chat_template_backup.txt`
- Perform an in-place equal-length replacement of `tokenizer.chat_template` in the GGUF
- Verify the write by re-reading and comparing

3. **(Optional) Verify the patch**

```bash
python verify_patch.py /path/to/your_model.gguf
```

4. **(Optional) Preview the template rendering**

```bash
python test_template.py
```

5. **Reload the model**

In your inference frontend (LM Studio / llama.cpp / KoboldCpp, etc.), **fully unload and reload the model** to ensure the new template takes effect.

### LM Studio Note

LM Studio may override the GGUF's embedded template with its own. Ensure that:
- Prompt Template is set to **Default** (uses GGUF embedded template) in model settings
- If issues persist, paste the contents of `qwen38_fixed_template.jinja` into LM Studio's custom Prompt Template

## Test Result

### Environment

- Model: Qwen3.8-27B-Uncensored-HauhauCS-Aggressive
- Quantization: **Q4_K_P** (verified)
- Frontend: LM Studio

> **Note on other quantizations:** The `tokenizer.chat_template` is stored as metadata in the GGUF header and is identical across all quantization variants (Q4_K_P, Q5_K_P, Q6_K, Q8, etc.). Quantization only affects tensor data, not metadata. The patch should therefore work on any quantization of this model, but has only been tested on Q4_K_P.

### Before Fix

Chinese input produced mixed-language output that drifted to English:

```
木板冰凉地贴着我的脊背，凉意顺着肩胛骨一路渗进骨头里。我试着动一根手指，
却只换来手腕被 yanked back against the grain——no. 腕 straps were tight,
my hands splayed and pinned above me, fingers twitching uselessly against the
rough wood. My ankles were just as good for nothing;
```

### After Fix

Tested with a Chinese prompt (image + "看图写一个小故事"):

- **Reasoning**: Fully in Chinese (~1 min 45 sec)
- **Final output**: Complete Chinese short story, zero language switching

Excerpt:

> 《四重音》
>
> 在数据与梦境交界的地方，住着一个会唱歌的女孩。她叫初音，头发是海的颜色，长发能飘到很远很远的地方。
>
> 有时，她站在一片没有名字的花海里。夜色把花瓣染成蓝紫与雪白，风一吹，整片花田像海浪一样起伏...

## Customization

### Change the language rule

Edit the `_lang` variable in `qwen38_fixed_template.jinja`:

```jinja
{%- set _lang = "Always think and respond in Japanese. Never switch to English. " %}
```

### Change reasoning depth instructions

Edit the `_effort` branches:

```jinja
{%- if _effort == 'xhigh' %}
    {%- set reasoning_instructions = 'Your xhigh instruction. ' ~ _lang %}
{%- elif _effort == 'low' %}
    {%- set reasoning_instructions = 'Your low instruction. ' ~ _lang %}
{%- endif %}
```

### Add medium effort level

Add after the `low` branch:

```jinja
{%- elif _effort == 'medium' %}
    {%- set reasoning_instructions = 'Balance thoroughness and efficiency. ' ~ _lang %}
```

### Byte length limit

In-place replacement requires the new template to be <= the original template size (8952 bytes). The script auto-pads with spaces at the end if shorter, and aborts if longer.

Check your template size:

```bash
python -c "print(len(open('qwen38_fixed_template.jinja', encoding='utf-8').read().rstrip().encode('utf-8')))"
```

### Restore the original template

Rename `original_chat_template_backup.txt` to `.jinja` and re-run the patch script.

## Files

| File | Description |
|------|-------------|
| `gguf_patch_template.py` | Main patch script — in-place replacement of GGUF chat_template |
| `gguf_meta_dump.py` | GGUF metadata export tool for inspection |
| `verify_patch.py` | Verifies the patch by reading the template back from GGUF |
| `test_template.py` | Jinja template rendering test |
| `qwen38_fixed_template.jinja` | The fixed chat template |
| `original_chat_template_backup.txt` | Auto-generated backup of original template |

## Scope

This fix is specifically for [Qwen3.8-27B-Uncensored-HauhauCS-Aggressive](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF) as reported in [Discussions #12](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/discussions/12). Other models with similar `reasoning_instructions` mechanisms may benefit, but the template content must be adjusted accordingly.

## Credits

- [HauhauCS](https://huggingface.co/HauhauCS) — Model author
- [filia23424](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/discussions/12) — Root cause analysis
- [JimmyAe](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/discussions/12) — Language rule approach
- All reporters in HuggingFace Discussions #12

## License

MIT
