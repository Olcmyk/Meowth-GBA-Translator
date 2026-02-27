# GBA 宝可梦翻译工具使用指南

## 完整翻译流程

### 1. 提取文本

从 ROM 文件中提取所有文本（表格数据 + 脚本对话）：

```bash
dotnet run --project src/MeowthBridge extract testgba/firered_en.gba -o testgba/firered_extracted.json
```

**输出**：
- `testgba/firered_extracted.json` - 包含 4355 条文本

---

### 2. 翻译文本

#### 方式 A: 假翻译（测试用）

将每个单词的最后一个字母改为 "2"，用于测试流程：

```bash
dotnet run --project src/MeowthBridge fake-translate testgba/firered_extracted.json -o testgba/firered_translated.json
```

**特点**：
- 免费，无需 API
- 保留 `[player]`、`[rival]` 等占位符
- 只翻译"空格+单词+空格"模式的单词

#### 方式 B: 真翻译（使用 OpenAI API）

调用 OpenAI API 进行真实翻译：

```bash
dotnet run --project src/MeowthBridge translate testgba/firered_extracted.json YOUR_API_KEY -o testgba/firered_translated.json
```

**可选参数**：
- `-o <path>` - 输出文件路径（默认：input_translated.json）
- `--api-url <url>` - API 端点（默认：OpenAI）
- `--model <model>` - 模型名称（默认：gpt-4o-mini）
- `--batch <size>` - 并行请求数（默认：10）
- `--delay <ms>` - 批次间延迟（默认：1000ms）

**示例**：

```bash
# 使用默认设置
dotnet run --project src/MeowthBridge translate testgba/firered_extracted.json sk-xxxxx

# 自定义设置
dotnet run --project src/MeowthBridge translate testgba/firered_extracted.json sk-xxxxx \
  -o testgba/firered_cn.json \
  --model gpt-4o \
  --batch 5 \
  --delay 2000

# 使用其他兼容 OpenAI 的 API（如 Azure、本地模型）
dotnet run --project src/MeowthBridge translate testgba/firered_extracted.json YOUR_KEY \
  --api-url https://your-api-endpoint.com/v1/chat/completions \
  --model your-model-name
```

**翻译规则**：
- 保留 `[player]`、`[rival]` 等占位符
- 保留 POKéMON、POKéDEX 等专有名词
- 保留 `\n`、`\p`、`\l` 等控制码
- 保持游戏风格和语气

**预计成本**（使用 gpt-4o-mini）：
- 4355 条文本
- 约 50,000 tokens
- 成本：约 $0.01 - $0.05

---

### 3. 写入 ROM

将翻译后的文本写回 ROM：

```bash
dotnet run --project src/MeowthBridge apply testgba/firered_en.gba testgba/firered_translated.json -o testgba/firered_cn.gba
```

**说明**：
- 自动复制原始 ROM
- 直接写入翻译文本（无长度限制检查）
- 保存为新的 ROM 文件

**输出**：
- `testgba/firered_cn.gba` - 翻译后的 ROM

---

### 4. 验证翻译（可选）

从翻译后的 ROM 重新提取文本，验证是否成功：

```bash
dotnet run --project src/MeowthBridge extract testgba/firered_cn.gba -o testgba/firered_verify.json
```

**验证命令**：

```bash
# 检查特定文本是否被翻译
python3 << 'EOF'
import json
verify = json.load(open('testgba/firered_verify.json'))
for entry in verify['entries'][:10]:
    print(f"{entry['id']}: {entry['original'][:60]}...")
EOF
```

---

## 其他命令

### 列出所有表格锚点

查看 ROM 中所有可用的文本表格：

```bash
dotnet run --project src/MeowthBridge list-anchors testgba/firered_en.gba
```

---

## 完整示例

### 假翻译流程（测试）

```bash
# 1. 提取
dotnet run --project src/MeowthBridge extract testgba/firered_en.gba -o testgba/firered_extracted.json

# 2. 假翻译
dotnet run --project src/MeowthBridge fake-translate testgba/firered_extracted.json -o testgba/firered_fake.json

# 3. 写入
dotnet run --project src/MeowthBridge apply testgba/firered_en.gba testgba/firered_fake.json -o testgba/firered_fake.gba

# 4. 用模拟器测试 testgba/firered_fake.gba
```

### 真翻译流程（生产）

```bash
# 1. 提取
dotnet run --project src/MeowthBridge extract testgba/firered_en.gba -o testgba/firered_extracted.json

# 2. 真翻译（需要 API Key）
dotnet run --project src/MeowthBridge translate testgba/firered_extracted.json YOUR_API_KEY -o testgba/firered_cn.json

# 3. 写入
dotnet run --project src/MeowthBridge apply testgba/firered_en.gba testgba/firered_cn.json -o testgba/firered_cn.gba

# 4. 验证
dotnet run --project src/MeowthBridge extract testgba/firered_cn.gba -o testgba/firered_verify.json

# 5. 用模拟器测试 testgba/firered_cn.gba
```

---

## 注意事项

### 翻译质量

1. **保留占位符**：`[player]`、`[rival]` 必须保持不变
2. **控制码**：`\n`（换行）、`\p`（换页）等必须保留
3. **专有名词**：POKéMON、POKéDEX 等建议保持英文
4. **长度限制**：翻译后的文本会直接覆盖原文，如果过长可能覆盖其他数据

### API 使用

1. **速率限制**：使用 `--batch` 和 `--delay` 控制请求速度
2. **成本控制**：先用少量数据测试，确认效果后再全量翻译
3. **错误处理**：如果翻译失败，会保留原文

### ROM 安全

1. **备份原始 ROM**：翻译前务必备份
2. **测试验证**：翻译后用模拟器测试游戏是否正常运行
3. **版本控制**：建议使用 git 管理翻译文件

---

## 故障排除

### 问题：翻译后游戏崩溃

**原因**：翻译文本过长，覆盖了其他数据

**解决**：
1. 检查翻译文本长度
2. 使用更简洁的翻译
3. 考虑使用缩写

### 问题：占位符不工作

**原因**：`[player]` 等被翻译了

**解决**：
1. 检查翻译 API 的提示词
2. 确保翻译器保留中括号内容

### 问题：API 请求失败

**原因**：速率限制或 API Key 无效

**解决**：
1. 检查 API Key 是否正确
2. 增加 `--delay` 参数
3. 减少 `--batch` 参数

---

## 支持的 ROM

- 宝可梦火红/叶绿（FireRed/LeafGreen）
- 宝可梦绿宝石（Emerald）
- 其他第三世代宝可梦游戏

---

## 技术细节

### 提取策略

1. **表格数据**：从 HMA 识别的表格结构提取
2. **脚本文本**：通过 loadpointer (0x0F) 指令扫描

### 写入策略

- 直接覆盖原始文本位置
- 不进行长度检查（假设翻译文本长度合适）
- 使用 PCS 编码写入

### 安全保证

- 只提取有明确引用的文本
- 避免误判数据结构为文本
- 保留游戏控制码和占位符
