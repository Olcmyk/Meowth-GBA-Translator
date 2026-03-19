#!/usr/bin/env python3
"""
快速方案: 遍历所有指针,看它们指向什么文本
"""
import json
from pathlib import Path
from collections import defaultdict

def extract_text_at(rom: bytes, addr: int, max_len: int = 200) -> str:
    """提取地址处的PCS文本"""
    result = ""
    for i in range(addr, min(addr + max_len, len(rom))):
        b = rom[i]
        if b == 0xFF:
            break
        elif b == 0x00:
            result += " "
        elif 0xBB <= b <= 0xD4:
            result += chr(ord('A') + (b - 0xBB))
        elif 0xD5 <= b <= 0xEE:
            result += chr(ord('a') + (b - 0xD5))
        else:
            result += f"[{b:02X}]"
    return result

def main():
    rom_path = Path("testgba/1986 - Pokemon Emerald (U)(TrashMan).gba")
    rom = rom_path.read_bytes()
    
    POINTER_OFFSET = 0x08000000
    
    print("遍历所有指针...")
    pointers_found = defaultdict(list)
    
    # 遍历 ROM 中所有可能是指针的位置
    # 指针通常在数据段，从 0x020000 开始
    for ptr_addr in range(0x020000, min(0x01FD0000, len(rom) - 3), 4):
        ptr_bytes = rom[ptr_addr:ptr_addr+4]
        ptr_value = int.from_bytes(ptr_bytes, "little")
        
        # 检查这个指针是否指向有效的 ROM 地址
        target_addr = ptr_value - POINTER_OFFSET
        
        if 0 <= target_addr < len(rom):
            # 检查目标地址是否是文本
            text = extract_text_at(rom, target_addr)
            if len(text) > 8 and text.count(' ') > 0:  # 至少8字符且有空格
                pointers_found[target_addr].append(ptr_addr)
        
        if ptr_addr % 100000 == 0:
            print(f"  处理中... 0x{ptr_addr:06X}")
    
    print(f"\n找到 {len(pointers_found)} 个有指针指向的文本地址")
    
    # 保存结果
    result = []
    for text_addr in sorted(pointers_found.keys()):
        pointers = pointers_found[text_addr]
        text = extract_text_at(rom, text_addr)
        
        result.append({
            "address": f"0x{text_addr:06X}",
            "text": text[:100],
            "pointers": [f"0x{p:06X}" for p in pointers],
            "pointer_count": len(pointers)
        })
    
    output_path = Path("work/all_pointed_texts.json")
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\n结果保存到: {output_path}")

if __name__ == "__main__":
    main()
