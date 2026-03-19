#!/usr/bin/env python3
"""
为表格中的文本找指针
"""
import json
from pathlib import Path

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

def main():
    rom_path = Path("testgba/1986 - Pokemon Emerald (U)(TrashMan).gba")
    rom = rom_path.read_bytes()
    
    # 加载提取的文本
    data = json.loads(Path("work/text.json").read_text("utf-8"))
    
    print("为表格文本搜索指针...")
    
    # 只处理无指针的表格文本
    table_texts = [e for e in data["entries"] 
                   if not e.get("is_pointer_based") and e.get("table_name")]
    
    print(f"处理 {len(table_texts)} 个表格文本...")
    
    updated = 0
    for i, entry in enumerate(table_texts):
        if i % 100 == 0:
            print(f"  {i}/{len(table_texts)}")
        
        addr = int(entry["address"].replace("0x", ""), 16)
        pointers = find_pointers_to_address(rom, addr)
        
        if pointers:
            entry["pointer_sources"] = [f"0x{p:06X}" for p in pointers]
            entry["is_pointer_based"] = True
            updated += 1
    
    print(f"\n找到 {updated} 个有指针的表格文本")
    
    # 保存更新后的数据
    output_path = Path("work/text_with_table_pointers.json")
    output_path.write_text(json.dumps({"entries": data["entries"]}, indent=2, ensure_ascii=False))
    print(f"保存到: {output_path}")

if __name__ == "__main__":
    main()
