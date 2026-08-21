import struct
import sys
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GGUF_PATH = r"./your_model.gguf"

def read_str(f):
    n = struct.unpack("<Q", f.read(8))[0]
    return f.read(n).decode("utf-8", errors="replace")

def skip_value(f, vtype):
    sizes = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
    if vtype in sizes:
        f.seek(sizes[vtype], 1)
    elif vtype == 8:
        n = struct.unpack("<Q", f.read(8))[0]
        f.seek(n, 1)
    elif vtype == 9:
        etype = struct.unpack("<I", f.read(4))[0]
        n = struct.unpack("<Q", f.read(8))[0]
        for _ in range(n):
            skip_value(f, etype)
    else:
        raise ValueError(f"unknown type {vtype}")

def main():
    global GGUF_PATH
    if len(sys.argv) > 1:
        GGUF_PATH = sys.argv[1]

    if not os.path.isfile(GGUF_PATH):
        print(f"错误: GGUF文件不存在: {GGUF_PATH}")
        print("用法: python verify_patch.py your_model.gguf")
        return 1

    with open(GGUF_PATH, "rb") as f:
        f.read(4)
        f.read(4)
        f.read(8)
        kv_count = struct.unpack("<Q", f.read(8))[0]
        for _ in range(kv_count):
            key = read_str(f)
            vtype = struct.unpack("<I", f.read(4))[0]
            if key == "tokenizer.chat_template":
                n = struct.unpack("<Q", f.read(8))[0]
                tpl = f.read(n).decode("utf-8", errors="replace")
                print(f"模板长度: {n} 字节")
                idx = tpl.find("reasoning_instructions")
                if idx >= 0:
                    print("\n=== reasoning_instructions 区域 ===")
                    print(tpl[idx-30:idx+400])
                idx2 = tpl.find("_lang")
                if idx2 >= 0:
                    print("\n=== _lang 变量区域 ===")
                    print(tpl[idx2-10:idx2+200])
                idx3 = tpl.find("Never switch")
                if idx3 >= 0:
                    print("\n=== 语言规则确认存在 ===")
                    print(tpl[idx3-50:idx3+100])
                else:
                    print("\n!!! 警告: 未找到 'Never switch' 关键词")
                break
            skip_value(f, vtype)
    return 0

if __name__ == "__main__":
    sys.exit(main())
