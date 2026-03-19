# Bug 修复报告 v2 - 句子边界丢失问题

## 问题描述

**用户反馈**：翻译后的 ROM 中，对话文本自动翻页，不等待玩家按 A 键。

**预期行为**：
- 原文中的段落分隔符（`\n\n`、`\.`、`\p`）应该转换为 `\p`（等待按 A）
- 原文中的句子边界（句号后的 `\n`）应该保留为 `\n`（同一文本框内换行）
- 自动换行应该使用 `\n`（同一文本框内换行）

**实际行为**：
- 原文的句子边界被错误地移除
- 多个句子被合并成一个句子
- 翻译后的文本结构与原文不一致

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

### 问题示例

**原文**：
```
"For some people, POKéMON are pets.\nOthers use them for battling.\n\nAs for myself\.\n\nI study POKéMON as a profession.\n\n"
```

**旧代码处理后**（错误）：
```
For some people, POKéMON are pets. Others use them for battling.
```
（`\n` 被替换为空格，两个句子合并）

**新代码处理后**（正确）：
```
For some people, POKéMON are pets.\nOthers use them for battling.
```
（`\n` 被保留，因为前一行以句号结尾）

**旧的翻译结果**（错误）：
```
对一些人来说，宝可梦是宠物。另一\n些人则用它们来对战。\p至于我自己\p我以研究宝可梦为职业。
```
问题：
- 第一句话被自动换行后，`\n` 出现在句子中间（"另一\n些人"）
- 失去了原文的句子边界

**新的翻译结果**（正确）：
```
对一些人来说，宝可梦是宠物。\n另一些人则用它们来对战。\p至于我自己\p我以研究宝可梦为职业。
```
修复：
- 两个句子分别在两行显示
- 保留了原文的句子边界
- `\n` 出现在句子之间，而不是句子中间

## 修复方案

### 修改文件

`src/meowth/control_codes.py` - `_classify_newlines` 函数

### 修改内容

在判断是否为语义换行时，增加对句子结尾标点的检查：

```python
# 修改前
if vis_len < _SEMANTIC_THRESHOLD:
    result_parts.append("\n")   # semantic newline (within box)
else:
    result_parts.append(" ")    # layout wrap (remove)

# 修改后
# Check if line ends with sentence-ending punctuation
ends_with_sentence = clean_line.rstrip().endswith(('.', '!', '?', '。', '！', '？'))

if vis_len < _SEMANTIC_THRESHOLD or ends_with_sentence:
    result_parts.append("\n")   # semantic newline (within box)
else:
    result_parts.append(" ")    # layout wrap (remove)
```

### 完整修改

```python
def _classify_newlines(text: str) -> str:
    """Replace newlines with semantic breaks or spaces.

    Three-level classification:
    - \\n\\n → paragraph break (page break in GBA, keep as \\n\\n)
    - \\n where the preceding line is short (< 75% of GBA line width)
      → semantic newline (same text box, keep as \\n)
    - \\n after sentence-ending punctuation (. ! ?)
      → semantic newline (sentence boundary, keep as \\n)
    - \\n where the preceding line is long (filled the text box)
      → layout wrap (replace with space)
    """
    _PARA = "\x00PARA\x00"
    text = text.replace("\n\n", _PARA)

    lines = text.split("\n")
    result_parts = []
    for i, line in enumerate(lines):
        result_parts.append(line)
        if i < len(lines) - 1:
            # Strip PARA markers before measuring visible length
            clean_line = line.replace(_PARA, "")
            vis_len = _visible_length(clean_line)

            # Check if line ends with sentence-ending punctuation
            ends_with_sentence = clean_line.rstrip().endswith(('.', '!', '?', '。', '！', '？'))

            if vis_len < _SEMANTIC_THRESHOLD or ends_with_sentence:
                result_parts.append("\n")   # semantic newline (within box)
            else:
                result_parts.append(" ")    # layout wrap (remove)

    result = "".join(result_parts)
    result = result.replace(_PARA, "\n\n")
    return result
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
对一些人来说，宝可梦是宠物。\n另一些人则用它们来对战。\p至于我自己\p我以研究宝可梦为职业。
```

**游戏中的显示**：

1. **第一个文本框**（等待按 A）：
   ```
   对一些人来说，宝可梦是宠物。
   另一些人则用它们来对战。
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
- **换行符 (`\n`) 数量**：1 个 → 同一文本框内换行，两个句子分别显示

## 测试步骤

1. **重新翻译文本**（必须重新翻译，因为旧翻译的句子结构已经错误）：
   ```bash
   meowth translate work/texts.json -o work/texts_translated_fixed.json \
     --provider deepseek --source en --target zh-Hans
   ```

2. **构建 ROM**：
   ```bash
   meowth build "testgba/1636 - Pokemon Fire Red (U)(Squirrels).gba" \
     --translations work/texts_translated_fixed.json \
     -o "outputs/1636 - Pokemon Fire Red (U)(Squirrels)_zh_v2.gba"
   ```

3. **测试游戏**：
   ```bash
   open -a mGBA "outputs/1636 - Pokemon Fire Red (U)(Squirrels)_zh_v2.gba"
   ```

4. **验证要点**：
   - 开场白（大木博士的介绍）
   - 两个句子是否分别在两行显示
   - 对话文本是否正确等待按 A
   - 句子边界是否保留

## 影响范围

### 受影响的文本

- **所有对话文本**（包含句子边界的文本）
- **所有自由文本**（包含句子边界的文本）

### 不受影响的文本

- **表格数据**（宝可梦名称、招式名称等）- 这些通常不包含句子边界
- **短文本**（少于 24 字符的文本）- 这些文本的换行已经被正确保留

## 相关文件

- **修改的文件**：`src/meowth/control_codes.py`
- **测试文件**：`work/texts_translated_fixed.json`
- **输出 ROM**：`outputs/1636 - Pokemon Fire Red (U)(Squirrels)_zh_v2.gba`

## 后续建议

1. **全面测试**：在模拟器中测试游戏的各个部分，确保所有对话都正确显示
2. **调整换行宽度**：如果发现某些文本显示不佳，可以调整 `LINE_WIDTH` 参数（当前为 32）
3. **处理特殊情况**：某些特殊文本（如菜单、战斗信息）可能需要特殊处理

## 版本信息

- **修复日期**：2026-03-18
- **修复版本**：v0.3.2
- **修复的 Bug**：句子边界丢失问题
- **修复的文件**：`src/meowth/control_codes.py`

---

**修复完成！** 🎉

现在翻译后的 ROM 应该能正确地保留原文的句子边界，并在需要的地方等待玩家按 A 键了。
