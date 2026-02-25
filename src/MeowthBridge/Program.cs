using HavenSoft.HexManiac.Core.Models;
using DotNetEnv;
using System.Diagnostics;

namespace MeowthBridge;

public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        if (args.Length < 1)
        {
            PrintUsage();
            return 1;
        }

        var command = args[0];

        return command switch
        {
            "extract" => await RunExtract(args),
            "translate" => await RunTranslate(args),
            "apply" => await RunApply(args),
            _ => PrintUnknownCommand(command)
        };
    }

    private static async Task<int> RunExtract(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine("Usage: MeowthBridge extract <rom.gba>");
            return 1;
        }

        var romPath = args[1];
        if (!File.Exists(romPath))
        {
            Console.Error.WriteLine($"ROM file not found: {romPath}");
            return 1;
        }

        Directory.CreateDirectory("work");

        Console.Error.WriteLine($"Loading ROM: {romPath}");
        var model = await RomLoader.Load(romPath);
        Console.Error.WriteLine($"ROM loaded. Game code: {RomLoader.GetGameCode(model)}");

        Console.Error.WriteLine("Extracting text...");
        var extractor = new TextExtractor(model);
        var entries = extractor.ExtractAll();

        var outputPath = Path.Combine("work", "text.json");
        var json = extractor.ToJson(entries);
        File.WriteAllText(outputPath, json);

        Console.Error.WriteLine($"Extracted {entries.Count} entries → {outputPath}");
        return 0;
    }

    private static async Task<int> RunTranslate(string[] args)
    {
        // 加载 .env 文件
        var envPath = Path.Combine(Directory.GetCurrentDirectory(), ".env");
        if (File.Exists(envPath))
            DotNetEnv.Env.Load(envPath);

        string? apiKey = null;
        var apiUrl = "https://api.deepseek.com/v1/chat/completions";
        var model = "deepseek-chat";
        int batchSize = 30;
        int delayMs = 500;

        // 解析参数
        for (int i = 1; i < args.Length; i++)
        {
            if (args[i] == "--api-key" && i + 1 < args.Length) apiKey = args[++i];
            else if (args[i] == "--api-url" && i + 1 < args.Length) apiUrl = args[++i];
            else if (args[i] == "--model" && i + 1 < args.Length) model = args[++i];
            else if (args[i] == "--batch" && i + 1 < args.Length) batchSize = int.Parse(args[++i]);
            else if (args[i] == "--delay" && i + 1 < args.Length) delayMs = int.Parse(args[++i]);
        }

        // 从环境变量获取 API Key
        if (string.IsNullOrEmpty(apiKey))
        {
            apiKey = Environment.GetEnvironmentVariable("DEEPSEEK_API_KEY")
                  ?? Environment.GetEnvironmentVariable("OPENAI_API_KEY");
        }

        if (string.IsNullOrEmpty(apiKey))
        {
            Console.Error.WriteLine("Error: API Key not found!");
            Console.Error.WriteLine("Provide via: --api-key KEY, env DEEPSEEK_API_KEY, or .env file");
            return 1;
        }

        var inputPath = Path.Combine("work", "text.json");
        var outputPath = Path.Combine("work", "text_translated.json");

        if (!File.Exists(inputPath))
        {
            Console.Error.WriteLine($"Input file not found: {inputPath}");
            Console.Error.WriteLine("Run 'extract' first to generate work/text.json");
            return 1;
        }

        Console.Error.WriteLine($"API: {apiUrl}, Model: {model}");
        var translator = new RealTranslator(apiKey, apiUrl, model);
        await translator.TranslateJsonFileAsync(inputPath, outputPath, batchSize, delayMs);
        return 0;
    }

    private static async Task<int> RunApply(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine("Usage: MeowthBridge apply <rom.gba>");
            return 1;
        }

        var romPath = args[1];
        if (!File.Exists(romPath))
        {
            Console.Error.WriteLine($"ROM file not found: {romPath}");
            return 1;
        }

        var translationsPath = Path.Combine("work", "text_translated.json");
        if (!File.Exists(translationsPath))
        {
            Console.Error.WriteLine($"Translations not found: {translationsPath}");
            Console.Error.WriteLine("Run 'translate' first to generate work/text_translated.json");
            return 1;
        }

        // 生成输出路径
        Directory.CreateDirectory("outputs");
        var tempModel = await RomLoader.Load(romPath);
        var gameCode = RomLoader.GetGameCode(tempModel);
        var gameName = gameCode switch
        {
            var c when c.StartsWith("BPRE") => "firered",
            var c when c.StartsWith("BPGE") => "leafgreen",
            var c when c.StartsWith("BPEE") => "emerald",
            var c when c.StartsWith("AXVE") => "ruby",
            var c when c.StartsWith("AXPE") => "sapphire",
            _ => "pokemon"
        };
        var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        var outputPath = Path.Combine("outputs", $"{gameName}_cn_{timestamp}.gba");

        // 复制 ROM，记录原始大小
        Console.Error.WriteLine($"Copying ROM: {romPath} → {outputPath}");
        File.Copy(romPath, outputPath, overwrite: true);
        var prePatachSize = (int)new FileInfo(outputPath).Length;

        // 应用中文字库补丁
        var projectRoot = FindProjectRoot();
        var fontPatchDir = Path.Combine(projectRoot, "Pokemon_GBA_Font_Patch", "pokeFRLG");
        var charmapPath = Path.Combine(fontPatchDir, "PMRSEFRLG_charmap.txt");
        var armipsPath = Path.Combine(projectRoot, "tools", "armips");

        if (File.Exists(armipsPath) && Directory.Exists(fontPatchDir))
        {
            Console.Error.WriteLine("Applying Chinese font patch...");
            ApplyFontPatch(outputPath, fontPatchDir, armipsPath);
            Console.Error.WriteLine("Font patch applied.");
        }
        else
        {
            Console.Error.WriteLine("Warning: Font patch or armips not found, skipping font patch.");
        }

        // 扩展 ROM 到 32MB
        TextWriter.ExpandRomStatic(outputPath);

        // 找到空闲空间起始地址：从 ROM 末尾向前扫描，跳过 0xFF 填充
        var freeSpaceStart = FindFreeSpaceStart(outputPath, prePatachSize);
        Console.Error.WriteLine($"Free space starts at: 0x{freeSpaceStart:X} ({(0x2000000 - freeSpaceStart) / 1024}KB available)");

        // 重新加载扩展后的 ROM
        Console.Error.WriteLine($"Loading expanded ROM: {outputPath}");
        var expandedModel = await RomLoader.Load(outputPath);
        Console.Error.WriteLine($"ROM loaded. Game code: {RomLoader.GetGameCode(expandedModel)}");

        // 应用翻译
        var expandedWriter = new TextWriter(expandedModel, freeSpaceStart, charmapPath);
        var written = expandedWriter.ApplyTranslations(translationsPath);

        if (written > 0)
        {
            Console.Error.WriteLine($"Saving ROM: {outputPath}");
            await RomLoader.Save(expandedModel, outputPath);
            Console.Error.WriteLine($"Done! Applied {written} translations → {outputPath}");
        }
        else
        {
            Console.Error.WriteLine("No translations were applied");
            return 1;
        }

        return 0;
    }

    private static void PrintUsage()
    {
        Console.Error.WriteLine("Meowth GBA Translator - Three-stage pipeline");
        Console.Error.WriteLine("");
        Console.Error.WriteLine("Usage:");
        Console.Error.WriteLine("  MeowthBridge extract <rom.gba>              → work/text.json");
        Console.Error.WriteLine("  MeowthBridge translate [options]             → work/text_translated.json");
        Console.Error.WriteLine("  MeowthBridge apply <rom.gba>                → outputs/{game}_cn_{timestamp}.gba");
        Console.Error.WriteLine("");
        Console.Error.WriteLine("Translate options:");
        Console.Error.WriteLine("  --api-key KEY    API key (or env DEEPSEEK_API_KEY)");
        Console.Error.WriteLine("  --api-url URL    API endpoint");
        Console.Error.WriteLine("  --model MODEL    Model name");
        Console.Error.WriteLine("  --batch SIZE     Batch size (default: 30)");
        Console.Error.WriteLine("  --delay MS       Delay between batches (default: 500)");
    }

    private static int PrintUnknownCommand(string command)
    {
        Console.Error.WriteLine($"Unknown command: {command}");
        PrintUsage();
        return 1;
    }

    private static string FindProjectRoot()
    {
        var dir = Directory.GetCurrentDirectory();
        while (dir != null)
        {
            if (Directory.Exists(Path.Combine(dir, "Pokemon_GBA_Font_Patch")))
                return dir;
            dir = Directory.GetParent(dir)?.FullName;
        }
        return Directory.GetCurrentDirectory();
    }

    /// <summary>
    /// 找到空闲空间的范围。字库补丁把字体数据写在 ROM 末尾（高地址），
    /// 中间区域（原始 ROM 结尾到字体数据之前）全是 0x00，可以用来存放翻译文本。
    /// 从 ROM 末尾向前扫描，跳过非空字节，找到字体数据的起始位置。
    /// </summary>
    private static int FindFreeSpaceStart(string romPath, int prePatchSize)
    {
        var data = File.ReadAllBytes(romPath);

        // 从末尾向前扫描，找到字体数据区域的起始位置
        // 字体数据在 ROM 末尾，包含非 0x00 的字节
        int fontDataStart = data.Length;
        for (int i = data.Length - 1; i >= prePatchSize; i--)
        {
            if (data[i] != 0x00 && data[i] != 0xFF)
            {
                fontDataStart = i + 1;
                // 继续向前扫描，找到连续空闲区域的边界
                // （字体数据内部可能有 0x00 字节）
                continue;
            }
            // 找到一大段空闲区域（连续 256 字节全是 0x00），说明到了空闲区
            if (i + 256 < fontDataStart)
            {
                bool allEmpty = true;
                for (int j = i; j < i + 256 && j < fontDataStart; j++)
                {
                    if (data[j] != 0x00 && data[j] != 0xFF)
                    {
                        allEmpty = false;
                        break;
                    }
                }
                if (allEmpty)
                {
                    // 找到了空闲区域和字体数据的边界
                    // 从 i 向后找到第一个非空字节就是字体数据起始
                    for (int j = i; j < data.Length; j++)
                    {
                        if (data[j] != 0x00 && data[j] != 0xFF)
                        {
                            fontDataStart = j;
                            break;
                        }
                    }
                    break;
                }
            }
        }

        // 空闲空间从原始 ROM 大小开始，到字体数据之前
        // 留 16 字节安全间隔，对齐到 4 字节
        var freeEnd = fontDataStart - 16;
        Console.Error.WriteLine($"Font data at: 0x{fontDataStart:X}, free space: 0x{prePatchSize:X} - 0x{freeEnd:X} ({(freeEnd - prePatchSize) / 1024}KB)");

        return prePatchSize;
    }

    private static void ApplyFontPatch(string romPath, string fontPatchDir, string armipsPath)
    {
        var baserom = Path.Combine(fontPatchDir, "baserom_FR.gba");
        var patched = Path.Combine(fontPatchDir, "chsfontrom_FR.gba");
        var asmFile = Path.Combine(fontPatchDir, "main_FR.asm");

        // 复制 ROM 到字库补丁目录
        File.Copy(romPath, baserom, overwrite: true);

        // 运行 armips
        var psi = new ProcessStartInfo
        {
            FileName = armipsPath,
            Arguments = $"\"{asmFile}\"",
            WorkingDirectory = fontPatchDir,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false
        };

        using var process = Process.Start(psi)!;
        process.WaitForExit();

        if (process.ExitCode != 0)
        {
            var stderr = process.StandardError.ReadToEnd();
            var stdout = process.StandardOutput.ReadToEnd();
            throw new Exception($"armips failed (exit {process.ExitCode}):\n{stderr}\n{stdout}");
        }

        if (!File.Exists(patched))
            throw new Exception($"Font patch output not found: {patched}");

        // 复制补丁后的 ROM 回输出路径
        File.Copy(patched, romPath, overwrite: true);

        // 清理临时文件
        if (File.Exists(baserom)) File.Delete(baserom);
        if (File.Exists(patched)) File.Delete(patched);
    }
}
