# Meowth GBA Translator - 技术文档

## 架构概览

Meowth 是一个基于 HexManiac Advance 的 GBA ROM 汉化工具，采用三阶段流水线设计。

### 三阶段流水线

```
ROM 文件 → [1. Extract] → text.json → [2. Translate] → text_translated.json → [3. Apply] → 汉化 ROM
```

1. **Extract（提取）**: 从 ROM 中提取所有可翻译文本
2. **Translate（翻译）**: 使用 AI API 批量翻译文本
3. **Apply（应用）**: 将翻译写入 ROM，生成汉化版本

---

## 核心技术：三步走文本提取

为了最大化文本覆盖率并保证准确性，我们采用三步走提取策略：

### 第一步：结构化文本（100% 准确）

提取 HexManiac 已识别的表格数据：
- 宝可梦名称 (`data.pokemon.names`)
- 道具名称 (`data.items.stats`)
- 招式名称 (`data.pokemon.moves.names`)
- 特性名称 (`data.abilities.names`)
- 地图名称 (`data.maps.names`)
- 等等...

**优点**: 完全可靠，HMA 已经解析了表格结构
**缺点**: 只覆盖结构化数据，不包括对话文本

### 第二步：LoadPointer 文本（非常安全）

扫描 ROM 中的 `loadpointer` 指令，提取脚本引用的文本：

```assembly
loadpointer 0x0 0x81A5B68  ; 加载文本指针到寄存器
```

**优点**:
- 脚本明确引用，非常可靠
- 覆盖大部分对话和剧情文本

**缺点**:
- 不包括 ARM 代码直接引用的文本
- 需要解析 GBA 汇编指令

### 第三步：全局指针扫描（需要验证）

扫描整个 ROM，查找所有指向有效 PCS 文本的指针：

```
ROM 中的 4 字节对齐数据 → 解析为指针 → 验证目标是否为有效文本
```

**验证规则**:
- 文本必须以 0xFF 结尾
- 包含合理的 PCS 字符
- 有小写字母、空格、标点
- 不在黑名单中

**优点**: 覆盖率最高，能找到所有文本
**缺点**: 可能误判二进制数据为文本（通过严格验证降低误报）

---

## 翻译流程

### 预处理（Preprocess）

1. **剥离引号**: `"Hello"` → `Hello`
2. **标准化复数**: `POKEMON BALLS` → `POKEMON BALL{PLURAL0}`
3. **区分换行类型**:
   - 短行后的 `\n` → `{SEMNL}` (语义换行，保留)
   - 长行后的 `\n` → 空格 (排版换行，去掉)
4. **提取控制码**: `[player]` → `{C0}`

### AI 翻译

- 使用 DeepSeek/OpenAI API
- 批量翻译（默认 30 条/批）
- MD5 缓存避免重复翻译
- 保留控制码占位符

### 后处理（Postprocess）

1. **还原控制码**: `{C0}` → `[player]`
2. **还原复数**: `{PLURAL0}` → `S`
3. **还原换行**: `{SEMNL}` → `\n`, `{PARA}` → `\n\n`
4. **自动换行**: 按中文字符宽度（2 单位）重新排版
5. **分页**: 每 2 行一页，用 `\p` 翻页

---

## 字库补丁

支持两种字库补丁方式：

### 1. 原版 ROM（armips 方式）

使用 Pokemon_GBA_Font_Patch + armips 汇编器：

```
ROM → 复制到 baserom_FR.gba → armips main_FR.asm → chsfontrom_FR.gba
```

**适用于**:
- 美版火红 (BPRE)
- 美版绿宝石 (BPEE)
- 16MB 原版 ROM

### 2. Decomp 改版（二进制补丁）

直接修改 ROM 二进制数据，无需 armips：

```
ROM → 检测版本 → 定位补丁位置 → 写入字库数据 → 应用补丁
```

**适用于**:
- pokeemerald 重编译工程
- pokefirered 重编译工程
- 大于 16MB 的改版 ROM

**实现**: `DecompFontPatcher.cs`

---

## 文本写入

### ROM 扩展

1. 扩展 ROM 到 32MB
2. 字库数据写在高地址（ROM 末尾）
3. 翻译文本写在中间空闲区域

```
[原始 ROM 16MB] [翻译文本区] [字库数据] [填充到 32MB]
```

### 指针更新

- **表格文本**: 直接覆盖原地址（如果长度允许）
- **指针文本**:
  - 短文本：原地覆盖
  - 长文本：写入扩展区，更新所有指针源

---

## 复数形式处理

### 问题

表格中有 `POKEMON BALL`（单数），但文本中可能是 `POKEMON BALLS`（复数）。

### 解决方案

预处理时标准化复数：

```
POKEMON BALLS → POKEMON BALL{PLURAL0}
```

这样翻译时可以匹配表格词汇，翻译后再还原：

```
宝可梦球{PLURAL0} → 宝可梦球S
```

**实现**: `TextPreprocessor.NormalizePlurals()`

---

## 项目结构

```
src/MeowthBridge/
├── Program.cs              # 主入口，三阶段流水线
├── TextExtractor.cs        # 文本提取（三步走）
├── RealTranslator.cs       # AI 翻译
├── TextPreprocessor.cs     # 预处理/后处理
├── TextWriter.cs           # 文本写入
├── ChsEncoder.cs           # 中文编码器
├── DecompFontPatcher.cs    # Decomp 字库补丁
└── RomLoader.cs            # ROM 加载器
```

---

## 使用示例

```bash
# 1. 提取文本
dotnet run --project src/MeowthBridge extract pokemon_firered.gba

# 2. 翻译文本
dotnet run --project src/MeowthBridge translate --api-key YOUR_KEY

# 3. 应用翻译
dotnet run --project src/MeowthBridge apply pokemon_firered.gba
```

输出: `outputs/firered_cn_20260318_123456.gba`

---

## 技术亮点

1. **三步走提取**: 结构化 → LoadPointer → 全局扫描，覆盖率高
2. **智能换行**: 区分语义换行和排版换行
3. **复数支持**: 自动处理 S/ES 词尾
4. **双字库方案**: 支持原版和 decomp 改版
5. **缓存机制**: MD5 缓存避免重复翻译
6. **批量翻译**: 提高 API 效率
7. **自动排版**: 按中文字符宽度重新换行

---

## 依赖

- .NET 8.0
- HexManiac.Core (文本提取)
- armips (原版字库补丁)
- DeepSeek/OpenAI API (翻译)

---

## 许可证

MIT License
