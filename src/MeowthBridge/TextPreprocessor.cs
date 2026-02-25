using System.Text;
using System.Text.RegularExpressions;

namespace MeowthBridge;

/// <summary>
/// 三明治结构的预处理和后处理：
/// 原文 → [预处理] → 干净文本 → [AI翻译] → 翻译结果 → [后处理] → 最终翻译
/// </summary>
public static class TextPreprocessor
{
    // 控制码正则：匹配 [xxx] 格式的所有控制码
    private static readonly Regex ControlCodeRegex = new(@"\[([a-zA-Z_][a-zA-Z0-9_]*)\]", RegexOptions.Compiled);

    // GBA 英文文本框宽度（字符数）。行可见长度 >= 此阈值的 75% 视为排版换行。
    private const int GbaLineWidth = 32;
    private const int SemanticThreshold = (int)(GbaLineWidth * 0.75); // 24

    // 用于计算可见长度时剥离的不可见控制码
    private static readonly Regex InvisibleRe = new(
        @"\\\.[plnr]|\[([a-zA-Z_]\w*)\]",
        RegexOptions.Compiled);

    /// <summary>
    /// 预处理：剥离引号、替换控制码为占位符、处理换行
    /// </summary>
    public static (string cleanText, Dictionary<string, string> codeMap) Preprocess(string text)
    {
        var codeMap = new Dictionary<string, string>();

        // 1. 剥离引号
        var clean = text;
        if (clean.StartsWith("\"") && clean.EndsWith("\""))
            clean = clean[1..^1];

        // 2. 处理换行符：区分语义换行和排版换行
        // \n\n → {PARA}（段落分隔/翻页）
        clean = clean.Replace("\n\n", "{PARA}");
        // 对剩余的单个 \n，判断前一行是否"顶到头了"
        // 短行（< 75% GBA宽度）后的 \n = 语义换行，保留为 {SEMNL}
        // 长行后的 \n = 排版换行，替换为空格
        clean = ClassifyNewlines(clean);

        // 3. 提取并替换控制码
        int codeIndex = 0;
        clean = ControlCodeRegex.Replace(clean, match =>
        {
            var original = match.Value; // e.g. [player]
            var placeholder = $"{{C{codeIndex}}}";
            codeMap[placeholder] = original;
            codeIndex++;
            return placeholder;
        });

        return (clean, codeMap);
    }

    /// <summary>
    /// 区分语义换行和排版换行。
    /// 短行（可见长度 < 阈值）后的 \n → {SEMNL}（语义换行，保留）
    /// 长行后的 \n → 空格（排版换行，去掉）
    /// </summary>
    private static string ClassifyNewlines(string text)
    {
        // {PARA} 已经替换好了，现在处理剩余的 \n
        var lines = text.Split('\n');
        if (lines.Length <= 1) return text;

        var sb = new StringBuilder();
        for (int i = 0; i < lines.Length; i++)
        {
            sb.Append(lines[i]);
            if (i < lines.Length - 1)
            {
                // 计算当前行的可见长度（去掉 {PARA} 和控制码）
                var cleanLine = lines[i].Replace("{PARA}", "");
                var visLen = VisibleLength(cleanLine);
                if (visLen < SemanticThreshold)
                    sb.Append("{SEMNL}"); // 语义换行
                else
                    sb.Append(' '); // 排版换行 → 空格
            }
        }
        return sb.ToString();
    }

    /// <summary>
    /// 计算一行文本的可见字符长度（剥离控制码）
    /// </summary>
    private static int VisibleLength(string line)
    {
        var stripped = InvisibleRe.Replace(line, "");
        return stripped.Length;
    }

    /// <summary>
    /// 后处理：还原控制码、还原段落分隔、自动换行、加回引号
    /// </summary>
    public static string Postprocess(string translated, Dictionary<string, string> codeMap)
    {
        // 0. 清除 LLM 可能自行插入的换行（语义换行是 {SEMNL}/{PARA}，其余都是 LLM 产物）
        var result = translated.Replace("\n", "");

        // 1. 还原控制码
        foreach (var (placeholder, original) in codeMap)
        {
            result = result.Replace(placeholder, original);
        }

        // 2. 还原段落分隔和语义换行
        result = result.Replace("{PARA}", "\n\n");
        result = result.Replace("{SEMNL}", "\n");

        // 3. 自动换行（按段落处理）
        //    每个段落内：先按语义换行拆段，每段 AutoWrap 成多行，
        //    然后把所有行按 2 行一页分配，用 \n 和 \p。
        var paragraphs = result.Split("\n\n");
        var wrappedParagraphs = new List<string>();
        foreach (var para in paragraphs)
        {
            var segments = para.Split('\n');
            var allLines = new List<string>();
            foreach (var seg in segments)
            {
                // AutoWrap 返回的文本用 \n 分行
                var wrapped = AutoWrap(seg);
                allLines.AddRange(wrapped.Split('\n'));
            }
            wrappedParagraphs.Add(DistributeLines(allLines, 2));
        }
        // 段落之间用 \p 翻页
        result = string.Join("\\p", wrappedParagraphs);

        // 4. 加回引号
        result = $"\"{result}\"";

        return result;
    }

    /// <summary>
    /// 把多行文本分配到 GBA 文本框：每 linesPerBox 行一页。
    /// 页内用 \n，页间用 \p。
    /// </summary>
    private static string DistributeLines(List<string> lines, int linesPerBox)
    {
        if (lines.Count == 0) return "";

        var sb = new StringBuilder();
        int lineInBox = 0;

        for (int i = 0; i < lines.Count; i++)
        {
            if (i > 0)
            {
                if (lineInBox >= linesPerBox)
                {
                    sb.Append("\\p");
                    lineInBox = 0;
                }
                else
                {
                    sb.Append("\\n");
                }
            }
            sb.Append(lines[i]);
            lineInBox++;
        }

        return sb.ToString();
    }

    /// <summary>
    /// 自动换行：按 16 宽度单位插入 \n
    /// 中文字符宽度=2，英文/数字/符号=1
    /// 控制码宽度按最大值计算（[player]=7 等）
    /// \. 宽度=0
    /// </summary>
    public static string AutoWrap(string text, int maxWidth = 32)
    {
        if (string.IsNullOrEmpty(text)) return text;

        var result = new StringBuilder();
        var currentWidth = 0;
        int i = 0;

        while (i < text.Length)
        {
            // 检查 \. 停顿标记（宽度=0）
            if (i + 1 < text.Length && text[i] == '\\' && text[i + 1] == '.')
            {
                result.Append("\\.");
                i += 2;
                continue;
            }

            // 检查 \p 翻页标记（宽度=0，但重置行宽）
            if (i + 1 < text.Length && text[i] == '\\' && text[i + 1] == 'p')
            {
                result.Append("\\p");
                currentWidth = 0;
                i += 2;
                continue;
            }

            // 检查控制码 [xxx]
            if (text[i] == '[')
            {
                var endBracket = text.IndexOf(']', i);
                if (endBracket > i)
                {
                    var code = text[i..(endBracket + 1)];
                    var codeWidth = GetControlCodeWidth(code);

                    if (currentWidth + codeWidth > maxWidth && currentWidth > 0)
                    {
                        result.Append('\n');
                        currentWidth = 0;
                    }

                    result.Append(code);
                    currentWidth += codeWidth;
                    i = endBracket + 1;
                    continue;
                }
            }

            var c = text[i];
            var charWidth = GetCharWidth(c);

            if (currentWidth + charWidth > maxWidth && currentWidth > 0)
            {
                result.Append('\n');
                currentWidth = 0;
            }

            result.Append(c);
            currentWidth += charWidth;
            i++;
        }

        return result.ToString();
    }

    /// <summary>
    /// 验证控制码完整性，返回警告列表
    /// </summary>
    public static List<string> ValidateCodes(string original, string translated, Dictionary<string, string> codeMap)
    {
        var warnings = new List<string>();

        foreach (var (placeholder, code) in codeMap)
        {
            if (!translated.Contains(code))
            {
                warnings.Add($"Missing control code {code} in translation");
            }
        }

        var translatedCodes = ControlCodeRegex.Matches(translated);
        var originalCodes = ControlCodeRegex.Matches(original);
        var originalSet = new HashSet<string>(originalCodes.Select(m => m.Value));

        foreach (Match m in translatedCodes)
        {
            if (!originalSet.Contains(m.Value))
            {
                warnings.Add($"Extra control code {m.Value} in translation");
            }
        }

        return warnings;
    }

    private static int GetCharWidth(char c)
    {
        if (c >= 0x4E00 && c <= 0x9FFF) return 2;
        if (c >= 0x3400 && c <= 0x4DBF) return 2;
        if (c >= 0xF900 && c <= 0xFAFF) return 2;
        if (c >= 0x3040 && c <= 0x309F) return 2;
        if (c >= 0x30A0 && c <= 0x30FF) return 2;
        if (c >= 0xFF00 && c <= 0xFFEF) return 2;
        if (c >= 0x3000 && c <= 0x303F) return 2;
        return 1;
    }

    private static int GetControlCodeWidth(string code)
    {
        return code.ToLower() switch
        {
            "[player]" => 7,
            "[rival]" => 7,
            _ when code.StartsWith("[buffer") => 7,
            "[black]" or "[blue]" or "[red]" or "[green]" or "[white]" => 0,
            "[pause_music]" or "[resume_music]" => 0,
            _ => 7
        };
    }
}
