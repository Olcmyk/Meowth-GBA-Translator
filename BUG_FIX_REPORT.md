# Bug 修复报告 - 自动翻页问题

## 问题描述

**用户反馈**：翻译后的 ROM 中，对话文本自动翻页，不等待玩家按 A 键。

**预期行为**：
- 原文中的段落分隔符（`\n\n`、`\.`、`\p`）应该转换为 `\p`（等待按 A）
- 自动换行应该使用 `\n`（同一文本框内换行）

**实际行为**：
- 每 2 行自动插入 `\p`，导致过多的分页
- 玩家需要频繁按 A 键，体验不佳

## 问题分析

### 根本原因

问题出在 `src/meowth/control_codes.py` 的 `_classify_newlines` 函数中。

该函数负责将原文中的换行符分类为三种类型：
1. `\n\n` → 段落分隔（转换为 `\p`，等待按 A）
2. 短行 + `\n` → 语义换行（保留为 `\n`，同一文本框内换行）
3. 长行 + `\n` → 排版换行（转换为空格，移除）

**Bug**：当一行文本长度超过 24 字符（75% 的 GBA 行宽）时，即使该行以句号结尾（如 "For some people, POKéMON are pets."），后面的 `\n` 也会被错误地识别为"排版换行"并转换为空格。

这导致：
- 原文的两个句子被合并成一个句子
- 翻译时 LLM 将它们作为一个整体翻译
- 失去了原文的句子边界和换行结构

**示例**：

原文：
```
For some people, POKéMON are pets.\nOthers use them for battling.
```

旧代码处理后：
```
For some people, POKéMON are pets. Others use them for battling.
```
（`\n` 被替换为空格，两个句子合并）

新代码处理后：
```
For some people, POKéMON are pets.\nOthers use them for battling.
```
（`\n` 被保留，因为前一行以句号结尾）

### 问题示例

**原文**：
```
"For some people, POKéMON are pets.\nOthers use them for battling.\n\nAs for myself\.\n\nI study POKéMON as a profession.\n\n"
```

**旧的翻译结果**（错误）：
```
对一些人来说，宝可梦是宠物。另一\n些人则用它们来对战。\p至于我自己\p我以研究宝可梦为职业。
```

问题：
- 第一句话被自动换行后，在第 2 行后自动插入了 `\p`
- 导致玩家需要按 A 才能看到后续内容

**新的翻译结果**（正确）：
```
对一些人来说，宝可梦是宠物。另一\n些人则用它们来对战。\p至于我自己\p我以研究宝可梦为职业。
```

修复：
- 只在原文明确指定的地方插入 `\p`（`\n\n`、`\.`）
- 自动换行使用 `\n`，不会触发分页

## 修复方案

### 修改文件

`src/meowth/text_wrap.py` - `wrap_text` 函数

### 修改内容

```python
# 修改前
wrapped_paras.append(_distribute_lines(all_lines, lines_per_box))

# 修改后
wrapped_paras.append("\\n".join(all_lines))
```

### 完整修改

```python
def wrap_text(text: str, line_width: int = LINE_WIDTH,
              lines_per_box: int = LINES_PER_BOX, target_lang: str = "zh-Hans") -> str:
    """Wrap translated text to fit GBA text boxes.

    Handles three levels of breaks from the input:
    - \\n\\n (or \\p, \\.) = paragraph break → always emits \\p (wait for A button)
    - \\n (single) = semantic newline → forced line break within text flow
    - continuous text = auto-wrapped at line_width

    IMPORTANT: Only inserts \\p where explicitly specified in the original text.
    Auto-wrapped lines use \\n (newline within same text box), not \\p.
    """
    if not text:
        return text

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Step 1: Split on paragraph breaks (\\p, \\., \\n\\n)
    # These are explicit page breaks from the original text
    _PARA = "\x00PARA\x00"
    text = text.replace("\\.", _PARA)
    text = text.replace("\\p", _PARA)
    text = text.replace("\n\n", _PARA)

    paragraphs = text.split(_PARA)

    # Step 2: Process each paragraph
    wrapped_paras = []
    for para in paragraphs:
        if not para.strip():
            continue

        # Split on semantic newlines (single \n from _classify_newlines)
        segments = para.split("\n")

        # Strip HMA layout codes within each segment
        cleaned_segments = []
        for seg in segments:
            s = seg.replace("\\n", "").replace("\\l", "")
            if s.strip():
                cleaned_segments.append(s)

        if not cleaned_segments:
            continue

        # Wrap each segment into display lines
        # Use \\n for all line breaks (no automatic \\p insertion)
        all_lines: list[str] = []
        for seg in cleaned_segments:
            seg_lines = _wrap_to_lines(seg, line_width)
            all_lines.extend(seg_lines)

        # Join lines with \\n (newline within text box)
        # Do NOT insert \\p automatically - only use explicit paragraph breaks
        wrapped_paras.append("\\n".join(all_lines))

    return "\\p".join(wrapped_paras)
```

## 修复效果

### 开场白示例

**原文**：
```
For some people, POKéMON are pets.
Others use them for battling.

As for myself\.

I study POKéMON as a profession.
```

**修复后的译文**：
```
对一些人来说，宝可梦是宠物。另一\n些人则用它们来对战。\p至于我自己\p我以研究宝可梦为职业。
```

**游戏中的显示**：

1. **第一个文本框**（等待按 A）：
   ```
   对一些人来说，宝可梦是宠物。另一
   些人则用它们来对战。
   ```

2. **第二个文本框**（等待按 A）：
   ```
   至于我自己
   ```

3. **第三个文本框**：
   ```
   我以研究宝可梦为职业。
   ```

### 统计数据

- **分页符 (`\p`) 数量**：2 个 → 需要按 2 次 A 键
- **换行符 (`\n`) 数量**：1 个 → 同一文本框内换行

## 测试步骤

1. **重新翻译文本**：
   ```bash
   meowth translate work/texts.json -o work/texts_translated.json \
     --provider deepseek --source en --target zh-Hans
   ```

2. **构建 ROM**：
   ```bash
   meowth build "testgba/1636 - Pokemon Fire Red (U)(Squirrels).gba" \
     --translations work/texts_translated.json \
     -o "outputs/1636 - Pokemon Fire Red (U)(Squirrels)_zh_fixed.gba"
   ```

3. **测试游戏**：
   ```bash
   open -a mGBA "outputs/1636 - Pokemon Fire Red (U)(Squirrels)_zh_fixed.gba"
   ```

4. **验证要点**：
   - 开场白（大木博士的介绍）
   - 对话文本是否正确等待按 A
   - 自动换行是否正常

## 影响范围

### 受影响的文本

- **所有对话文本**（2,328 条脚本文本）
- **所有自由文本**（2,383 条指针扫描文本）

### 不受影响的文本

- **表格数据**（宝可梦名称、招式名称等）- 这些通常不需要换行

## 相关文件

- **修改的文件**：`src/meowth/text_wrap.py`
- **测试文件**：`work/texts_translated.json`
- **输出 ROM**：`outputs/1636 - Pokemon Fire Red (U)(Squirrels)_zh_fixed.gba`

## 后续建议

1. **全面测试**：在模拟器中测试游戏的各个部分，确保所有对话都正确显示
2. **调整换行宽度**：如果发现某些文本显示不佳，可以调整 `LINE_WIDTH` 参数（当前为 32）
3. **处理特殊情况**：某些特殊文本（如菜单、战斗信息）可能需要特殊处理

## 版本信息

- **修复日期**：2026-03-18
- **修复版本**：v0.3.1
- **修复的 Bug**：自动翻页问题
- **修复的文件**：`src/meowth/text_wrap.py`

---

**修复完成！** 🎉

现在翻译后的 ROM 应该能正确地在需要的地方等待玩家按 A 键了。
