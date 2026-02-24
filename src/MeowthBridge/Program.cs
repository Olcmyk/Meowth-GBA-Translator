using HavenSoft.HexManiac.Core.Models;

namespace MeowthBridge;

public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        if (args.Length < 1)
        {
            Console.Error.WriteLine("Usage:");
            Console.Error.WriteLine("  MeowthBridge extract <rom_path> [-o output.json]");
            Console.Error.WriteLine("  MeowthBridge list-anchors <rom_path>");
            Console.Error.WriteLine("  MeowthBridge fake-translate <input.json> [-o output.json]");
            Console.Error.WriteLine("  MeowthBridge apply <rom_path> <translations.json> [-o output.gba]");
            return 1;
        }

        var command = args[0];

        if (command == "apply")
        {
            if (args.Length < 3)
            {
                Console.Error.WriteLine("Usage: MeowthBridge apply <rom_path> <translations.json> [-o output.gba]");
                return 1;
            }

            var romPath = args[1];
            var jsonPath = args[2];
            var outputPath = romPath.Replace(".gba", "_translated.gba");
            for (int i = 3; i < args.Length - 1; i++)
            {
                if (args[i] == "-o") outputPath = args[i + 1];
            }

            if (!File.Exists(romPath))
            {
                Console.Error.WriteLine($"ROM file not found: {romPath}");
                return 1;
            }

            if (!File.Exists(jsonPath))
            {
                Console.Error.WriteLine($"JSON file not found: {jsonPath}");
                return 1;
            }

            // 复制 ROM 文件
            Console.Error.WriteLine($"Copying ROM: {romPath} -> {outputPath}");
            File.Copy(romPath, outputPath, overwrite: true);

            // 加载 ROM
            Console.Error.WriteLine($"Loading ROM: {outputPath}");
            var model = await RomLoader.Load(outputPath);
            Console.Error.WriteLine($"ROM loaded. Game code: {RomLoader.GetGameCode(model)}");

            // 应用翻译
            var writer = new TextWriter(model);
            var written = writer.ApplyTranslations(jsonPath);

            if (written > 0)
            {
                // 保存 ROM
                Console.Error.WriteLine($"Saving ROM: {outputPath}");
                await RomLoader.Save(model, outputPath);
                Console.Error.WriteLine($"Done! Applied {written} translations");
            }
            else
            {
                Console.Error.WriteLine("No translations were applied");
                return 1;
            }

            return 0;
        }

        if (command == "fake-translate")
        {
            if (args.Length < 2)
            {
                Console.Error.WriteLine("Usage: MeowthBridge fake-translate <input.json> [-o output.json]");
                return 1;
            }

            var inputPath = args[1];
            var outputPath = inputPath.Replace(".json", "_translated.json");
            for (int i = 2; i < args.Length - 1; i++)
            {
                if (args[i] == "-o") outputPath = args[i + 1];
            }

            if (!File.Exists(inputPath))
            {
                Console.Error.WriteLine($"Input file not found: {inputPath}");
                return 1;
            }

            FakeTranslator.TranslateJsonFile(inputPath, outputPath);
            return 0;
        }

        if (command == "list-anchors")
        {
            if (args.Length < 2)
            {
                Console.Error.WriteLine("Usage: MeowthBridge list-anchors <rom_path>");
                return 1;
            }

            var romPath = args[1];
            if (!File.Exists(romPath))
            {
                Console.Error.WriteLine($"ROM file not found: {romPath}");
                return 1;
            }

            Console.Error.WriteLine($"Loading ROM: {romPath}");
            var model = await RomLoader.Load(romPath);
            Console.Error.WriteLine($"ROM loaded. Game code: {RomLoader.GetGameCode(model)}\n");

            Console.WriteLine("Available anchors with text content:");
            Console.WriteLine("=====================================");

            var anchors = model.Anchors.OrderBy(a => a).ToList();
            foreach (var anchor in anchors)
            {
                if (anchor.Contains("name") || anchor.Contains("text") || anchor.Contains("description") ||
                    anchor.Contains("message") || anchor.Contains("string") || anchor.Contains("data"))
                {
                    var address = model.GetAddressFromAnchor(new HavenSoft.HexManiac.Core.Models.NoDataChangeDeltaModel(), -1, anchor);
                    if (address >= 0)
                    {
                        var run = model.GetNextRun(address);
                        Console.WriteLine($"{anchor,-50} @ 0x{address:X6}  [{run?.GetType().Name ?? "Unknown"}]");
                    }
                }
            }
            return 0;
        }

        if (command == "extract")
        {
            if (args.Length < 2)
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
            var extractor = new TextExtractor(model);
            var entries = extractor.ExtractAll();

            var json = extractor.ToJson(entries);
            File.WriteAllText(outputPath, json);

            Console.Error.WriteLine($"Extracted {entries.Count} entries");
            Console.Error.WriteLine($"Written to: {outputPath}");
            return 0;
        }

        Console.Error.WriteLine($"Unknown command: {command}");
        Console.Error.WriteLine("Usage:");
        Console.Error.WriteLine("  MeowthBridge extract <rom_path> [-o output.json]");
        Console.Error.WriteLine("  MeowthBridge list-anchors <rom_path>");
        Console.Error.WriteLine("  MeowthBridge fake-translate <input.json> [-o output.json]");
        Console.Error.WriteLine("  MeowthBridge apply <rom_path> <translations.json> [-o output.gba]");
        return 1;
    }
}
