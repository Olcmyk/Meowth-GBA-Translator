using System.Text.Json;
using HavenSoft.HexManiac.Core;
using HavenSoft.HexManiac.Core.Models;
using HavenSoft.HexManiac.Core.Models.Runs;

namespace MeowthBridge;

public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        if (args.Length < 2 || args[0] != "extract")
        {
            Console.Error.WriteLine("Usage: MeowthBridge extract <rom_path> [-o output.json]");
            return 1;
        }

        var romPath = args[1];
        var outputPath = "texts.json";
        for (int i = 2; i < args.Length - 1; i++)
        {
            if (args[i] == "-o") outputPath = args[i + 1];
        }

        if (!File.Exists(romPath))
        {
            Console.Error.WriteLine($"ROM file not found: {romPath}");
            return 1;
        }

        Console.Error.WriteLine($"Loading ROM: {romPath}");
        var model = await RomLoader.Load(romPath);
        Console.Error.WriteLine($"ROM loaded. Game code: {RomLoader.GetGameCode(model)}");

        Console.Error.WriteLine("Extracting text...");
        var result = TextExtractor.Extract(model);

        var options = new JsonSerializerOptions { WriteIndented = true };
        var json = JsonSerializer.Serialize(result, options);
        File.WriteAllText(outputPath, json);

        Console.Error.WriteLine($"Extracted {result.Tables.Sum(t => t.Entries.Count)} table entries");
        Console.Error.WriteLine($"Extracted {result.FreeTexts.Count} free text entries");
        Console.Error.WriteLine($"Written to: {outputPath}");
        return 0;
    }
}
