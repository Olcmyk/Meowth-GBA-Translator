namespace MeowthBridge;

/// <summary>
/// 中文字库编码器：将翻译后的文本转换为 GBA ROM 字节序列。
/// 使用 Pokemon_GBA_Font_Patch 的 PMRSEFRLG_charmap.txt 字符映射。
/// 单字节：ASCII/PCS 字符（0x00-0xFF）
/// 双字节：中文字符（0x0100-0x1E5D）
/// </summary>
public class ChsEncoder
{
    private readonly Dictionary<char, byte[]> _charMap = new();
    private readonly Dictionary<string, byte[]> _macroMap = new();
    private readonly Dictionary<string, byte[]> _colorMap = new();

    public ChsEncoder(string charmapPath)
    {
        LoadCharmap(charmapPath);
        LoadMacros();
        LoadFallbacks();
    }

    private void LoadCharmap(string path)
    {
        foreach (var line in File.ReadAllLines(path))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            var eqIdx = line.IndexOf('=');
            if (eqIdx < 0) continue;

            var hexPart = line[..eqIdx].Trim();
            var charPart = line[(eqIdx + 1)..];

            // 跳过多字节宏定义（如 5354={PKMN}）和花括号标记
            if (hexPart.Length > 4) continue;
            if (charPart.StartsWith("{")) continue;

            if (!int.TryParse(hexPart, System.Globalization.NumberStyles.HexNumber, null, out int code))
                continue;

            if (charPart.Length == 1)
            {
                var ch = charPart[0];
                if (code <= 0xFF)
                    _charMap[ch] = new byte[] { (byte)code };
                else
                    _charMap[ch] = new byte[] { (byte)(code >> 8), (byte)(code & 0xFF) };
            }
            // 处理 armips 转义：\' → '
            else if (charPart == "\\'")
            {
                if (code <= 0xFF)
                    _charMap['\''] = new byte[] { (byte)code };
            }
        }
    }

    private void LoadMacros()
    {
        // FD 系列：变量替换
        _macroMap["[player]"] = new byte[] { 0xFD, 0x01 };
        _macroMap["[buffer1]"] = new byte[] { 0xFD, 0x02 };
        _macroMap["[buffer2]"] = new byte[] { 0xFD, 0x03 };
        _macroMap["[buffer3]"] = new byte[] { 0xFD, 0x04 };
        _macroMap["[rival]"] = new byte[] { 0xFD, 0x06 };

        // FC 系列：控制码
        _macroMap["[resetfont]"] = new byte[] { 0xFC, 0x07 };
        _macroMap["[pause]"] = new byte[] { 0xFC, 0x09 };
        _macroMap["[wait_sound]"] = new byte[] { 0xFC, 0x0A };
        _macroMap["[escape]"] = new byte[] { 0xFC, 0x0C };
        _macroMap["[shift_right]"] = new byte[] { 0xFC, 0x0D };
        _macroMap["[shift_down]"] = new byte[] { 0xFC, 0x0E };
        _macroMap["[fill_window]"] = new byte[] { 0xFC, 0x0F };
        _macroMap["[skip]"] = new byte[] { 0xFC, 0x12 };
        _macroMap["[japanese]"] = new byte[] { 0xFC, 0x15 };
        _macroMap["[latin]"] = new byte[] { 0xFC, 0x16 };
        _macroMap["[pause_music]"] = new byte[] { 0xFC, 0x17 };
        _macroMap["[resume_music]"] = new byte[] { 0xFC, 0x18 };

        // BPRE/BPGE 颜色码
        _colorMap["[white]"] = new byte[] { 0xFC, 0x01, 0x00 };
        _colorMap["[white2]"] = new byte[] { 0xFC, 0x01, 0x01 };
        _colorMap["[black]"] = new byte[] { 0xFC, 0x01, 0x02 };
        _colorMap["[grey]"] = new byte[] { 0xFC, 0x01, 0x03 };
        _colorMap["[gray]"] = new byte[] { 0xFC, 0x01, 0x03 };
        _colorMap["[red]"] = new byte[] { 0xFC, 0x01, 0x04 };
        _colorMap["[orange]"] = new byte[] { 0xFC, 0x01, 0x05 };
        _colorMap["[green]"] = new byte[] { 0xFC, 0x01, 0x06 };
        _colorMap["[lightgreen]"] = new byte[] { 0xFC, 0x01, 0x07 };
        _colorMap["[blue]"] = new byte[] { 0xFC, 0x01, 0x08 };
        _colorMap["[lightblue]"] = new byte[] { 0xFC, 0x01, 0x09 };
    }

    /// <summary>
    /// 添加回退映射：全角字符→半角、直引号→弯引号等
    /// 只在 charmap 中没有对应字符时才添加
    /// </summary>
    private void LoadFallbacks()
    {
        // 全角数字 → 半角数字
        for (int i = 0; i <= 9; i++)
            TryAddFallback((char)(0xFF10 + i), (char)('0' + i));

        // 全角大写字母 → 半角
        for (int i = 0; i < 26; i++)
            TryAddFallback((char)(0xFF21 + i), (char)('A' + i));

        // 全角小写字母 → 半角
        for (int i = 0; i < 26; i++)
            TryAddFallback((char)(0xFF41 + i), (char)('a' + i));

        // 全角标点 → 半角等价
        TryAddFallback('～', '~');   // U+FF5E → ~
        TryAddFallback('／', '/');   // U+FF0F → /
        TryAddFallback('（', '(');   // U+FF08
        TryAddFallback('）', ')');   // U+FF09
        TryAddFallback('＋', '+');   // U+FF0B
        TryAddFallback('＝', '=');   // U+FF1D
        TryAddFallback('＆', '&');   // U+FF06

        // 直引号 → 弯引号（charmap 有 B1=" B2="）
        TryAddFallback('"', '\u201C');  // " → "
        // 方括号 → 圆括号
        TryAddFallback('[', '(');
        TryAddFallback(']', ')');
        // 竖线 → 减号
        TryAddFallback('|', '-');

        // 破折号/长横线 → 减号
        TryAddFallback('\u2014', '-');  // — em dash
        TryAddFallback('\u2013', '-');  // – en dash
        // 书名号 → 尖括号（charmap 没有，用 < >）
        TryAddFallback('\u300A', '<');  // 《
        TryAddFallback('\u300B', '>');  // 》
        // 花括号 → 圆括号
        TryAddFallback('{', '(');
        TryAddFallback('}', ')');
        // 美元符号 → 空格
        TryAddFallback('$', ' ');
        // 星号 → 空格
        TryAddFallback('*', ' ');
        // œ → o（charmap 没有小写 œ）
        TryAddFallback('\u0153', 'o');
    }

    private void TryAddFallback(char from, char to)
    {
        if (!_charMap.ContainsKey(from) && _charMap.TryGetValue(to, out var bytes))
            _charMap[from] = bytes;
    }

    private static readonly Dictionary<string, byte> F9Macros = new()
    {
        ["[up]"] = 0x00, ["[down]"] = 0x01, ["[left]"] = 0x02, ["[right]"] = 0x03,
        ["[plus]"] = 0x04, ["[LV]"] = 0x05, ["[PP]"] = 0x06, ["[ID]"] = 0x07,
        ["[No]"] = 0x08, ["[_]"] = 0x09,
        ["[super_effective]"] = 0x15, ["[not_very_effective]"] = 0x16, ["[not_effective]"] = 0x17,
        ["[heart]"] = 0xE7, ["[moon]"] = 0xE8, ["[eighth_note]"] = 0xE9,
    };

    private static byte[]? TryEncodeF9Macro(string macro)
    {
        if (F9Macros.TryGetValue(macro, out var code))
            return new byte[] { 0xF9, code };
        return null;
    }

    /// <summary>
    /// 将翻译后的文本转换为 GBA ROM 字节序列（含 0xFF 终止符）
    /// </summary>
    public List<byte> Encode(string text)
    {
        var result = new List<byte>();
        int i = 0;

        while (i < text.Length)
        {
            // 1. 转义序列：\n \p \l \. \pk \mn 及其他 HexManiac 转义
            if (text[i] == '\\' && i + 1 < text.Length)
            {
                switch (text[i + 1])
                {
                    case 'n': result.Add(0xFE); i += 2; continue;
                    case 'p':
                        // \pk = 0x53
                        if (i + 2 < text.Length && text[i + 2] == 'k')
                        {
                            result.Add(0x53);
                            i += 3;
                            continue;
                        }
                        // \pn = 0xFB (paragraph feed)
                        if (i + 2 < text.Length && text[i + 2] == 'n')
                        {
                            result.Add(0xFB);
                            i += 3;
                            continue;
                        }
                        result.Add(0xFB); i += 2; continue;
                    case 'l': result.Add(0xFA); i += 2; continue;
                    case '.': result.Add(0xB0); i += 2; continue;
                    case 'm':
                        // \mn = 0x54
                        if (i + 2 < text.Length && text[i + 2] == 'n')
                        {
                            result.Add(0x54);
                            i += 3;
                            continue;
                        }
                        break;
                    case 'e': result.Add(0x2C); i += 2; continue;  // \e
                    case 'r': result.Add(0x48); i += 2; continue;  // \r (not carriage return)
                    case 'd': result.Add(0x84); i += 2; continue;  // \d
                    case '<': result.Add(0x85); i += 2; continue;  // \<
                    case '>': result.Add(0x86); i += 2; continue;  // \>
                    case '+': result.Add(0x2E); i += 2; continue;  // \+
                    case '\\':
                        // \\ = FD escape prefix (raw next byte)
                        result.Add(0xFD);
                        i += 2;
                        continue;
                    default:
                        // 未知转义，跳过反斜杠
                        i++;
                        continue;
                }
            }

            // 2. 真实换行符 → 0xFE
            if (text[i] == '\n')
            {
                result.Add(0xFE);
                i++;
                continue;
            }

            // 3. 宏/控制码：[player], [rival], [black] 等
            if (text[i] == '[')
            {
                var endBracket = text.IndexOf(']', i);
                if (endBracket > i)
                {
                    var macro = text[i..(endBracket + 1)];
                    if (_macroMap.TryGetValue(macro, out var macroBytes))
                    {
                        result.AddRange(macroBytes);
                        i = endBracket + 1;
                        continue;
                    }
                    if (_colorMap.TryGetValue(macro, out var colorBytes))
                    {
                        result.AddRange(colorBytes);
                        i = endBracket + 1;
                        continue;
                    }
                    // 未知宏，尝试作为 F9 特殊符号
                    var f9Bytes = TryEncodeF9Macro(macro);
                    if (f9Bytes != null)
                    {
                        result.AddRange(f9Bytes);
                        i = endBracket + 1;
                        continue;
                    }
                }
            }

            // 4. 查字符映射表
            var ch = text[i];
            if (_charMap.TryGetValue(ch, out var bytes))
            {
                result.AddRange(bytes);
            }
            else
            {
                // 未知字符，跳过并警告
                Console.Error.WriteLine($"  Warning: unknown char '{ch}' (U+{(int)ch:X4}), skipped");
            }
            i++;
        }

        // 终止符
        result.Add(0xFF);
        return result;
    }
}
