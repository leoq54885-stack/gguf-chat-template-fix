import struct
import sys
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ===== 配置区域 =====
# 修改为你自己的路径
GGUF_PATH = r"./your_model.gguf"
NEW_TEMPLATE_PATH = r"./qwen38_fixed_template.jinja"
BACKUP_PATH = r"./original_chat_template_backup.txt"
# ====================

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
    if len(sys.argv) > 1:
        global GGUF_PATH
        GGUF_PATH = sys.argv[1]

    if not os.path.isfile(GGUF_PATH):
        print(f"错误: GGUF文件不存在: {GGUF_PATH}")
        print("用法: python gguf_patch_template.py [your_model.gguf]")
        print("或在脚本顶部修改 GGUF_PATH")
        return 1

    with open(NEW_TEMPLATE_PATH, encoding="utf-8") as tf:
        new_str = tf.read().rstrip("\n")
    new_bytes = new_str.encode("utf-8")

    with open(GGUF_PATH, "rb") as f:
        magic = f.read(4)
        assert magic == b"GGUF", "不是GGUF文件"
        f.seek(4)
        _version = struct.unpack("<I", f.read(4))[0]
        _tensors = struct.unpack("<Q", f.read(8))[0]
        kv_count = struct.unpack("<Q", f.read(8))[0]

        str_len_offset = None
        for _ in range(kv_count):
            key = read_str(f)
            vtype = struct.unpack("<I", f.read(4))[0]
            if key == "tokenizer.chat_template":
                assert vtype == 8, f"chat_template类型异常: {vtype}"
                str_len_offset = f.tell()
                old_len = struct.unpack("<Q", f.read(8))[0]
                data_offset = f.tell()
                old_bytes = f.read(old_len)
                break
            skip_value(f, vtype)

        if str_len_offset is None:
            print("未找到 tokenizer.chat_template")
            return 1

    print(f"原模板字节数: {old_len}, 新模板字节数: {len(new_bytes)}")

    with open(BACKUP_PATH, "wb") as bf:
        bf.write(old_bytes)
    print(f"原模板已备份到: {BACKUP_PATH}")

    diff = old_len - len(new_bytes)
    if diff < 0:
        print(f"错误: 新模板比原模板长 {abs(diff)} 字节, 无法原地替换, 已中止, 未修改任何文件")
        return 1
    if diff > 0:
        assert new_bytes.endswith(b"%}"), "模板结尾不是 %}, 无法补齐"
        new_bytes = new_bytes[:-2] + b" " * diff + b"%}"
    assert len(new_bytes) == old_len

    with open(GGUF_PATH, "r+b") as f:
        f.seek(data_offset)
        f.write(new_bytes)
        f.flush()

    with open(GGUF_PATH, "rb") as f:
        f.seek(str_len_offset)
        check_len = struct.unpack("<Q", f.read(8))[0]
        check_bytes = f.read(check_len)
    assert check_len == old_len and check_bytes == new_bytes, "写入后校验失败"
    print("写入成功, 校验通过")
    print("新模板结尾预览:", check_bytes[-120:].decode("utf-8", errors="replace"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
