using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Encodings.Web;
using HavenSoft.HexManiac.Core.Models;
using HavenSoft.HexManiac.Core.Models.Runs;
using HavenSoft.HexManiac.Core.Models.Code;

namespace MeowthBridge;

public class TextExtractor
{
    private readonly IDataModel _model;

    public TextExtractor(IDataModel model)
    {
        _model = model;
    }

    public List<TextEntry> ExtractAll()
    {
        var entries = new List<TextEntry>();
        var extractedAddresses = new HashSet<int>();
        int id = 0;

        // Phase 1: 提取表格文本（100% 准确，HMA 已识别表格结构）
        Console.Error.WriteLine("Phase 1: 提取表格文本...");
        ExtractTableTexts(entries, extractedAddresses, ref id);
        Console.Error.WriteLine($"  表格文本: {entries.Count} 条");

        // Phase 2: 扫描 loadpointer 指令，构建安全的指针源映射
        Console.Error.WriteLine("Phase 2: 扫描 loadpointer 指令...");
        var loadpointerMap = ScanLoadpointerSources();
        Console.Error.WriteLine($"  发现 {loadpointerMap.Count} 个文本地址的 loadpointer 引用");

        // Phase 3: 提取 loadpointer 引用的文本（脚本明确引用，非常安全）
        Console.Error.WriteLine("Phase 3: 提取 loadpointer 文本...");
        int beforeLp = entries.Count;
        ExtractLoadpointerTexts(entries, extractedAddresses, ref id, loadpointerMap);
        Console.Error.WriteLine($"  loadpointer 文本: {entries.Count - beforeLp} 条");

        // Phase 4: 扫描所有指针（包括 ARM 代码中的引用）
        Console.Error.WriteLine("Phase 4: 扫描所有指针...");
        var allPointerMap = ScanAllPointers();
        Console.Error.WriteLine($"  发现 {allPointerMap.Count} 个文本地址的指针引用");

        // Phase 5: 提取所有指针引用的文本
        Console.Error.WriteLine("Phase 5: 提取指针文本...");
        int beforePtr = entries.Count;
        ExtractAllPointerTexts(entries, extractedAddresses, ref id, allPointerMap);
        Console.Error.WriteLine($"  指针文本: {entries.Count - beforePtr} 条");

        return entries;
    }

    private void ExtractTableTexts(List<TextEntry> entries, HashSet<int> extractedAddresses, ref int id)
    {
        var tableNames = new Dictionary<string, (string category, int? knownCount)>
        {
            // 基础数据表
            ["data.pokemon.names"] = ("pokemon_names", null),
            ["data.pokemon.type.names"] = ("type_names", 18),
            ["data.items.stats"] = ("item_names", 375),
            ["data.pokemon.moves.names"] = ("move_names", null),
            ["data.abilities.names"] = ("ability_names", null),
            ["data.pokemon.natures.names"] = ("nature_names", null),
            ["data.trainers.classes.names"] = ("trainer_classes", null),

            // 描述文本
            ["data.abilities.descriptions"] = ("ability_descriptions", null),
            ["data.pokemon.moves.descriptions"] = ("move_descriptions", null),

            // 地图和栖息地
            ["data.maps.names"] = ("map_names", null),
            ["data.maps.banks"] = ("map_banks", null),
            ["data.pokedex.habitat.names"] = ("habitat_names", null),

            // 战斗和菜单文本
            ["data.battle.text"] = ("battle_text", null),
            ["data.menus.text.options"] = ("menu_options", null),
            ["data.menus.text.pc"] = ("menu_pc", null),
            ["data.menus.text.pcoptions"] = ("menu_pcoptions", null),
            ["data.menus.text.pokemon"] = ("menu_pokemon", null),
            ["data.text.menu.itemStorage"] = ("menu_item_storage", null),
            ["data.text.menu.pause"] = ("menu_pause", null),
            ["data.text.menu.pokemon.options"] = ("menu_pokemon_options", null),
            ["data.text.trade.messages"] = ("trade_messages", null),
        };

        foreach (var (tableName, (category, knownCount)) in tableNames)
        {
            var address = _model.GetAddressFromAnchor(new NoDataChangeDeltaModel(), -1, tableName);
            if (address < 0) continue;

            var run = _model.GetNextRun(address);
            if (run is not ITableRun tableRun) continue;

            var elementCount = knownCount ?? tableRun.ElementCount;
            if (elementCount <= 1 && knownCount == null) continue;

            for (int i = 0; i < elementCount; i++)
            {
                var (text, textAddress, textLength) = ExtractTableElementText(tableRun, i);
                if (string.IsNullOrEmpty(text)) continue;

                extractedAddresses.Add(textAddress);

                entries.Add(new TextEntry
                {
                    Id = $"tbl_{category}_{id++:D5}",
                    Category = category,
                    Address = $"0x{textAddress:X}",
                    Original = text,
                    ByteLength = textLength,  // 使用实际文本长度
                    IsPointerBased = false,
                    TableName = tableName,
                    TableIndex = i
                });
            }
        }
    }

    private (string? text, int address, int length) ExtractTableElementText(ITableRun tableRun, int index)
    {
        var elementStart = tableRun.Start + index * tableRun.ElementLength;
        int segmentOffset = 0;

        foreach (var segment in tableRun.ElementContent)
        {
            if (segment.Type == ElementContentType.PCS)
            {
                var text = _model.TextConverter.Convert(_model, elementStart + segmentOffset, segment.Length);
                return (text, elementStart + segmentOffset, segment.Length);
            }
            if (segment.Type == ElementContentType.Pointer)
            {
                var pointer = _model.ReadPointer(elementStart + segmentOffset);
                if (pointer >= 0 && pointer < _model.Count)
                {
                    var run = _model.GetNextRun(pointer);
                    if (run is PCSRun pcsRun && run.Start == pointer)
                    {
                        var text = _model.TextConverter.Convert(_model, pcsRun.Start, pcsRun.Length);
                        return (text, pcsRun.Start, pcsRun.Length);
                    }
                }
            }
            segmentOffset += segment.Length;
        }
        return (null, 0, 0);
    }

    /// <summary>
    /// 扫描 loadpointer (0x0F) 指令，构建 文本地址 → 指针源地址集合 的映射。
    /// 这是唯一安全的指针源发现方式：只信任脚本中明确的 loadpointer 指令，
    /// 不依赖 HMA 的 SearchForPointers（全 ROM 4 字节对齐扫描，会误判跳转表）。
    /// </summary>
    private Dictionary<int, HashSet<int>> ScanLoadpointerSources()
    {
        var map = new Dictionary<int, HashSet<int>>();

        for (int i = 0x0A0000; i < _model.Count - 6; i++)
        {
            if (_model[i] != 0x0F) continue; // loadpointer opcode

            // GBA Pokémon script engine only has 4 banks (0-3).
            // Any other value means this 0x0F byte is data, not a loadpointer.
            byte bank = _model[i + 1];
            if (bank > 3) continue;

            int ptrOffset = i + 2;
            if (ptrOffset + 4 > _model.Count) continue;

            var pointer = _model.ReadPointer(ptrOffset);
            if (pointer < 0 || pointer >= _model.Count) continue;

            var textLength = ValidatePcsText(pointer);
            if (textLength < 2) continue;

            if (!map.ContainsKey(pointer))
                map[pointer] = new HashSet<int>();
            map[pointer].Add(ptrOffset);

            i += 5; // opcode(1) + bank(1) + pointer(4) - 1 (loop will i++)
        }

        return map;
    }

    /// <summary>
    /// Phase 3: 提取 loadpointer 引用的文本
    /// 只提取脚本中明确通过 loadpointer (0x0F) 指令引用的文本
    /// </summary>
    private void ExtractLoadpointerTexts(
        List<TextEntry> entries, HashSet<int> extractedAddresses, ref int id,
        Dictionary<int, HashSet<int>> loadpointerMap)
    {
        int found = 0;

        foreach (var (textAddr, ptrSources) in loadpointerMap)
        {
            if (extractedAddresses.Contains(textAddr)) continue;

            var textLength = ValidatePcsText(textAddr);
            if (textLength < 2) continue;

            var text = _model.TextConverter.Convert(_model, textAddr, textLength);
            if (string.IsNullOrEmpty(text) || text == "\"\"") continue;

            var cleanText = text.Trim('"');
            if (cleanText.Length < 1) continue;

            extractedAddresses.Add(textAddr);

            entries.Add(new TextEntry
            {
                Id = $"scr_{id++:D5}",
                Category = "scripts",
                Address = $"0x{textAddr:X}",
                PointerSources = ptrSources.Select(p => $"0x{p:X}").ToList(),
                Original = text,
                ByteLength = textLength,
                IsPointerBased = true
            });
            found++;
        }
    }

    /// <summary>
    /// Phase 4: 扫描所有 4 字节对齐的指针，构建文本地址映射
    /// 这会找到 ARM 代码中的文本引用（如数据池中的指针）
    /// </summary>
    private Dictionary<int, HashSet<int>> ScanAllPointers()
    {
        var map = new Dictionary<int, HashSet<int>>();
        
        // 扫描所有 4 字节对齐的位置
        for (int i = 0; i < _model.Count - 3; i += 4)
        {
            // 指针必须以 0x08 或 0x09 结尾（GBA 地址空间）
            if (_model[i + 3] != 0x08 && _model[i + 3] != 0x09) continue;
            
            var pointer = _model.ReadPointer(i);
            
            // 指针必须指向 ROM 内
            if (pointer < 0 || pointer >= _model.Count) continue;
            
            // 跳过指向头部的指针
            if (pointer < 0x0A0000) continue;
            
            // 使用严格验证（Phase 5 专用）
            var textLength = ValidatePcsTextStrict(pointer);
            if (textLength < 2) continue;
            
            if (!map.ContainsKey(pointer))
                map[pointer] = new HashSet<int>();
            map[pointer].Add(i);
        }
        
        return map;
    }

    /// <summary>
    /// Phase 5: 提取所有指针引用的文本
    /// </summary>
    private void ExtractAllPointerTexts(
        List<TextEntry> entries, HashSet<int> extractedAddresses, ref int id,
        Dictionary<int, HashSet<int>> allPointerMap)
    {
        int found = 0;
        int rejected = 0;

        foreach (var (textAddr, ptrSources) in allPointerMap)
        {
            if (extractedAddresses.Contains(textAddr)) continue;

            // 第一关：严格的字节级验证
            var textLength = ValidatePcsTextStrict(textAddr);
            if (textLength < 2)
            {
                rejected++;
                continue;
            }

            // 第二关：转换文本
            var text = _model.TextConverter.Convert(_model, textAddr, textLength);
            if (string.IsNullOrEmpty(text) || text == "\"\"")
            {
                rejected++;
                continue;
            }

            // 第三关：宽松的文本检查（因为有指针指向，说明是有效的）
            // 只检查是否包含足够的字母（至少3个）
            int letters = 0;
            foreach (char c in text)
            {
                if (char.IsLetter(c)) letters++;
            }

            if (letters < 3)
            {
                rejected++;
                continue;
            }

            // 通过所有检查，提取文本
            extractedAddresses.Add(textAddr);

            entries.Add(new TextEntry
            {
                Id = $"ptr_{id++:D5}",
                Category = "pointers",
                Address = $"0x{textAddr:X}",
                PointerSources = ptrSources.Select(p => $"0x{p:X}").ToList(),
                Original = text,
                ByteLength = textLength,
                IsPointerBased = true
            });
            found++;
        }

        Console.Error.WriteLine($"  (拒绝了 {rejected} 条低质量文本)");
    }

    /// <summary>
    /// 验证地址处是否为有效 PCS 文本，返回长度（含 0xFF 终止符），无效返回 0
    /// 覆盖完整 Gen3 PCS 字符集：
    ///   0x00=空格, 0x01-0x50=扩展字符, 0x51-0xA0=扩展字符,
    ///   0xA1-0xAA=数字, 0xAB-0xBA=标点, 0xBB-0xD4=A-Z, 0xD5-0xEE=a-z,
    ///   0xEF=♂, 0xF0=♀, 0xF1-0xF9=特殊字符/控制码,
    ///   0xFA=换行, 0xFB=换段, 0xFC/0xFD=带参控制码, 0xFE=换行
    /// 同时通过字母比例（≥20%）过滤碰巧命中 0xFF 的二进制数据
    /// </summary>
    private int ValidatePcsText(int address)
    {
        if (address < 0 || address >= _model.Count) return 0;

        const int MAX_LENGTH = 2000;
        int letters = 0;
        int totalPrintable = 0;

        for (int i = 0; i < MAX_LENGTH && address + i < _model.Count; i++)
        {
            byte b = _model[address + i];

            if (b == 0xFF) // 终止符
            {
                if (letters < 2) return 0;
                // 字母比例检查：过滤伪装成文本的二进制数据
                if (totalPrintable > 0 && (double)letters / totalPrintable < 0.20) return 0;
                return i + 1;
            }

            // A-Z, a-z, é — 计入字母
            if ((b >= 0xBB && b <= 0xD4) || (b >= 0xD5 && b <= 0xEE) || b == 0x1B)
            {
                letters++;
                totalPrintable++;
                continue;
            }

            // 空格、数字、标点（含冒号 0xBA）
            if (b == 0x00 || (b >= 0xA1 && b <= 0xBA))
            {
                totalPrintable++;
                continue;
            }

            // 换行/换段控制码
            if (b == 0xFA || b == 0xFB || b == 0xFE)
            {
                totalPrintable++;
                continue;
            }

            // 带参数的控制码 FC/FD — 跳过参数字节
            if (b == 0xFC && address + i + 1 < _model.Count)
            {
                i++;
                continue;
            }
            if (b == 0xFD && address + i + 1 < _model.Count)
            {
                i++;
                continue;
            }

            // 扩展 PCS 字符：0x01-0x50（重音字母等）、0x51-0xA0、0xEF-0xF9（♂♀及特殊符号）
            if ((b >= 0x01 && b <= 0x50) || (b >= 0x51 && b <= 0xA0) || (b >= 0xEF && b <= 0xF9))
            {
                totalPrintable++;
                continue;
            }

            // 不在任何合法 PCS 范围内 — 不是文本
            return 0;
        }

        return 0; // 没找到终止符
    }

    /// <summary>
    /// 严格验证 PCS 文本（用于 Phase 5 全指针扫描）
    /// 比 ValidatePcsText 更保守，减少误判
    /// </summary>
    /// <summary>
    /// 超严格验证 PCS 文本（Phase 5 专用）
    /// 目标：100% 准确率，宁可漏掉也不能错
    /// </summary>
    private int ValidatePcsTextStrict(int address)
    {
        if (address < 0 || address >= _model.Count) return 0;

        const int MAX_LENGTH = 2000;
        int letters = 0;
        int totalPrintable = 0;
        int spaces = 0;
        int words = 0;
        int sentences = 0;
        bool inWord = false;
        bool hasUpperCase = false;
        bool hasLowerCase = false;

        for (int i = 0; i < MAX_LENGTH && address + i < _model.Count; i++)
        {
            byte b = _model[address + i];

            if (b == 0xFF) // 终止符
            {
                // 超严格要求：
                
                // 1. 最少 15 个字母（排除所有短标签和片段）
                if (letters < 15) return 0;
                
                // 2. 至少 3 个单词（确保是完整句子或短语）
                if (words < 3) return 0;
                
                // 3. 至少 2 个空格（确保有单词分隔）
                if (spaces < 2) return 0;
                
                // 4. 字母比例至少 40%（严格过滤二进制数据）
                if (totalPrintable > 0 && (double)letters / totalPrintable < 0.40) return 0;
                
                // 5. 总长度至少 20 字节（排除短文本）
                if (i < 20) return 0;
                
                // 6. 必须同时有大写和小写字母（排除全大写标签如 "SOMEONE'S PC"）
                if (!hasUpperCase || !hasLowerCase) return 0;
                
                // 7. 单词平均长度检查（排除乱码）
                double avgWordLength = (double)letters / words;
                if (avgWordLength < 2.0 || avgWordLength > 15.0) return 0;
                
                return i + 1;
            }

            // A-Z 大写字母
            if (b >= 0xBB && b <= 0xD4)
            {
                letters++;
                totalPrintable++;
                hasUpperCase = true;
                if (!inWord)
                {
                    words++;
                    inWord = true;
                }
                continue;
            }

            // a-z 小写字母
            if (b >= 0xD5 && b <= 0xEE)
            {
                letters++;
                totalPrintable++;
                hasLowerCase = true;
                if (!inWord)
                {
                    words++;
                    inWord = true;
                }
                continue;
            }

            // é 特殊字母
            if (b == 0x1B)
            {
                letters++;
                totalPrintable++;
                if (!inWord)
                {
                    words++;
                    inWord = true;
                }
                continue;
            }

            // 空格 — 单词分隔符
            if (b == 0x00)
            {
                spaces++;
                totalPrintable++;
                inWord = false;
                continue;
            }

            // 句号、问号、感叹号（句子结束标记）
            if (b == 0xAD || b == 0xAC || b == 0xAB)
            {
                sentences++;
                totalPrintable++;
                inWord = false;
                continue;
            }

            // 其他标点和数字
            if (b >= 0xA1 && b <= 0xBA)
            {
                totalPrintable++;
                continue;
            }

            // 换行/换段控制码
            if (b == 0xFA || b == 0xFB || b == 0xFE)
            {
                totalPrintable++;
                inWord = false;
                continue;
            }

            // 带参数的控制码
            if (b == 0xFC && address + i + 1 < _model.Count)
            {
                i++;
                continue;
            }
            if (b == 0xFD && address + i + 1 < _model.Count)
            {
                i++;
                continue;
            }

            // 扩展字符（更保守：只接受常见范围）
            if ((b >= 0x01 && b <= 0x50) || (b >= 0xEF && b <= 0xF9))
            {
                totalPrintable++;
                continue;
            }

            // 不合法字节 — 直接拒绝
            return 0;
        }

        return 0;
    }

    /// <summary>
    /// 黑名单：已知的系统标签、模板字符串、内部标识符
    /// 这些不应该被翻译
    /// </summary>
    private static readonly HashSet<string> TEXT_BLACKLIST = new()
    {
        // 系统标签
        "SOMEONE'S PC",
        "PLAYER'S PC",
        "BILL'S PC",
        
        // 短标签
        "PP",
        "HP",
        "Lv.",
        "No.",
        "HT",
        "WT",
        
        // 单个单词（太短，可能是标签）
        "RED",
        "GREEN",
        "BLUE",
        "RUBY",
        "SAPPHIRE",
        "EMERALD",
        "GOLD",
        "SILVER",
        
        // 其他已知的内部字符串
        "SMALL DESK",
        "BIG DESK",
    };

    /// <summary>
    /// 检查文本是否包含模板变量或特殊占位符
    /// 这些通常是游戏内部使用的模板字符串
    /// </summary>
    private bool ContainsTemplateVariables(string text)
    {
        // 检查反斜杠占位符：\00, \05, \1F, \20 等
        if (System.Text.RegularExpressions.Regex.IsMatch(text, @"\\[0-9A-F]{2}"))
            return true;
        
        // 检查 [buffer] 占位符
        if (text.Contains("[buffer"))
            return true;
        
        // 检查连续的控制字符
        int controlCharCount = 0;
        foreach (char c in text)
        {
            if (c == '\\' || c == '!' || c == '\x01' || c == '\x02')
            {
                controlCharCount++;
                if (controlCharCount > 5) return true;
            }
            else
            {
                controlCharCount = 0;
            }
        }
        
        return false;
    }

    /// <summary>
    /// 检查文本质量（超严格）
    /// </summary>
    private bool IsHighQualityText(string text)
    {
        if (string.IsNullOrEmpty(text)) return false;

        var cleanText = text.Trim('"').Trim();

        // 1. 检查黑名单
        if (TEXT_BLACKLIST.Contains(cleanText)) return false;

        // 2. 允许模板变量（[player]、\qo、\qc 等）- 注释掉严格检查
        // if (ContainsTemplateVariables(cleanText)) return false;

        // 3. 检查长度（至少 8 字符，允许短文本如 "This is what we call a POKéMON."）
        if (cleanText.Length < 8) return false;

        // 4. 检查是否有完整的句子结构或包含变量
        // 移除控制码和变量后再检查句子结构
        var textForSentenceCheck = System.Text.RegularExpressions.Regex.Replace(cleanText, @"\\[a-z]", " ");
        textForSentenceCheck = System.Text.RegularExpressions.Regex.Replace(textForSentenceCheck, @"\[.*?\]", " ");
        textForSentenceCheck = System.Text.RegularExpressions.Regex.Replace(textForSentenceCheck, @"\\[0-9A-F]{2}", " ");
        var sentences = System.Text.RegularExpressions.Regex.Matches(textForSentenceCheck, @"[A-Z][^.!?\n]*[.!?]");
        // 允许没有句号的文本，只要有足够的字母即可
        if (sentences.Count == 0 && cleanText.Length < 15) return false;
        
        // 5. 检查字母比例
        int letters = 0;
        int total = 0;
        foreach (char c in cleanText)
        {
            if (char.IsLetter(c)) letters++;
            if (c != '\n' && c != '\r' && c != '\\') total++;
        }
        
        if (total > 0 && (double)letters / total < 0.40) return false;
        
        // 6. 检查是否有常见的对话/描述词汇（提高置信度）
        // 扩展常见词列表，包含更多英语常用词
        var commonWords = new[] { 
            "the", "a", "an", "and", "or", "but", "if", "for", "to", "of", "in", "on", "at", "by", "with",
            "you", "your", "i", "my", "we", "our", "he", "she", "it", "they", "them", "their",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "can", "could", "should", "may", "might", "must",
            "this", "that", "these", "those", "some", "any", "all", "no", "not",
            "as", "from", "into", "about", "after", "before", "when", "where", "who", "what", "which", "how"
        };
        
        var lowerText = cleanText.ToLower();
        int commonWordCount = 0;
        
        foreach (var word in commonWords)
        {
            // 检查单词是否作为独立单词出现（前后有空格、标点或开头/结尾）
            if (System.Text.RegularExpressions.Regex.IsMatch(lowerText, @"\b" + word + @"\b"))
            {
                commonWordCount++;
                break; // 找到 1 个就够了
            }
        }
        
        // 至少包含 1 个常见词
        if (commonWordCount < 1) return false;
        
        return true;
    }

    public string ToJson(List<TextEntry> entries)
    {
        var output = new OutputData { Entries = entries };
        return JsonSerializer.Serialize(output, new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
        });
    }
}

public class OutputData
{
    [JsonPropertyName("entries")]
    public List<TextEntry> Entries { get; set; } = new();
}

public class TextEntry
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("category")]
    public string Category { get; set; } = "";

    [JsonPropertyName("address")]
    public string Address { get; set; } = "";

    [JsonPropertyName("pointer_sources")]
    public List<string> PointerSources { get; set; } = new();

    [JsonPropertyName("original")]
    public string Original { get; set; } = "";

    [JsonPropertyName("byte_length")]
    public int ByteLength { get; set; }

    [JsonPropertyName("is_pointer_based")]
    public bool IsPointerBased { get; set; }

    [JsonPropertyName("table_name")]
    public string? TableName { get; set; }

    [JsonPropertyName("table_index")]
    public int? TableIndex { get; set; }

    [JsonPropertyName("translated")]
    public string? Translated { get; set; }
}


