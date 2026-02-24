using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace MeowthBridge;

public class FakeTranslator
{
    /// <summary>
    /// 假翻译：只翻译符合"空格+单词+空格"模式的单词
    /// 规则：
    /// 1. 单词必须前后都有空格（或在行首/行尾）
    /// 2. 单词只包含大小写字母
    /// 3. 将��词的最后一个字母替换成 "2"
    /// 4. 保留中括号内的内容不变
    /// 例如: " Hello World " -> " Hell2 Worl2 "
    /// 例如: "[player] is here" -> "[player] i2 her2"
    /// </summary>
    public static string FakeTranslate(string text)
    {
        if (string.IsNullOrEmpty(text)) return text;

        // 移除引号
        var cleanText = text.Trim('"');
        if (string.IsNullOrEmpty(cleanText)) return text;

        // 使用正则表达式匹配：空格+纯字母单词+空格
        // (?<=\s|^) - 前面是空格或行首
        // ([a-zA-Z]{2,}) - 2个或以上的字母
        // (?=\s|$) - 后面是空格或行尾
        var result = Regex.Replace(cleanText, @"(?<=\s|^)([a-zA-Z]{2,})(?=\s|$)", match =>
        {
            var word = match.Value;
            // 将最后一个字母替换成 "2"
            return word.Substring(0, word.Length - 1) + "2";
        });

        // 如果原文有引号，保留引号
        if (text.StartsWith("\"") && text.EndsWith("\""))
        {
            return $"\"{result}\"";
        }

        return result;
    }

    public static void TranslateJsonFile(string inputPath, string outputPath)
    {
        Console.Error.WriteLine($"Reading: {inputPath}");
        var json = File.ReadAllText(inputPath);

        var options = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            WriteIndented = true,
            DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull
        };

        var data = JsonSerializer.Deserialize<OutputData>(json, options);
        if (data == null || data.Entries == null)
        {
            Console.Error.WriteLine("Failed to parse JSON");
            return;
        }

        Console.Error.WriteLine($"Translating {data.Entries.Count} entries...");
        int count = 0;
        foreach (var entry in data.Entries)
        {
            entry.Translated = FakeTranslate(entry.Original);
            count++;
            if (count % 500 == 0)
            {
                Console.Error.WriteLine($"  Processed {count}/{data.Entries.Count}");
            }
        }

        Console.Error.WriteLine($"Writing: {outputPath}");
        var outputJson = JsonSerializer.Serialize(data, options);
        File.WriteAllText(outputPath, outputJson);

        Console.Error.WriteLine($"Done! Translated {count} entries");
    }
}
