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

        // Phase 2: 完全信任 HMA 的 PCSRun —— 精确提取所有文本
        // HMA 在模型初始化时已经通过指针分析验证了每个 PCSRun
        // 不再需要暴力扫描（那是导致游戏崩溃的根源）
        Console.Error.WriteLine("Phase 2: 提取 HMA 识别的所有文本...");
        int beforeScript = entries.Count;
        ExtractHmaTexts(entries, extractedAddresses, ref id);
        Console.Error.WriteLine($"  HMA 文本: {entries.Count - beforeScript} 条");

        // Phase 3: 扫描 loadpointer 指令中的文本指针
        // HMA 的 SearchForPointers 只扫描 4 字节对齐的指针
        // 但 XSE 脚本的 loadpointer (0x0F) 指令中的指针不一定对齐
        // 直接扫描整个脚本数据区找 loadpointer 操作码
        Console.Error.WriteLine("Phase 3: 扫描 loadpointer 指令...");
        int beforeLp = entries.Count;
        ExtractLoadpointerTexts(entries, extractedAddresses, ref id);
        Console.Error.WriteLine($"  loadpointer 文本: {entries.Count - beforeLp} 条");

        return entries;
    }

    private void ExtractTableTexts(List<TextEntry> entries, HashSet<int> extractedAddresses, ref int id)
    {
        var tableNames = new Dictionary<string, (string category, int? knownCount)>
        {
            ["data.pokemon.names"] = ("pokemon_names", null),
            ["data.pokemon.type.names"] = ("type_names", 18),
            ["data.items.stats"] = ("item_names", 375),
            ["data.moves.names"] = ("move_names", null),
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
    /// Phase 2: 完全信任 HMA 的 PCSRun 识别结果
    /// HMA 在模型初始化时通过 SearchForPointers + WriteStringRuns 精确识别了所有文本
    /// 每个 PCSRun 都有可靠的 PointerSources（包括代码区的 literal pool 条目）
    /// </summary>
    private void ExtractHmaTexts(List<TextEntry> entries, HashSet<int> extractedAddresses, ref int id)
    {
        int withPointers = 0, noPointers = 0, tooShort = 0;

        foreach (var run in _model.All<PCSRun>())
        {
            if (extractedAddresses.Contains(run.Start)) continue;

            var pointerSources = run.PointerSources?.ToList() ?? new List<int>();
            if (pointerSources.Count == 0)
            {
                noPointers++;
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
            withPointers++;

            entries.Add(new TextEntry
            {
                Id = $"scr_{id++:D5}",
                Category = "scripts",
                Address = $"0x{run.Start:X}",
                PointerSources = pointerSources.Select(p => $"0x{p:X}").ToList(),
                Original = text,
                ByteLength = run.Length,
                IsPointerBased = true
            });
        }

        Console.Error.WriteLine($"  有指针: {withPointers}, 无指针跳过: {noPointers}, 太短跳过: {tooShort}");
    }

    /// <summary>
    /// Phase 3: 扫描 loadpointer (0x0F) 指令提取 HMA 遗漏的文本
    /// loadpointer 格式: 0F <bank> <4字节指针>
    /// 指针在 opcode+2 处，不一定 4 字节对齐，所以 HMA 的对齐扫描会漏掉
    /// 这是安全的：只收集明确的脚本指令中的指针，不会碰到代码区 literal pool
    /// </summary>
    private void ExtractLoadpointerTexts(List<TextEntry> entries, HashSet<int> extractedAddresses, ref int id)
    {
        int found = 0;
        // 文本地址 -> 所有指向它的 loadpointer 指针源
        var textToPointers = new Dictionary<int, HashSet<int>>();

        // 扫描脚本数据区
        // FRLG ARM 代码区约 0x000000-0x0A0000，之后是数据和脚本
        // loadpointer 主要集中在 0x0C0000-0x1C0000 区域
        for (int i = 0x0A0000; i < _model.Count - 6; i++)
        {
            if (_model[i] != 0x0F) continue; // loadpointer opcode

            // 读取指针（在 opcode+2 处）
            int ptrOffset = i + 2;
            if (ptrOffset + 4 > _model.Count) continue;

            var pointer = _model.ReadPointer(ptrOffset);
            if (pointer < 0 || pointer >= _model.Count) continue;

            // 验证目标是有效 PCS 文本
            var textLength = ValidatePcsText(pointer);
            if (textLength < 2) continue;

            if (!textToPointers.ContainsKey(pointer))
                textToPointers[pointer] = new HashSet<int>();
            textToPointers[pointer].Add(ptrOffset);

            // 跳过已处理的指针字节
            i += 5; // opcode(1) + bank(1) + pointer(4) - 1 (loop will i++)
        }

        // 为每个新发现的文本创建条目
        foreach (var (textAddr, ptrSources) in textToPointers)
        {
            if (extractedAddresses.Contains(textAddr)) continue;

            var textLength = ValidatePcsText(textAddr);
            if (textLength < 2) continue;

            var text = _model.TextConverter.Convert(_model, textAddr, textLength);
            if (string.IsNullOrEmpty(text) || text == "\"\"") continue;

            var cleanText = text.Trim('"');
            if (cleanText.Length < 1) continue;

            extractedAddresses.Add(textAddr);

            // 合并 HMA 已知的指针源
            var allPointers = new HashSet<int>(ptrSources);
            var run = _model.GetNextRun(textAddr);
            if (run is PCSRun pcsRun && run.Start == textAddr && pcsRun.PointerSources != null)
            {
                foreach (var ps in pcsRun.PointerSources)
                    allPointers.Add(ps);
            }

            entries.Add(new TextEntry
            {
                Id = $"scr_{id++:D5}",
                Category = "scripts",
                Address = $"0x{textAddr:X}",
                PointerSources = allPointers.Select(p => $"0x{p:X}").ToList(),
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
    /// </summary>
    private int ValidatePcsText(int address)
    {
        if (address < 0 || address >= _model.Count) return 0;

        const int MAX_LENGTH = 2000;
        int letters = 0;

        for (int i = 0; i < MAX_LENGTH && address + i < _model.Count; i++)
        {
            byte b = _model[address + i];

            if (b == 0xFF) // 终止符
            {
                // 至少要有一些字母才算有效文本
                if (letters < 2) return 0;
                return i + 1;
            }

            // 有效 PCS 字符
            if (b == 0x00 || b == 0x1B ||                          // 空格, é
                (b >= 0xA1 && b <= 0xAA) ||                        // 数字
                (b >= 0xAB && b <= 0xB9) ||                        // 标点
                (b >= 0xBB && b <= 0xD4) ||                        // A-Z
                (b >= 0xD5 && b <= 0xEE) ||                        // a-z
                b == 0xFA || b == 0xFB || b == 0xFE)               // 换行控制码
            {
                if ((b >= 0xBB && b <= 0xD4) || (b >= 0xD5 && b <= 0xEE) || b == 0x1B)
                    letters++;
                continue;
            }

            // 控制码 FC/FD - 跳过参数
            if (b == 0xFC && address + i + 1 < _model.Count)
            {
                i++; // 跳过至少一个参数字节
                // FC 控制码可能有更多参数，但简单跳过一个足够做验证
                continue;
            }
            if (b == 0xFD && address + i + 1 < _model.Count)
            {
                i++;
                continue;
            }

            // 扩展 PCS 字符（重音字母等）
            if ((b >= 0x01 && b <= 0x35) || (b >= 0x51 && b <= 0x9A))
                continue;

            // 无效字符 - 不是 PCS 文本
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


