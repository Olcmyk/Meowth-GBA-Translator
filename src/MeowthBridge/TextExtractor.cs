using System.Text.Json.Serialization;
using HavenSoft.HexManiac.Core.Models;
using HavenSoft.HexManiac.Core.Models.Runs;

namespace MeowthBridge;

#region JSON Models

public class ExtractionResult
{
    [JsonPropertyName("game_code")]
    public string GameCode { get; set; } = "";

    [JsonPropertyName("tables")]
    public List<TableExtraction> Tables { get; set; } = new();

    [JsonPropertyName("free_texts")]
    public List<FreeTextEntry> FreeTexts { get; set; } = new();
}

public class TableExtraction
{
    [JsonPropertyName("category")]
    public string Category { get; set; } = "";

    [JsonPropertyName("table_name")]
    public string TableName { get; set; } = "";

    [JsonPropertyName("entries")]
    public List<TableEntry> Entries { get; set; } = new();
}

public class TableEntry
{
    [JsonPropertyName("index")]
    public int Index { get; set; }

    [JsonPropertyName("address")]
    public string Address { get; set; } = "";

    [JsonPropertyName("pointer_addresses")]
    public List<string> PointerAddresses { get; set; } = new();

    [JsonPropertyName("original")]
    public string Original { get; set; } = "";

    [JsonPropertyName("max_bytes")]
    public int MaxBytes { get; set; }

    [JsonPropertyName("is_pointer")]
    public bool IsPointer { get; set; }
}

public class FreeTextEntry
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("address")]
    public string Address { get; set; } = "";

    [JsonPropertyName("pointer_addresses")]
    public List<string> PointerAddresses { get; set; } = new();

    [JsonPropertyName("original")]
    public string Original { get; set; } = "";

    [JsonPropertyName("byte_length")]
    public int ByteLength { get; set; }
}

#endregion

public static class TextExtractor
{
    // Tables with inline PCS text (name is embedded in each element)
    private static readonly (string tableName, string category, string fieldName)[] InlineTables = {
        (HardcodeTablesModel.PokemonNameTable, "pokemon_names", "name"),
        (HardcodeTablesModel.MoveNamesTable, "move_names", "name"),
        (HardcodeTablesModel.AbilityNamesTable, "ability_names", "name"),
        (HardcodeTablesModel.ItemsTableName, "item_names", "name"),
        (HardcodeTablesModel.TypesTableName, "type_names", "name"),
        (HardcodeTablesModel.TrainerClassNamesTable, "trainer_class_names", "name"),
    };

    // Tables with pointer-based text (each element has a pointer to text elsewhere)
    private static readonly (string tableName, string category, string fieldName)[] PointerTables = {
        (HardcodeTablesModel.MapNameTable, "map_names", "name"),
        (HardcodeTablesModel.NaturesTableName, "nature_names", "name"),
        (HardcodeTablesModel.MoveDescriptionsName, "move_descriptions", "description"),
        (HardcodeTablesModel.AbilityDescriptionsTable, "ability_descriptions", "description"),
    };

    public static ExtractionResult Extract(HardcodeTablesModel model)
    {
        var result = new ExtractionResult { GameCode = RomLoader.GetGameCode(model) };
        var tableTextAddresses = new HashSet<int>();

        // Extract inline tables
        foreach (var (tableName, category, fieldName) in InlineTables)
        {
            var table = ExtractInlineTable(model, tableName, category, fieldName, tableTextAddresses);
            if (table != null) result.Tables.Add(table);
        }

        // Extract pointer-based tables
        foreach (var (tableName, category, fieldName) in PointerTables)
        {
            var table = ExtractPointerTable(model, tableName, category, fieldName, tableTextAddresses);
            if (table != null) result.Tables.Add(table);
        }

        // Extract free text
        result.FreeTexts = ExtractFreeText(model, tableTextAddresses);
        return result;
    }

    // Known element counts for FireRed (BPRE0) when HMA can't resolve dynamic lengths
    private static readonly Dictionary<string, int> KnownCounts = new() {
        { "data.items.stats", 375 },
        { "data.pokemon.type.names", 18 },
    };

    private static TableExtraction? ExtractInlineTable(
        HardcodeTablesModel model, string tableName, string category,
        string fieldName, HashSet<int> tableTextAddresses)
    {
        var tableRun = model.GetTable(tableName);
        if (tableRun == null) { Console.Error.WriteLine($"  [SKIP] Table not found: {tableName}"); return null; }

        // Find the text segment offset
        var segments = tableRun.ElementContent;
        int textOffset = 0;
        int textLength = 0;
        bool found = false;
        foreach (var seg in segments)
        {
            if (seg.Name == fieldName && seg.Type == ElementContentType.PCS)
            {
                textLength = seg.Length;
                found = true;
                break;
            }
            textOffset += seg.Length;
        }
        if (!found) { Console.Error.WriteLine($"  [SKIP] No PCS field '{fieldName}' in {tableName}"); return null; }

        // Use known count if HMA reports too few elements
        int elementCount = tableRun.ElementCount;
        if (elementCount <= 1 && KnownCounts.TryGetValue(tableName, out int knownCount))
        {
            Console.Error.WriteLine($"  [FIX] {tableName}: HMA reports {elementCount}, using known count {knownCount}");
            elementCount = knownCount;
        }

        var extraction = new TableExtraction { Category = category, TableName = tableName };
        Console.Error.WriteLine($"  {tableName}: {elementCount} entries (inline, {textLength}B field)");

        for (int i = 0; i < elementCount; i++)
        {
            int elemStart = tableRun.Start + i * tableRun.ElementLength;
            int textStart = elemStart + textOffset;
            tableTextAddresses.Add(textStart);

            string text = model.TextConverter.Convert(model, textStart, textLength).Trim('"');

            // For inline table text, the pointer is to the table start, not individual elements
            var pointers = new List<string>();
            if (i == 0 && tableRun.PointerSources != null)
                foreach (int src in tableRun.PointerSources)
                    pointers.Add($"0x{src:X6}");

            extraction.Entries.Add(new TableEntry
            {
                Index = i,
                Address = $"0x{textStart:X6}",
                PointerAddresses = pointers,
                Original = text,
                MaxBytes = textLength,
                IsPointer = false
            });
        }
        return extraction;
    }

    private static TableExtraction? ExtractPointerTable(
        HardcodeTablesModel model, string tableName, string category,
        string fieldName, HashSet<int> tableTextAddresses)
    {
        var tableRun = model.GetTable(tableName);
        if (tableRun == null) { Console.Error.WriteLine($"  [SKIP] Table not found: {tableName}"); return null; }

        // Find the pointer segment offset
        var segments = tableRun.ElementContent;
        int ptrOffset = 0;
        bool found = false;
        foreach (var seg in segments)
        {
            if (seg.Name == fieldName && seg.Type == ElementContentType.Pointer)
            {
                found = true;
                break;
            }
            ptrOffset += seg.Length;
        }
        if (!found) { Console.Error.WriteLine($"  [SKIP] No pointer field '{fieldName}' in {tableName}"); return null; }

        var extraction = new TableExtraction { Category = category, TableName = tableName };
        Console.Error.WriteLine($"  {tableName}: {tableRun.ElementCount} entries (pointer-based)");

        for (int i = 0; i < tableRun.ElementCount; i++)
        {
            int elemStart = tableRun.Start + i * tableRun.ElementLength;
            int ptrAddr = elemStart + ptrOffset;

            // Read the 4-byte pointer (little-endian, subtract 0x08000000)
            int raw = model.RawData[ptrAddr]
                    | (model.RawData[ptrAddr + 1] << 8)
                    | (model.RawData[ptrAddr + 2] << 16)
                    | (model.RawData[ptrAddr + 3] << 24);
            int textAddr = raw - 0x08000000;

            if (textAddr < 0 || textAddr >= model.RawData.Length) continue;

            // Find the PCSRun at this address to get length
            var run = model.GetNextRun(textAddr);
            if (run.Start != textAddr || run is not PCSRun pcsRun) continue;

            string text = model.TextConverter.Convert(model, textAddr, pcsRun.Length).Trim('"');
            tableTextAddresses.Add(textAddr);

            // The pointer address itself is what we need for repointing
            extraction.Entries.Add(new TableEntry
            {
                Index = i,
                Address = $"0x{textAddr:X6}",
                PointerAddresses = new List<string> { $"0x{ptrAddr:X6}" },
                Original = text,
                MaxBytes = pcsRun.Length,
                IsPointer = true
            });
        }
        return extraction;
    }

    private static List<FreeTextEntry> ExtractFreeText(
        HardcodeTablesModel model, HashSet<int> tableTextAddresses)
    {
        var entries = new List<FreeTextEntry>();
        int id = 0;

        foreach (var run in model.All<PCSRun>())
        {
            if (tableTextAddresses.Contains(run.Start)) continue;

            string text = model.TextConverter.Convert(model, run.Start, run.Length).Trim('"');
            if (string.IsNullOrWhiteSpace(text) || text.Length < 2) continue;

            var pointers = new List<string>();
            if (run.PointerSources != null)
                foreach (int src in run.PointerSources)
                    pointers.Add($"0x{src:X6}");

            entries.Add(new FreeTextEntry
            {
                Id = $"text_{id:D5}",
                Address = $"0x{run.Start:X6}",
                PointerAddresses = pointers,
                Original = text,
                ByteLength = run.Length
            });
            id++;
        }
        return entries;
    }
}
