import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GGUF_TYPES = {
    0: "uint8", 1: "int8", 2: "uint16", 3: "int16", 4: "uint32", 5: "int32",
    6: "float32", 7: "bool", 8: "string", 9: "array", 10: "uint64",
    11: "int64", 12: "float64",
}

def read_str(f):
    n = struct.unpack("<Q", f.read(8))[0]
    return f.read(n).decode("utf-8", errors="replace")

def read_value(f, vtype):
    if vtype == 0: return struct.unpack("<B", f.read(1))[0]
    if vtype == 1: return struct.unpack("<b", f.read(1))[0]
    if vtype == 2: return struct.unpack("<H", f.read(2))[0]
    if vtype == 3: return struct.unpack("<h", f.read(2))[0]
    if vtype == 4: return struct.unpack("<I", f.read(4))[0]
    if vtype == 5: return struct.unpack("<i", f.read(4))[0]
    if vtype == 6: return struct.unpack("<f", f.read(4))[0]
    if vtype == 7: return struct.unpack("<?", f.read(1))[0]
    if vtype == 8: return read_str(f)
    if vtype == 9:
        etype = struct.unpack("<I", f.read(4))[0]
        n = struct.unpack("<Q", f.read(8))[0]
        vals = [read_value(f, etype) for _ in range(n)]
        return vals
    if vtype == 10: return struct.unpack("<Q", f.read(8))[0]
    if vtype == 11: return struct.unpack("<q", f.read(8))[0]
    if vtype == 12: return struct.unpack("<d", f.read(8))[0]
    raise ValueError(f"unknown type {vtype}")

def main(path):
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"GGUF":
            print("不是GGUF文件:", magic)
            return
        version = struct.unpack("<I", f.read(4))[0]
        tensor_count = struct.unpack("<Q", f.read(8))[0]
        kv_count = struct.unpack("<Q", f.read(8))[0]
        print(f"GGUF version={version}, tensors={tensor_count}, kv={kv_count}")
        print("=" * 60)
        for _ in range(kv_count):
            key = read_str(f)
            vtype = struct.unpack("<I", f.read(4))[0]
            val = read_value(f, vtype)
            if isinstance(val, list) and len(val) > 8:
                preview = f"[array len={len(val)}, first8={val[:8]}]"
            elif isinstance(val, str) and len(val) > 20000:
                preview = val[:20000] + f"\n...(截断, 总长{len(val)})"
            else:
                preview = val
            print(f"[{key}] ({GGUF_TYPES.get(vtype, vtype)}):")
            print(preview)
            print("-" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python gguf_meta_dump.py your_model.gguf")
        sys.exit(1)
    main(sys.argv[1])
