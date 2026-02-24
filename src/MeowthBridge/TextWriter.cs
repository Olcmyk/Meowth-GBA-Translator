using HavenSoft.HexManiac.Core.Models;
using HavenSoft.HexManiac.Core.Models.Runs;
using System.Text.Json;

namespace MeowthBridge;

public class TextWriter
{
    private readonly IDataModel _model;

    public TextWriter(IDataModel model)
    {
        _model = model;
    }

    public int ApplyTranslations(string jsonPath)
    {
        Console.Error.WriteLine($"Reading translations from: {jsonPath}");
        var json = File.ReadAllText(jsonPath);

        var options = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        };

        var data = JsonSerializer.Deserialize<OutputData>(json, options);
        if (data == null || data.Entries == null)
        {
            Console.Error.WriteLine("Failed to parse JSON");
            return 0;
        }

        int written = 0;
        int skipped = 0;
        int errors = 0;

        Console.Error.WriteLine($"Applying {data.Entries.Count} translations...");

        foreach (var entry in data.Entries)
        {
            // 跳过没有翻译的条目
            if (string.IsNullOrEmpty(entry.Translated))
            {
                skipped++;
                continue;
            }

            // 解析地址
            if (!entry.Address.StartsWith("0x"))
            {
                Console.Error.WriteLine($"Invalid address format: {entry.Address}");
                errors++;
                continue;
            }

            int address = Convert.ToInt32(entry.Address.Substring(2), 16);
            if (address < 0 || address >= _model.Count)
            {
                Console.Error.WriteLine($"Address out of range: {entry.Address}");
                errors++;
                continue;
            }

            try
            {
                // 移除引号
                var translatedText = entry.Translated.Trim('"');

                // 转换文本为 PCS 字节
                var pcsBytes = _model.TextConverter.Convert(translatedText, out var _);

                // 检查长度是否超出
                if (pcsBytes.Count > entry.ByteLength)
                {
                    Console.Error.WriteLine($"Warning: Translation too long for {entry.Id} at {entry.Address}");
                    Console.Error.WriteLine($"  Original length: {entry.ByteLength}, Translated length: {pcsBytes.Count}");
                    Console.Error.WriteLine($"  Text: {translatedText.Substring(0, Math.Min(50, translatedText.Length))}...");
                    errors++;
                    continue;
                }

                // 写入字节
                for (int i = 0; i < pcsBytes.Count; i++)
                {
                    _model[address + i] = pcsBytes[i];
                }

                // 如果翻译文本较短，用空格填充剩余空间（直到终止符 0xFF）
                for (int i = pcsBytes.Count; i < entry.ByteLength; i++)
                {
                    if (_model[address + i] == 0xFF) break; // 遇到终止符停止
                    _model[address + i] = 0x00; // 用空格填充
                }

                written++;

                if (written % 500 == 0)
                {
                    Console.Error.WriteLine($"  Written: {written}, Skipped: {skipped}, Errors: {errors}");
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Error writing {entry.Id} at {entry.Address}: {ex.Message}");
                errors++;
            }
        }

        Console.Error.WriteLine($"\nCompleted:");
        Console.Error.WriteLine($"  Written: {written}");
        Console.Error.WriteLine($"  Skipped: {skipped}");
        Console.Error.WriteLine($"  Errors: {errors}");

        return written;
    }
}
