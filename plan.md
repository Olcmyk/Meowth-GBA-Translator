# Meowth-GBA-Translator 实现计划 v2

## Context

构建一个自动化 GBA 宝可梦翻译工具，实现一键英译中。先聚焦 FireRed (BPRE)。

**调试规则：**
- DeepSeek API 的请求和响应都缓存到本地 `work/cache/`，避免重复调用浪费钱
- 每次输出结果保存到 `outputs/` 并带时间戳，不覆盖之前的结果
- 每次成功输出中文 GBA 文件时 git commit
- `testgba/firered_en.gba` 是调试用的英文版火红，不可修改

## 已有资源

- **HexManiacAdvance** (`HexManiacAdvance/`) — .NET 6.0 GBA ROM 编辑库
- **Pokemon_GBA_Font_Patch** (`Pokemon_GBA_Font_Patch/`) — 成熟的 GBA 中文字库 patch
- **PokeAPI** (`pokeapi-master/`) — 宝可梦多语言术语数据 (CSV)
- **armips** (`tools/armips`) — 已编译的 ARM 汇编器
- **测试 ROM** (`testgba/firered_en.gba`) — 英文火红 16MB

## 核心设计决策

### 为什么用 C# + Python 混合而不是纯 Python？

HMA 的价值在于**提取阶段**：
- 自动发现 ROM 表结构（`data.pokemon.names`, `data.pokemon.moves.names` 等命名锚点）
- 追踪所有指向文本的指针地址（repointing 的前提）
- 正确解析 PCS 编码文本（含控制码）
- 区分文本类别（表内文本 vs 自由文本）

纯 Python 要实现这些需要硬编码大量 ROM 偏移量，且不同 ROM 版本偏移不同。

**HMA 不参与注入**——它不认识 Font Patch 的中文 2 字节编码。注入由 Python 直接操作 ROM 字节完成。

### ROM 扩展策略

16MB → 32MB 扩展（追加 16MB 的 0xFF）。这是 ROM 汉化的标准做法：
- 中文 2 字节编码几乎总是比英文 PCS 长
- 扩展后有 16MB 空闲空间，repointing 变得简单
- HMA 原生支持 ROM 扩展（`ExpandData()`）
- Font Patch 的代码注入在 `0x09FD3000+`，不影响扩展区域

## 技术架构

```
原始 ROM (16MB .gba)
  → [C# MeowthBridge extract] → texts.json (含文本+指针地址+类别)
  → [Python translate] → texts_translated.json
  → [Python build_rom]
      1. 复制原始 ROM
      2. 扩展到 32MB
      3. armips 应用 Font Patch (注入字库+渲染引擎)
      4. 注入翻译文本 (写入扩展区域+更新指针)
  → output_cn.gba
```

关键变化 vs v1：
- **注入完全在 Python 中完成**，不再用 C# 注入
- **Font Patch 和文本注入在同一步骤中**，顺序：先 Font Patch 再注入文本
- **ROM 扩展到 32MB** 解决空间问题

## 项目结构

```
Meowth-GBA-Translator/
├── HexManiacAdvance/                  # HMA 仓库（已有）
├── Pokemon_GBA_Font_Patch/            # 中文字库 patch（已有）
├── pokeapi-master/                    # PokeAPI 数据（已有）
├── testgba/                           # 测试 ROM（已有）
├── tools/armips                       # armips 汇编器（已有）
├── src/
│   ├── MeowthBridge/                  # C# CLI — 仅负责提取
│   │   ├── MeowthBridge.csproj
│   │   ├── Program.cs                 # extract 命令
│   │   ├── RomLoader.cs              # ROM 加载 + 游戏识别
│   │   └── TextExtractor.cs          # 提取文本+指针地址 → JSON
│   └── meowth/                        # Python 主包
│       ├── cli.py                     # CLI 入口
│       ├── pipeline.py                # 主编排流程
│       ├── translator.py              # DeepSeek 翻译 + 缓存
│       ├── control_codes.py           # PCS 控制码保护
│       ├── glossary.py                # PokeAPI 术语表
│       ├── charmap.py                 # Font Patch 字符映射
│       ├── rom_writer.py             # ROM 扩展 + 文本注入 + 指针更新
│       └── font_patch.py            # armips Font Patch 调用
├── work/                              # 工作目录（gitignore）
│   └── cache/                         # DeepSeek API 缓存
├── outputs/                           # 输出目录（gitignore 内容）
├── Meowth.sln
├── pyproject.toml
├── meowth.toml                        # 用户配置
└── .env                               # API 密钥（gitignore）
```

## 实现步骤

### Phase 1: C# MeowthBridge — 文本提取（仅提取）

创建最小化的 .NET 6.0 console app，唯一职责：从 ROM 提取文本到 JSON。

**1.1 项目搭建**
- `Meowth.sln` 包含 MeowthBridge + HexManiac.Core 项目引用
- 确保 HMA 的 `resources/` 文件被复制到输出目录

**1.2 ROM 加载 (`RomLoader.cs`)**
- `HardcodeTablesModel(singletons, data)` 加载 ROM
- `await model.InitializationWorkload` 等待表发现
- 自动识别游戏代码 (BPRE0 = FireRed)

**1.3 文本提取 (`TextExtractor.cs`)**

提取两类文本，输出格式不同：

**表内文本**（宝可梦名、招式名、道具名等）：
```json
{
  "category": "pokemon_names",
  "table": "data.pokemon.names",
  "entries": [
    {
      "index": 0,
      "address": "0x245EE0",
      "pointer_addresses": ["0x245ED0"],
      "original": "BULBASAUR",
      "max_bytes": 11
    }
  ]
}
```

**自由文本**（对话、NPC、描述等）：
```json
{
  "category": "free_text",
  "entries": [
    {
      "id": "text_0001",
      "address": "0x1A2B3C",
      "pointer_addresses": ["0x1A0010", "0x1B2230"],
      "original": "Hello!\\nI'm Professor OAK!\\pWelcome to the\\nworld of POKéMON!",
      "byte_length": 58
    }
  ]
}
```

关键字段：`pointer_addresses` — 所有指向该文本的指针地址列表。这是注入阶段 repointing 的依据。

**提取的表列表**（来自 HMA wiki 的 Auto Anchors）：
- `data.pokemon.names` — 宝可梦名
- `data.pokemon.moves.names` — 招式名
- `data.abilities.names` — 特性名
- `data.items.stats` (name 字段) — 道具名
- `data.pokemon.type.names` — 属性名
- `data.trainers.classes.names` — 训练师类别
- `data.maps.names` — 地图名
- 所有 `PCSRun` 自由文本

**HMA API:**
- `model.All<PCSRun>()` — 遍历所有自由文本
- `model.GetTable(name)` — 获取命名表
- `model.TextConverter.Convert()` — PCS 字节 → 字符串
- `run.PointerSources` — 获取指向该 run 的所有指针地址

**验证**: 提取 JSON 后与 HMA GUI 对比，确认文本数量和内容一致。

### Phase 2: Python 翻译层

**2.1 术语表 (`glossary.py`)**
- 从 PokeAPI CSV 加载官方中文翻译：
  - `pokemon_species_names.csv` (language_id: 9=en, 12=zh-Hans, 4=zh-Hant)
  - `move_names.csv`, `ability_names.csv`, `item_names.csv`, `type_names.csv`, `nature_names.csv`
- 表内文本直接查表替换，不走 LLM
- 如果简中 (12) 缺失，fallback 到繁中 (4)
- 先验证 PokeAPI 对 Gen 1-3 的中文覆盖率

**2.2 控制码保护 (`control_codes.py`)**
- 翻译前：提取 PCS 控制码 → 编号占位符 `{C0}`, `{C1}`
- 翻译后：还原占位符
- 控制码来源：HMA 的 `pcsReference.txt`
- 包括：`\n`, `\l`, `\p`, `[player]`, `[rival]`, `\v01`-`\vFF` 等

**2.3 字符映射 (`charmap.py`)**
- 解析 `PMRSEFRLG_charmap.txt` → Unicode ↔ 字节编码映射
- 编码规则：
  - 英文/数字/标点：单字节 PCS (0xBB=A, 0xD5=a, 0xA1=0)
  - 中文标点：单字节 (0x37=。, 0x3B=，, 0x3C=！, 0x3D=？)
  - 中文汉字：双字节 (0x0100=啊 ... 0x1E5D=齄)
- 翻译后验证所有字符都在 charmap 范围内
- 不支持的字符 → 报警 + 尝试近义字替换

**2.4 DeepSeek 翻译 (`translator.py`)**
- 仅支持 DeepSeek（先做一个 provider，后续按需加）
- 缓存机制：
  - 请求 hash → `work/cache/{hash}_request.json` + `work/cache/{hash}_response.json`
  - 相同输入直接读缓存，不调 API
- System prompt 包含：
  - 宝可梦翻译风格指南（保持原作语气）
  - 相关术语表（从 glossary 注入）
  - 控制码占位符说明（不要翻译 `{C0}` 等）
  - 字数限制提示
- 按类别分批翻译

**2.5 文本宽度约束 (`charmap.py` 内)**
- 中文字符：11px 宽（Font Patch 11×11 字体）
- 英文/数字：按原 PCS 字宽（约 6-8px）
- 控制码：0px
- GBA 文本框约 240px 宽
- 固定长度字段（如宝可梦名 11 字节 → 最多 5 个中文字）

### Phase 3: ROM 构建 (`rom_writer.py` + `font_patch.py`)

这是整个流程最关键的一步，合并了原 v1 的 Phase 3 和 Phase 4。

**3.1 流程**
```python
def build_rom(original_rom, texts_translated, output_path):
    # 1. 复制原始 ROM
    rom = bytearray(open(original_rom, 'rb').read())

    # 2. 扩展到 32MB
    rom.extend(b'\xFF' * (0x2000000 - len(rom)))

    # 3. 保存临时 ROM，应用 Font Patch
    save(rom, temp_path)
    run_armips(temp_path)  # 注入字库+渲染引擎

    # 4. 重新加载 patched ROM
    rom = bytearray(open(temp_path, 'rb').read())

    # 5. 注入翻译文本
    free_space_ptr = 0x1000000  # 从 16MB 开始（扩展区域）
    for entry in texts_translated:
        encoded = encode_chinese(entry['translated'])  # charmap 编码
        encoded.append(0xFF)  # 终止符

        if len(encoded) <= entry['max_bytes']:
            # 原地写入
            write_bytes(rom, entry['address'], encoded)
        else:
            # 写入扩展区域 + 更新指针
            write_bytes(rom, free_space_ptr, encoded)
            for ptr_addr in entry['pointer_addresses']:
                write_pointer(rom, ptr_addr, free_space_ptr)
            free_space_ptr += len(encoded)
            # 对齐到 4 字节
            free_space_ptr = (free_space_ptr + 3) & ~3

    # 6. 保存
    save(rom, output_path)
```

**3.2 Font Patch 调用 (`font_patch.py`)**
- 将 ROM 复制到 `Pokemon_GBA_Font_Patch/pokeFRLG/baserom_FR.gba`
- 执行 `tools/armips Pokemon_GBA_Font_Patch/pokeFRLG/main_FR.asm`
- 输出在 `Pokemon_GBA_Font_Patch/pokeFRLG/chsfontrom_FR.gba`
- 读回 patched ROM 继续处理

**3.3 指针写入格式**
GBA 指针是 4 字节小端序 + 0x08000000 偏移：
```python
def write_pointer(rom, ptr_addr, target_addr):
    value = target_addr + 0x08000000
    rom[ptr_addr:ptr_addr+4] = value.to_bytes(4, 'little')
```

**3.4 注意事项**
- Font Patch 在 `0x09FD3000+` 注入代码，不会与 `0x1000000` 开始的文本区域冲突
- `free_space_ptr` 需要跳过 Font Patch 已占用的区域
- 表内固定长度文本（如宝可梦名）必须原地写入，不能 repoint

### Phase 4: CLI 整合 + 端到端

**Python CLI (`cli.py`):**
```bash
# 完整流程
meowth translate testgba/firered_en.gba -o outputs/firered_cn_{timestamp}.gba

# 分步执行
meowth extract testgba/firered_en.gba -o work/texts.json
meowth translate-only work/texts.json -o work/texts_translated.json
meowth build testgba/firered_en.gba --translations work/texts_translated.json -o outputs/firered_cn.gba
```

**配置 (`meowth.toml`):**
```toml
[translation]
provider = "deepseek"
model = "deepseek-chat"
source_language = "en"
target_language = "zh-Hans"

[translation.api]
key_env = "DEEPSEEK_API_KEY"  # 从 .env 读取

[font_patch]
armips_path = "tools/armips"
game = "FR"

[output]
dir = "outputs"
cache_dir = "work/cache"
```

## 前置依赖

- .NET 6.0 SDK（编译 MeowthBridge 提取工具）
- Python 3.10+
- armips（已有 `tools/armips`）

## 验证方式

1. **Phase 1**: MeowthBridge extract → JSON，与 HMA GUI 对比文本数量
2. **Phase 2**: 翻译 JSON，检查控制码保留、术语正确、字符在 charmap 内
3. **Phase 3**: 构建 ROM，在 mGBA 中运行，检查中文显示正常
4. **端到端**: 一条命令 `meowth translate` 完成全流程

## 与 v1 的主要区别

| 方面 | v1 | v2 |
|------|----|----|
| C# 职责 | 提取 + 注入 | 仅提取 |
| 注入方式 | C# 操作 HMA RawData | Python 直接操作字节 |
| ROM 大小 | 未明确 | 扩展到 32MB |
| Repointing | "找空闲空间"（模糊） | 明确：扩展区域 0x1000000+ |
| 文本注入顺序 | 先注入再 Font Patch（错误） | 先 Font Patch 再注入（正确） |
| LLM Provider | 多 provider | 先只做 DeepSeek |
| API 缓存 | 未设计 | 请求 hash → 本地缓存 |
| 敏感信息 | 明文在 plan.md | .env + .gitignore |
