#!/usr/bin/env python3
"""Seaglass 假翻译：把每个单词后两个字母改为'正'
如果单词只有一个字母则不改动
"""
import json
import re


def fake_translate(text: str) -> str:
    t = text
    if t.startswith('"') and t.endswith('"'):
        t = t[1:-1]

    def replace_word(m):
        word = m.group(0)
        if len(word) <= 1:
            return word
        elif len(word) == 2:
            return word[0] + '正'
        else:
            return word[:-2] + '正正'

    t = re.sub(r"[a-zA-Z']+", replace_word, t)
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
    print(f'Example: {fake_translate("I am fine")}')


if __name__ == '__main__':
    main()
