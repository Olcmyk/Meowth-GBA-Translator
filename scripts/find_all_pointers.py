#!/usr/bin/env python3
"""
暴力搜索ROM中所有被指针引用的文本
"""
import json
from pathlib import Path
from collections import defaultdict

def is_valid_pcs_text(rom: bytes, addr: int, min_len: int = 8) -> bool:
    """检查地址处是否是有效的PCS文本"""
    if addr + min_len > len(rom):
        return False
    
    # 检查是否以0xFF结尾（PCS文本终止符）
    text_len = 0
    for i in range(addr, min(addr + 500, len(rom))):
        if rom[i] == 0xFF:
            text_len = i - addr + 1
            break
    
    if text_len < min_len:
        return False
    
    # 检查是否包含足够的字母
    letters = 0
    for i in range(addr, addr + text_len):
        b = rom[i]
        if (0xBB <= b <= 0xD4) or (0xD5 <= b <= 0xEE):  # A-Z or a-z
            letters += 1
    
    return letters >= 3  # 至少3个字母

def find_all_text_addresses(rom: bytes, start: int = 0x2C0000, end: int = 0x400000) -> list:
    """找所有可能是文本的地址"""
    texts = []
    for addr in range(start, min(end, len(rom) - 8)):
        if is_valid_pcs_text(rom, addr):
            texts.append(addr)
    return texts

def find_pointers_to_address(rom: bytes, target_addr: int, 
                            search_start: int = 0x020000, 
                            search_end: int = 0x01FD0000) -> list:
    """找所有指向target_addr的指针"""
    POINTER_OFFSET = 0x08000000
    target_pointer = (POINTER_OFFSET + target_addr).to_bytes(4, "little")
    
    pointers = []
    for addr in range(search_start, min(search_end, len(rom) - 3), 4):
        if rom[addr:addr+4] == target_pointer:
            pointers.append(addr)
    
    return pointers

def extract_text_at(rom: bytes, addr: int) -> str:
    """提取地址处的PCS文本"""
    result = ""
    for i in range(addr, min(addr + 500, len(rom))):
        b = rom[i]
        if b == 0xFF:
            break
        elif b == 0x00:
            result += " "
        elif b == 0xA3:
            result += "2"
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
    
    print("Step 1: 扫描ROM找所有可能的文本...")
    texts = find_all_text_addresses(rom)
    print(f"  找到 {len(texts)} 个可能的文本地址")
    
    print("\nStep 2: 对每个文本搜索指针...")
    text_to_pointers = defaultdict(list)
    
    for i, text_addr in enumerate(texts):
        if i % 100 == 0:
            print(f"  处理中... {i}/{len(texts)}")
        
        pointers = find_pointers_to_address(rom, text_addr)
        if pointers:
            text_to_pointers[text_addr] = pointers
    
    print(f"\n找到 {len(text_to_pointers)} 个有指针指向的文本")
    
    # 保存结果
    result = []
    for text_addr in sorted(text_to_pointers.keys()):
        pointers = text_to_pointers[text_addr]
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
    print(f"总计: {len(result)} 个有指针的文本")

if __name__ == "__main__":
    main()
