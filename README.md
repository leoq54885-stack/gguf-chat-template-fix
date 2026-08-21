# GGUF Chat Template Multilingual Fix

A workaround for the multilingual output issue in [Qwen3.8-27B-Uncensored-HauhauCS-Aggressive](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF), where the model switches to English mid-response when using non-English inputs.

**Targets [HuggingFace Discussions #12](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/discussions/12).** Tested on Q4_K_P only. The `tokenizer.chat_template` is metadata identical across all quantizations, so the patch should work on any variant.

> **This is not a perfect fix.** The model may still drift to English in long outputs. This workaround buys time until the model author releases an official fix. Using a low temperature (e.g. 0.1) significantly reduces the drift.

## The Problem

The model is processed with heretic/abliteration (uncensoring), which weakens instruction-following. The GGUF's `tokenizer.chat_template` injects a pure English `reasoning_instructions` preamble into every conversation, pulling both chain-of-thought and output toward English.

## The Fix

Replace `reasoning_instructions` with a short instruction in your target language. This repo uses Chinese as a demo:

```jinja
{%- set reasoning_instructions = '简短思考，永远使用中文。' %}
```

**You should change this to your own language.** See step 2 below.

## Quick Start

### Prerequisites

- Python 3.8+
- The target GGUF file

### Steps

1. **Clone**

```bash
git clone https://github.com/leoq54885-stack/gguf-chat-template-fix.git
cd gguf-chat-template-fix
```

2. **Customize the template for your language**

Open `qwen38_fixed_template.jinja`, find this line and change it to your language:

```jinja
{%- set reasoning_instructions = '简短思考，永远使用中文。' %}
```

Examples:

```jinja
{%- set reasoning_instructions = 'Think briefly, always respond in Japanese.' %}
{%- set reasoning_instructions = 'Pense brièvement, répondez toujours en français.' %}
{%- set reasoning_instructions = '简短思考，永远使用中文。' %}
```

3. **Patch your GGUF**

```bash
python gguf_patch_template.py /path/to/your_model.gguf
```

The script backs up the original template, performs an in-place equal-length replacement, and verifies the write.

4. **Verify (optional)**

```bash
python verify_patch.py /path/to/your_model.gguf
python test_template.py
```

5. **Reload the model**

Fully unload and reload the model in your frontend (LM Studio / llama.cpp / KoboldCpp, etc.).

6. **Set a low temperature**

Use a low temperature to reduce English drift in long outputs. This is critical — the template fix alone does not fully prevent the model from switching back to English.

## Limitations

- **Not a perfect fix.** The model may still drift to English in long outputs, especially at higher temperatures.
- **Low temperature required.** Combine with temp for best results.
- **Waiting for official fix.** The model author ([HauhauCS](https://huggingface.co/HauhauCS)) is aware of the issue and working on a fix.

## Test Result

**Environment:** Qwen3.8-27B-Uncensored-HauhauCS-Aggressive, Q4_K_P, LM Studio, low temperature.

**Before:** Chinese prompt (image + "撰写恐怖小说") drifted to English within a few sentences.

```
木板冰凉地贴着我的脊背，凉意顺着肩胛骨一路渗进骨头里。我试着动一根手指，
却只换来手腕被 yanked back against the grain——no. 腕 straps were tight,
my hands splayed and pinned above me, fingers twitching uselessly against the
rough wood. My ankles were just as good for nothing;
```

**After:** Chinese prompt (image + "看图写一个小故事") produced fully Chinese reasoning and output.

> 《四重音》
>
> 在数据与梦境交界的地方，住着一个会唱歌的女孩。她叫初音，头发是海的颜色，长发能飘到很远很远的地方。

## Byte Length Limit

The new template must be <= 8952 bytes (original size). The script auto-pads with spaces if shorter, aborts if longer.

```bash
python -c "print(len(open('qwen38_fixed_template.jinja', encoding='utf-8').read().rstrip().encode('utf-8')))"
```

To restore the original: rename `original_chat_template_backup.txt` to `.jinja` and re-run the patch.

## Files

| File | Description |
|------|-------------|
| `gguf_patch_template.py` | Main patch script |
| `gguf_meta_dump.py` | GGUF metadata export tool |
| `verify_patch.py` | Verifies patch by reading template back from GGUF |
| `test_template.py` | Jinja template rendering test |
| `qwen38_fixed_template.jinja` | The fixed chat template (Chinese demo) |

## Credits

- [HauhauCS](https://huggingface.co/HauhauCS) — Model author
- [filia23424](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/discussions/12) — Root cause analysis
- [JimmyAe](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/discussions/12) — Language rule approach
- All reporters in Discussions #12

## License

MIT
