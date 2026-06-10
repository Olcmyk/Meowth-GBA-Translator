using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Encodings.Web;
using HavenSoft.HexManiac.Core.Models;
using HavenSoft.HexManiac.Core.Models.Runs;
using HavenSoft.HexManiac.Core.Models.Code;

#pragma warning disable CS0162

namespace MeowthBridge;

public class TextExtractor
{
    private readonly IDataModel _model;
    private Dictionary<int, List<int>>? _exactPointerSources;

    public TextExtractor(IDataModel model)
    {
        _model = model;
    }

    public List<TextEntry> ExtractAll()
    {
        var entries = new List<TextEntry>();
        var extractedAddresses = new HashSet<int>();
        var entriesByAddress = new Dictionary<int, TextEntry>();
        int id = 0;

        // Phase 1: 提取表格文本（100% 准确，HMA 已识别表格结构）
        Console.Error.WriteLine("Phase 1: 提取表格文本...");
        ExtractTableTexts(entries, extractedAddresses, entriesByAddress, ref id);
        ExtractSequentialAbilityTexts(entries, extractedAddresses, entriesByAddress, ref id);
        ExtractLooseAbilityDescriptionTexts(entries, extractedAddresses, entriesByAddress, ref id);
        ExtractHackAbilityDescriptionTexts(entries, extractedAddresses, entriesByAddress, ref id);
        Console.Error.WriteLine($"  表格文本: {entries.Count} 条");

        // Phase 2: 扫描 loadpointer 指令，构建安全的指针源映射
        Console.Error.WriteLine("Phase 2: 扫描 loadpointer 指令...");
        var loadpointerMap = ScanLoadpointerSources();
        Console.Error.WriteLine($"  发现 {loadpointerMap.Count} 个文本地址的 loadpointer 引用");

        // Phase 3: 提取 loadpointer 引用的文本（脚本明确引用，非常安全）
        Console.Error.WriteLine("Phase 3: 提取 loadpointer 文本...");
        int beforeLp = entries.Count;
        ExtractLoadpointerTexts(entries, extractedAddresses, entriesByAddress, ref id, loadpointerMap);
        Console.Error.WriteLine($"  loadpointer 文本: {entries.Count - beforeLp} 条");

        Console.Error.WriteLine("Phase 4: loose expansion PCS text scan...");
        int beforeLoose = entries.Count;
        ExtractLooseExpansionPcsTexts(entries, extractedAddresses, entriesByAddress, ref id);
        Console.Error.WriteLine($"  loose custom text: {entries.Count - beforeLoose} entries");

        return entries;
    }

    private void ExtractTableTexts(
        List<TextEntry> entries,
        HashSet<int> extractedAddresses,
        Dictionary<int, TextEntry> entriesByAddress,
        ref int id)
    {
        var tableNames = new Dictionary<string, (string category, int? knownCount)>
        {
            // 基础数据表
            ["data.pokemon.names"] = ("pokemon_names", null),
            ["data.pokemon.type.names"] = ("type_names", 18),
            ["data.items.stats"] = ("item_names", 375),
            ["data.items.berry.stats"] = ("berry_names", null),
            ["data.decorations.stats"] = ("decoration_names", null),
            ["data.pokemon.moves.names"] = ("move_names", null),
            ["data.abilities.names"] = ("ability_names", null),
            ["data.pokemon.natures.names"] = ("nature_names", null),
            ["data.trainers.classes.names"] = ("trainer_classes", null),
            ["data.trainers.stats"] = ("trainer_names", null),
            ["data.pokemon.trades"] = ("trade_text", null),

            // 描述文本
            ["data.abilities.descriptions"] = ("ability_descriptions", null),
            ["data.pokemon.moves.descriptions"] = ("move_descriptions", null),
            ["data.pokemon.contest.descriptions"] = ("contest_descriptions", null),
            ["data.battlefrontier.tutor.descriptions1"] = ("tutor_descriptions", null),
            ["data.battlefrontier.tutor.descriptions2"] = ("tutor_descriptions", null),

            // 地图和栖息地
            ["data.maps.names"] = ("map_names", null),
            ["data.maps.banks"] = ("map_banks", null),
            ["data.pokedex.stats"] = ("pokedex_text", null),
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

        foreach (var tableName in _model.Anchors.OrderBy(a => a))
        {
            var isKnownTextTable = tableNames.ContainsKey(tableName);
            if (!ShouldScanTable(tableName, isKnownTextTable)) continue;

            var (category, knownCount) = tableNames.TryGetValue(tableName, out var known)
                ? known
                : (InferBaseCategory(tableName), null);
            var address = _model.GetAddressFromAnchor(new NoDataChangeDeltaModel(), -1, tableName);
            if (address < 0) continue;

            var run = _model.GetNextRun(address);
            if (run is not ITableRun tableRun) continue;
            if (!TableHasTextFields(tableRun)) continue;

            var elementCount = knownCount ?? tableRun.ElementCount;
            if (elementCount <= 1 && knownCount == null) continue;

            for (int i = 0; i < elementCount; i++)
            {
                foreach (var textField in ExtractTableElementTexts(tableRun, tableName, category, i))
                {
                    if (string.IsNullOrEmpty(textField.Text)) continue;
                    AddOrMergeEntry(
                        entries, extractedAddresses, entriesByAddress, ref id,
                        $"tbl_{textField.Category}",
                        textField.Category,
                        textField.TextAddress,
                        textField.Text,
                        textField.TextLength,
                        textField.IsPointerBased,
                        textField.PointerSource,
                        tableName,
                        i,
                        textField.FieldName);
                }
                continue;

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

    private List<ExtractedTextField> ExtractTableElementTexts(
        ITableRun tableRun,
        string tableName,
        string baseCategory,
        int index)
    {
        var results = new List<ExtractedTextField>();
        var elementStart = tableRun.Start + index * tableRun.ElementLength;
        int segmentOffset = 0;

        foreach (var segment in tableRun.ElementContent)
        {
            var fieldName = string.IsNullOrWhiteSpace(segment.Name)
                ? $"field_{segmentOffset:X}"
                : segment.Name;
            var category = InferFieldCategory(tableName, baseCategory, fieldName);

            if (segment.Type == ElementContentType.PCS)
            {
                var text = _model.TextConverter.Convert(_model, elementStart + segmentOffset, segment.Length);
                if (IsExtractableTableText(text))
                {
                    results.Add(new ExtractedTextField
                    {
                        FieldName = fieldName,
                        Category = category,
                        Text = text,
                        TextAddress = elementStart + segmentOffset,
                        TextLength = segment.Length,
                        IsPointerBased = false
                    });
                }
            }
            else if (segment.Type == ElementContentType.Pointer && IsLikelyTextPointerField(tableName, fieldName, category))
            {
                var pointerSource = elementStart + segmentOffset;
                var pointer = _model.ReadPointer(pointerSource);
                if (pointer >= 0 && pointer < _model.Count)
                {
                    var textLength = ValidatePcsText(pointer);
                    if (textLength >= 2)
                    {
                        var text = _model.TextConverter.Convert(_model, pointer, textLength);
                        if (IsExtractableTableText(text))
                        {
                            results.Add(new ExtractedTextField
                            {
                                FieldName = fieldName,
                                Category = category,
                                Text = text,
                                TextAddress = pointer,
                                TextLength = textLength,
                                IsPointerBased = true,
                                PointerSource = pointerSource
                            });
                        }
                    }
                }
            }

            segmentOffset += segment.Length;
        }

        return results;
    }

    private static bool TableHasTextFields(ITableRun tableRun)
    {
        return tableRun.ElementContent.Any(segment =>
            segment.Type == ElementContentType.PCS ||
            segment.Type == ElementContentType.Pointer);
    }

    private static bool ShouldScanTable(string tableName, bool isKnownTextTable)
    {
        if (isKnownTextTable) return true;

        var name = tableName.ToLowerInvariant();
        string[] unsafeTokens =
        {
            ".graphics", "graphics.", ".gfx", "_gfx", ".sprite", "sprites",
            ".palette", "palettes", ".tileset", "tilesets", ".tilemap",
            "tilemap", ".animation", "animations", ".sound", "sound.",
            ".song", "songs", ".cry", "cries", ".music", "tracks",
        };
        if (unsafeTokens.Any(name.Contains)) return false;

        string[] textTokens =
        {
            ".text", "texts", ".menus.", ".menu.", "message", "messages",
            "string", "strings", "dialog", "dialogue", "script.text",
        };
        return textTokens.Any(name.Contains);
    }

    private static bool IsLikelyTextPointerField(string tableName, string fieldName, string category)
    {
        var field = fieldName.ToLowerInvariant();
        if (field.Contains("description")) return true;
        if (field == "text" || field == "line" || field == "label" || field == "message") return true;
        if (field.EndsWith("text") || field.EndsWith("message")) return true;
        if (category.Contains("description")) return true;
        if (tableName.Contains(".text") || tableName.Contains(".menus.")) return true;
        return false;
    }

    private static bool IsExtractableTableText(string text)
    {
        if (string.IsNullOrEmpty(text) || text == "\"\"") return false;
        var clean = text.Trim('"').Trim();
        return clean.Length > 0;
    }

    private void ExtractSequentialAbilityTexts(
        List<TextEntry> entries,
        HashSet<int> extractedAddresses,
        Dictionary<int, TextEntry> entriesByAddress,
        ref int id)
    {
        ExtractSequentialPcsStrings(
            entries, extractedAddresses, entriesByAddress, ref id,
            "data.abilities.names", "ability_names", "ability_name", "name",
            LooksLikeAbilityName, maxCount: 512);
        ExtractSequentialPcsStrings(
            entries, extractedAddresses, entriesByAddress, ref id,
            "data.abilities.descriptions", "ability_descriptions", "ability_description", "description",
            LooksLikeAbilityDescription, maxCount: 512);
    }

    private void ExtractSequentialPcsStrings(
        List<TextEntry> entries,
        HashSet<int> extractedAddresses,
        Dictionary<int, TextEntry> entriesByAddress,
        ref int id,
        string anchorName,
        string category,
        string idPrefix,
        string tableField,
        Func<string, bool> predicate,
        int maxCount)
    {
        var pos = _model.GetAddressFromAnchor(new NoDataChangeDeltaModel(), -1, anchorName);
        if (pos < 0) return;

        for (int index = 0; index < maxCount && pos < _model.Count; index++)
        {
            while (pos < _model.Count && _model[pos] == 0xFF)
                pos++;
            if (pos >= _model.Count) break;

            var textLength = ValidateSequentialPcsText(pos);
            if (textLength < 2) break;

            var text = _model.TextConverter.Convert(_model, pos, textLength);
            if (!predicate(text)) break;

            AddOrMergeEntry(
                entries, extractedAddresses, entriesByAddress, ref id,
                idPrefix, category, pos, text, textLength, false, null,
                anchorName, index, tableField);

            pos += textLength;
        }
    }

    private void ExtractLooseAbilityDescriptionTexts(
        List<TextEntry> entries,
        HashSet<int> extractedAddresses,
        Dictionary<int, TextEntry> entriesByAddress,
        ref int id)
    {
        var start = entries
            .Where(e => e.Category == "ability_descriptions")
            .Select(e => int.TryParse(e.Address.AsSpan(2), System.Globalization.NumberStyles.HexNumber, null, out var address) ? address : -1)
            .Where(address => address >= 0)
            .DefaultIfEmpty(_model.GetAddressFromAnchor(new NoDataChangeDeltaModel(), -1, "data.abilities.descriptions"))
            .Min();
        if (start < 0) return;

        const int MaxAbilityDescriptionRegion = 0x0800;
        var nextAbilityNameAddress = entries
            .Where(e => e.Category == "ability_names")
            .Select(e => int.TryParse(e.Address.AsSpan(2), System.Globalization.NumberStyles.HexNumber, null, out var address) ? address : -1)
            .Where(address => address > start)
            .DefaultIfEmpty(_model.Count)
            .Min();
        var end = Math.Min(Math.Min(_model.Count, start + MaxAbilityDescriptionRegion), nextAbilityNameAddress);

        for (int address = start; address < end; address++)
        {
            if (extractedAddresses.Contains(address)) continue;
            if (address > start && _model[address - 1] != 0xFF) continue;

            var textLength = ValidateSequentialPcsText(address);
            if (textLength < 2) continue;

            var text = _model.TextConverter.Convert(_model, address, textLength);
            if (!LooksLikeAbilityDescription(text)) continue;

            AddOrMergeEntry(
                entries, extractedAddresses, entriesByAddress, ref id,
                "ability_description", "ability_descriptions", address, text, textLength, false, null,
                "data.abilities.descriptions", null, "description");

            address += Math.Max(0, textLength - 1);
        }
    }

    private void ExtractHackAbilityDescriptionTexts(
        List<TextEntry> entries,
        HashSet<int> extractedAddresses,
        Dictionary<int, TextEntry> entriesByAddress,
        ref int id)
    {
        var firstAbilityNameAddress = entries
            .Where(e => e.Category == "ability_names")
            .Select(e => int.TryParse(e.Address.AsSpan(2), System.Globalization.NumberStyles.HexNumber, null, out var address) ? address : -1)
            .Where(address => address > 0x0800000)
            .DefaultIfEmpty(-1)
            .Min();
        if (firstAbilityNameAddress < 0) return;

        const int MaxPrecedingDescriptionBlock = 0x1800;
        var start = Math.Max(0, firstAbilityNameAddress - MaxPrecedingDescriptionBlock);
        var end = Math.Min(_model.Count, firstAbilityNameAddress);

        for (int address = start; address < end; address++)
        {
            if (extractedAddresses.Contains(address)) continue;
            if (address > start && _model[address - 1] != 0xFF) continue;

            var textLength = ValidateSequentialPcsText(address);
            if (textLength < 2) continue;

            var text = _model.TextConverter.Convert(_model, address, textLength);
            if (!LooksLikeAbilityDescription(text)) continue;

            AddOrMergeEntry(
                entries, extractedAddresses, entriesByAddress, ref id,
                "ability_description", "ability_descriptions", address, text, textLength, false, null,
                "data.abilities.descriptions", null, "description");

            address += Math.Max(0, textLength - 1);
        }
    }

    private static bool LooksLikeAbilityName(string text)
    {
        if (string.IsNullOrEmpty(text) || text == "\"\"") return false;
        var clean = text.Trim('"').Trim();
        if (clean == "-------") return true;
        if (clean == "-") return true;
        if (clean.Length < 2 || clean.Length > 32) return false;
        if (clean.Contains('\r') || clean.Contains('\n') || clean.Contains('\\') || clean.Contains('['))
            return false;
        return clean.All(ch =>
            char.IsLetter(ch) || ch == ' ' || ch == '-' || ch == '\'' || ch == '.' || ch == '0' || ch == '1' || ch == '2');
    }

    private static bool LooksLikeAbilityDescription(string text)
    {
        if (string.IsNullOrEmpty(text) || text == "\"\"") return false;
        var clean = text.Trim('"').Trim();
        if (clean.Length < 8 || clean.Length > 96) return false;
        if (clean.Contains('\r') || clean.Contains('\n') || clean.Contains('\\') || clean.Contains('['))
            return false;
        if (clean.Count(char.IsLower) < 2) return false;
        return clean.Count(char.IsLetter) >= 4;
    }

    private int ValidateSequentialPcsText(int address)
    {
        if (address < 0 || address >= _model.Count) return 0;

        const int MAX_LENGTH = 128;
        int printable = 0;

        for (int i = 0; i < MAX_LENGTH && address + i < _model.Count; i++)
        {
            byte b = _model[address + i];
            if (b == 0xFF)
                return printable > 0 ? i + 1 : 0;

            if ((b >= 0xBB && b <= 0xD4) || (b >= 0xD5 && b <= 0xEE) || b == 0x1B)
            {
                printable++;
                continue;
            }
            if (b == 0x00 || (b >= 0xA1 && b <= 0xBA))
            {
                printable++;
                continue;
            }
            if (b == 0xFA || b == 0xFB || b == 0xFE)
            {
                printable++;
                continue;
            }
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

            return 0;
        }

        return 0;
    }

    private static string InferBaseCategory(string tableName)
    {
        var name = tableName.Replace(".", "_").Replace("/", "_");
        if (name.StartsWith("data_")) name = name["data_".Length..];
        return $"table_{name}";
    }

    private static string InferFieldCategory(string tableName, string baseCategory, string fieldName)
    {
        var field = fieldName.ToLowerInvariant();
        if (tableName == "data.items.stats")
        {
            if (field == "name") return "item_names";
            if (field.StartsWith("description")) return "item_descriptions";
        }
        if (tableName == "data.items.berry.stats")
        {
            if (field == "name") return "berry_names";
            if (field.StartsWith("description")) return "berry_descriptions";
        }
        if (tableName == "data.decorations.stats")
        {
            if (field == "name") return "decoration_names";
            if (field.StartsWith("description")) return "decoration_descriptions";
        }
        if (tableName == "data.pokedex.stats")
        {
            if (field == "species") return "pokedex_species";
            if (field.StartsWith("description")) return "pokedex_descriptions";
        }
        if (tableName == "data.trainers.stats" && field == "name") return "trainer_names";
        if (tableName == "data.pokemon.trades")
        {
            if (field == "nickname") return "trade_nicknames";
            if (field == "trainername") return "trade_trainer_names";
        }
        if (field.StartsWith("description"))
            return baseCategory.Contains("description") ? baseCategory : $"{baseCategory}_descriptions";
        if (field == "name" || field == "label" || field == "species" || field == "nickname" || field == "trainername")
            return baseCategory;
        return $"{baseCategory}_{field}";
    }

    private static void AddOrMergeEntry(
        List<TextEntry> entries,
        HashSet<int> extractedAddresses,
        Dictionary<int, TextEntry> entriesByAddress,
        ref int id,
        string idPrefix,
        string category,
        int textAddress,
        string text,
        int textLength,
        bool isPointerBased,
        int? pointerSource,
        string? tableName = null,
        int? tableIndex = null,
        string? tableField = null)
    {
        if (entriesByAddress.TryGetValue(textAddress, out var existing))
        {
            if (pointerSource.HasValue)
            {
                var source = $"0x{pointerSource.Value:X}";
                if (!existing.PointerSources.Contains(source))
                    existing.PointerSources.Add(source);
                existing.IsPointerBased = true;
            }
            return;
        }

        extractedAddresses.Add(textAddress);
        var entry = new TextEntry
        {
            Id = $"{idPrefix}_{id++:D5}",
            Category = category,
            Address = $"0x{textAddress:X}",
            Original = text,
            ByteLength = textLength,
            IsPointerBased = isPointerBased,
            TableName = tableName,
            TableIndex = tableIndex,
            TableField = tableField
        };
        if (pointerSource.HasValue)
            entry.PointerSources.Add($"0x{pointerSource.Value:X}");
        entries.Add(entry);
        entriesByAddress[textAddress] = entry;
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
        List<TextEntry> entries,
        HashSet<int> extractedAddresses,
        Dictionary<int, TextEntry> entriesByAddress,
        ref int id,
        Dictionary<int, HashSet<int>> loadpointerMap)
    {
        int found = 0;

        foreach (var (textAddr, ptrSources) in loadpointerMap)
        {
            var textLength = ValidatePcsText(textAddr);
            if (textLength < 2) continue;

            var text = _model.TextConverter.Convert(_model, textAddr, textLength);
            if (string.IsNullOrEmpty(text) || text == "\"\"") continue;

            var cleanText = text.Trim('"');
            if (cleanText.Length < 1) continue;

            if (entriesByAddress.TryGetValue(textAddr, out var existing))
            {
                foreach (var ptrSource in ptrSources.Select(p => $"0x{p:X}"))
                    if (!existing.PointerSources.Contains(ptrSource))
                        existing.PointerSources.Add(ptrSource);
                existing.IsPointerBased = true;
                continue;
            }

            AddOrMergeEntry(
                entries, extractedAddresses, entriesByAddress, ref id,
                "scr", "scripts", textAddr, text, textLength, true, null);
            var added = entriesByAddress[textAddr];
            foreach (var ptrSource in ptrSources.Select(p => $"0x{p:X}"))
                if (!added.PointerSources.Contains(ptrSource))
                    added.PointerSources.Add(ptrSource);
            found++;
        }
    }

    private void ExtractLooseExpansionPcsTexts(
        List<TextEntry> entries,
        HashSet<int> extractedAddresses,
        Dictionary<int, TextEntry> entriesByAddress,
        ref int id)
    {
        const int LooseTextStart = 0x01600000;
        var start = Math.Min(LooseTextStart, _model.Count);

        for (int address = start; address < _model.Count; address++)
        {
            if (extractedAddresses.Contains(address)) continue;
            if (address > start && _model[address - 1] != 0xFF) continue;

            var textLength = ValidatePcsText(address);
            if (textLength < 4) continue;

            var text = _model.TextConverter.Convert(_model, address, textLength);
            if (!LooksLikeLooseCustomText(address, text)) continue;

            var pointerSources = FindPointerSourcesTo(address);
            AddOrMergeEntry(
                entries, extractedAddresses, entriesByAddress, ref id,
                "custom", "custom_text", address, text, textLength, pointerSources.Count > 0,
                pointerSources.Count > 0 ? pointerSources[0] : null);

            if (pointerSources.Count > 1 && entriesByAddress.TryGetValue(address, out var added))
            {
                foreach (var pointerSource in pointerSources.Skip(1))
                {
                    var source = $"0x{pointerSource:X}";
                    if (!added.PointerSources.Contains(source))
                        added.PointerSources.Add(source);
                }
            }

            address += Math.Max(0, textLength - 1);
        }
    }

    private List<int> FindPointerSourcesTo(int textAddress)
    {
        _exactPointerSources ??= BuildExactPointerSourceMap();
        return _exactPointerSources.TryGetValue(textAddress, out var sources)
            ? sources
            : new List<int>();
    }

    private Dictionary<int, List<int>> BuildExactPointerSourceMap()
    {
        var sourcesByTarget = new Dictionary<int, List<int>>();
        for (int address = 0x0A0000; address <= _model.Count - 4; address += 4)
        {
            var value =
                _model[address] |
                (_model[address + 1] << 8) |
                (_model[address + 2] << 16) |
                (_model[address + 3] << 24);
            if (value < 0x08000000) continue;

            var target = value - 0x08000000;
            if (target < 0 || target >= _model.Count) continue;

            if (!sourcesByTarget.TryGetValue(target, out var sources))
            {
                sources = new List<int>();
                sourcesByTarget[target] = sources;
            }
            sources.Add(address);
        }

        return sourcesByTarget;
    }

    private static bool LooksLikeLooseCustomText(int address, string text)
    {
        if (string.IsNullOrEmpty(text) || text == "\"\"") return false;

        var clean = text.Trim('"').Trim();
        if (clean.Length < 8 || clean.Length > 512) return false;
        if (clean.Contains("\\!") || clean.Contains("\\?") || clean.Contains("\\CC")) return false;
        if (clean.Contains("\\btn")) return false;
        if (HasRawHexEscape(clean)) return false;
        if (!IsMostlyPlainEnglishText(clean)) return false;
        if (address < 0x01E00000 && !LooksLikeLongExpansionDescription(clean)) return false;

        int letters = 0;
        int textLike = 0;
        foreach (var ch in clean)
        {
            if (char.IsLetter(ch)) letters++;
            if (
                char.IsLetterOrDigit(ch) ||
                char.IsWhiteSpace(ch) ||
                ch == '\\' ||
                ch == '[' ||
                ch == ']' ||
                ".,!?;:'\"-/()[]".Contains(ch)
            )
            {
                textLike++;
            }
        }

        if (letters < 6) return false;
        if (!clean.Any(char.IsWhiteSpace) && !clean.Any(ch => ".,!?;:'\"-/()[]".Contains(ch))) return false;
        return (double)textLike / clean.Length >= 0.75;
    }

    private static bool HasRawHexEscape(string text)
    {
        for (int i = 0; i + 2 < text.Length; i++)
        {
            if (text[i] != '\\') continue;

            var next = text[i + 1];
            if (next == 'n' || next == 'p' || next == 'l' || next == 'r' || next == '.' || next == 'q')
                continue;

            return true;
        }
        return false;
    }

    private static bool IsMostlyPlainEnglishText(string text)
    {
        if (!HasOnlyAllowedBracketTokens(text)) return false;

        var plainText = RemoveBracketTokens(text);
        int textLike = 0;
        int letters = 0;
        int lowercase = 0;
        int words = 0;
        bool inWord = false;

        foreach (var ch in plainText)
        {
            var allowed =
                ch <= 0x7E ||
                ch == '\r' ||
                ch == '\n' ||
                ch == 'é' ||
                ch == 'É' ||
                ch == '♂' ||
                ch == '♀';
            if (!allowed)
                return false;

            if (char.IsLetter(ch))
            {
                letters++;
                if (char.IsLower(ch))
                    lowercase++;
                if (!inWord)
                {
                    words++;
                    inWord = true;
                }
            }
            else if (ch != '\'')
            {
                inWord = false;
            }

            if (
                char.IsLetterOrDigit(ch) ||
                char.IsWhiteSpace(ch) ||
                ch == '\\' ||
                ch == '[' ||
                ch == ']' ||
                ".,!?;:'\"-/()[]".Contains(ch)
            )
            {
                textLike++;
            }
        }

        if (letters < 6 || lowercase < 2 || words < 2) return false;
        return (double)textLike / plainText.Length >= 0.90;
    }

    private static bool LooksLikeLongExpansionDescription(string text)
    {
        var plain = RemoveBracketTokens(text)
            .Replace("\\n", " ")
            .Replace("\\p", " ")
            .Replace("\\l", " ")
            .Replace("\\r", " ")
            .Replace("\\.", " ");

        int words = 0;
        bool inWord = false;
        foreach (var ch in plain)
        {
            if (char.IsLetter(ch))
            {
                if (!inWord)
                {
                    words++;
                    inWord = true;
                }
            }
            else if (ch != '\'')
            {
                inWord = false;
            }
        }

        return plain.Trim().Length >= 40 && words >= 6;
    }

    private static bool HasOnlyAllowedBracketTokens(string text)
    {
        var allowed = new HashSet<string>
        {
            "player", "rival",
            "buffer1", "buffer2", "buffer3",
            "red", "black", "blue", "green", "white", "grey", "gray",
            "yellow", "magenta", "cyan", "lightblue", "lightgreen",
        };

        for (int i = 0; i < text.Length; i++)
        {
            if (text[i] != '[') continue;
            var end = text.IndexOf(']', i + 1);
            if (end < 0) return false;
            var token = text.Substring(i + 1, end - i - 1).ToLowerInvariant();
            if (!allowed.Contains(token)) return false;
            i = end;
        }

        return true;
    }

    private static string RemoveBracketTokens(string text)
    {
        var output = new System.Text.StringBuilder(text.Length);
        for (int i = 0; i < text.Length; i++)
        {
            if (text[i] == '[')
            {
                var end = text.IndexOf(']', i + 1);
                if (end >= 0)
                {
                    i = end;
                    continue;
                }
            }
            output.Append(text[i]);
        }
        return output.ToString();
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

    [JsonPropertyName("table_field")]
    public string? TableField { get; set; }

    [JsonPropertyName("translated")]
    public string? Translated { get; set; }
}

internal class ExtractedTextField
{
    public string FieldName { get; set; } = "";
    public string Category { get; set; } = "";
    public string Text { get; set; } = "";
    public int TextAddress { get; set; }
    public int TextLength { get; set; }
    public bool IsPointerBased { get; set; }
    public int? PointerSource { get; set; }
}
