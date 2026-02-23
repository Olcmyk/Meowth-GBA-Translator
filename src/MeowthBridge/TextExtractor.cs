using System.Text.Json;
using System.Text.Json.Serialization;
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

        // Phase 1: 从表格提取（100% 准确）
        Console.Error.WriteLine("Phase 1: 提取表格文本...");
        ExtractTableTexts(entries, extractedAddresses, ref id);
        Console.Error.WriteLine($"  表格文本: {entries.Count} 条");

        // Phase 2: 扫描 loadpointer 指令，构建安全的指针源映射
        // 只信任脚本中明确的 loadpointer (0x0F) 指令作为指针源
        // 不使用 HMA 的 SearchForPointers（全 ROM 扫描会误判跳转表等为指针）
        Console.Error.WriteLine("Phase 2: 扫描 loadpointer 指令...");
        var loadpointerMap = ScanLoadpointerSources();
        Console.Error.WriteLine($"  发现 {loadpointerMap.Count} 个文本地址的 loadpointer 引用");

        // Phase 3: 提取 HMA 识别的文本，仅使用 loadpointer 验证的指针源
        Console.Error.WriteLine("Phase 3: 提取 HMA 识别的文本...");
        int beforeHma = entries.Count;
        ExtractHmaTextsWithSafePointers(entries, extractedAddresses, ref id, loadpointerMap);
        Console.Error.WriteLine($"  HMA 文本: {entries.Count - beforeHma} 条");

        // Phase 4: 补充 loadpointer 发现但 HMA 未识别的文本
        Console.Error.WriteLine("Phase 4: 补充 loadpointer 文本...");
        int beforeLp = entries.Count;
        ExtractRemainingLoadpointerTexts(entries, extractedAddresses, ref id, loadpointerMap);
        Console.Error.WriteLine($"  loadpointer 补充: {entries.Count - beforeLp} 条");

        return entries;
    }

    private void ExtractTableTexts(List<TextEntry> entries, HashSet<int> extractedAddresses, ref int id)
    {
        var tableNames = new Dictionary<string, (string category, int? knownCount)>
        {
            ["data.pokemon.names"] = ("pokemon_names", null),
            ["data.pokemon.type.names"] = ("type_names", 18),
            ["data.items.stats"] = ("item_names", 375),
            ["data.pokemon.moves.names"] = ("move_names", null),
            ["data.abilities.names"] = ("ability_names", null),
            ["data.pokemon.natures.names"] = ("nature_names", null),
            ["data.trainers.classes.names"] = ("trainer_classes", null),
            ["data.maps.banks"] = ("map_names", null),
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
                var (text, textAddress) = ExtractTableElementText(tableRun, i);
                if (string.IsNullOrEmpty(text)) continue;

                extractedAddresses.Add(textAddress);

                entries.Add(new TextEntry
                {
                    Id = $"tbl_{category}_{id++:D5}",
                    Category = category,
                    Address = $"0x{textAddress:X}",
                    Original = text,
                    ByteLength = tableRun.ElementLength,
                    IsPointerBased = false,
                    TableName = tableName,
                    TableIndex = i
                });
            }
        }
    }

    private (string? text, int address) ExtractTableElementText(ITableRun tableRun, int index)
    {
        var elementStart = tableRun.Start + index * tableRun.ElementLength;
        int segmentOffset = 0;

        foreach (var segment in tableRun.ElementContent)
        {
            if (segment.Type == ElementContentType.PCS)
            {
                var text = _model.TextConverter.Convert(_model, elementStart + segmentOffset, segment.Length);
                return (text, elementStart + segmentOffset);
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
                        return (text, pcsRun.Start);
                    }
                }
            }
            segmentOffset += segment.Length;
        }
        return (null, 0);
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
    /// Phase 3: 提取 HMA 识别的 PCSRun 文本。
    /// 指针源仅使用 loadpointer 扫描结果，不使用 HMA 的 PointerSources。
    /// HMA 的 PointerSources 来自全 ROM 扫描，会误判数据结构中的指针，
    /// 修改后导致游戏崩溃（背包跳转表、地图事件表等）。
    /// </summary>
    // ARM 代码段结束地址 — 此地址之前的 PCSRun 是误判（机器码碰巧像文本）
    private const int MIN_TEXT_ADDRESS = 0x0A0000;

    private void ExtractHmaTextsWithSafePointers(
        List<TextEntry> entries, HashSet<int> extractedAddresses, ref int id,
        Dictionary<int, HashSet<int>> loadpointerMap)
    {
        int withPtrs = 0, inPlaceOnly = 0, noRefs = 0, tooShort = 0, armSkipped = 0;

        foreach (var run in _model.All<PCSRun>())
        {
            if (extractedAddresses.Contains(run.Start)) continue;

            // 跳过 ARM 代码段中的伪文本 — 机器码字节碰巧通过 PCS 验证
            if (run.Start < MIN_TEXT_ADDRESS)
            {
                armSkipped++;
                continue;
            }

            var hmaPointers = run.PointerSources?.ToList() ?? new List<int>();
            bool hasLoadpointer = loadpointerMap.ContainsKey(run.Start);

            if (hmaPointers.Count == 0 && !hasLoadpointer)
            {
                noRefs++;
                continue;
            }

            var text = _model.TextConverter.Convert(_model, run.Start, run.Length);
            if (string.IsNullOrEmpty(text) || text == "\"\"") continue;

            var cleanText = text.Trim('"');
            if (cleanText.Length < 1)
            {
                tooShort++;
                continue;
            }
            extractedAddresses.Add(run.Start);

            // 仅使用 loadpointer 验证的指针源
            var safePointers = hasLoadpointer
                ? loadpointerMap[run.Start].Select(p => $"0x{p:X}").ToList()
                : new List<string>();

            if (hasLoadpointer) withPtrs++;
            else inPlaceOnly++;

            entries.Add(new TextEntry
            {
                Id = $"scr_{id++:D5}",
                Category = "scripts",
                Address = $"0x{run.Start:X}",
                PointerSources = safePointers,
                Original = text,
                ByteLength = run.Length,
                IsPointerBased = hasLoadpointer
            });
        }

        Console.Error.WriteLine(
            $"  有loadpointer指针: {withPtrs}, 仅就地写入: {inPlaceOnly}, " +
            $"无引用跳过: {noRefs}, 太短跳过: {tooShort}, ARM代码跳过: {armSkipped}");
    }

    /// <summary>
    /// Phase 4: 补充 loadpointer 发现但 HMA 未识别的文本
    /// 这些文本没有对应的 PCSRun（HMA 未识别），但有明确的 loadpointer 引用
    /// </summary>
    private void ExtractRemainingLoadpointerTexts(
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

            // 仅使用 loadpointer 发现的安全指针源，不合并 HMA 的 PointerSources
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

        Console.Error.WriteLine($"  loadpointer 补充: {found} 条");
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

    public string ToJson(List<TextEntry> entries)
    {
        var output = new OutputData { Entries = entries };
        return JsonSerializer.Serialize(output, new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
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
}


