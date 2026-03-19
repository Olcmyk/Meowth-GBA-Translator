#!/usr/bin/env python3
"""蓝宝石假翻译：将 work/text.json 的 original 直接作为 translated 写入
用于测试字库补丁是否正常工作（文字不乱码即为成功）
"""
import json
import re
import sys

def fake_translate(text: str) -> str:
    """把每个单词最后一个字母替换为 2，用于验证文字是否正常显示"""
    # 去掉引号
    t = text
    if t.startswith('"') and t.endswith('"'):
        t = t[1:-1]
    # 替换：字母后面跟空格 → 字母改为2
    t = re.sub(r'([a-zA-Z])( )', r'2\2', t)
    return '"' + t + '"'

def main():
    input_path = 'work/text.json'
    output_path = 'work/text_translated.json'

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    count = 0
    for entry in data.get('entries', []):
        original = entry.get('original', '')
        entry['translated'] = fake_translate(original)
        count += 1

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'Fake-translated {count} entries → {output_path}')
    print(f'Example: {fake_translate("Hello World")}')

if __name__ == '__main__':
    main()
