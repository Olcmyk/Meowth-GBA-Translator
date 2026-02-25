using HavenSoft.HexManiac.Core.Models;
using System.Text.Json;
using System.Text.Encodings.Web;

namespace MeowthBridge;

public class TextWriter
{
    private readonly IDataModel _model;
    private readonly ChsEncoder _encoder;
    private const int GBA_MAX_SIZE = 0x2000000; // 32MB
    private const int GBA_BANK_OFFSET = 0x08000000;
    private int _nextFreeAddress;

    public TextWriter(IDataModel model, int originalRomSize, string charmapPath)
    {
        _model = model;
        _encoder = new ChsEncoder(charmapPath);
        // 扩展区域从原始 ROM 大小开始（不是扩展后的 32MB）
        _nextFreeAddress = originalRomSize;
    }

    /// <summary>
    /// 扩展 ROM 到 32MB（如果当前小于 32MB）
    /// </summary>
    public static void ExpandRomStatic(string romPath)
    {
        var data = File.ReadAllBytes(romPath);
        if (data.Length >= GBA_MAX_SIZE) return;

        Console.Error.WriteLine($"Expanding ROM from {data.Length / 1024}KB to {GBA_MAX_SIZE / 1024}KB");
        var expanded = new byte[GBA_MAX_SIZE];
        Array.Copy(data, expanded, data.Length);
        // 用 0xFF 填充扩展区域
        for (int i = data.Length; i < GBA_MAX_SIZE; i++)
            expanded[i] = 0xFF;
        File.WriteAllBytes(romPath, expanded);
    }

    public int ApplyTranslations(string jsonPath)
    {
        Console.Error.WriteLine($"Reading translations from: {jsonPath}");
        var json = File.ReadAllText(jsonPath);

        var options = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
        };

        var data = JsonSerializer.Deserialize<OutputData>(json, options);
        if (data?.Entries == null)
        {
            Console.Error.WriteLine("Failed to parse JSON");
            return 0;
        }

        int written = 0, skipped = 0, redirected = 0;
        Console.Error.WriteLine($"Applying {data.Entries.Count} translations...");

        foreach (var entry in data.Entries)
        {
            if (string.IsNullOrEmpty(entry.Translated))
            {
                skipped++;
                continue;
            }

            int address = Convert.ToInt32(entry.Address.Substring(2), 16);
            var translatedText = entry.Translated.Trim('"');
            var pcsBytes = _encoder.Encode(translatedText);

            if (entry.IsPointerBased)
            {
                if (pcsBytes.Count <= entry.ByteLength)
                {
                    // 直接写入原地址
                    WritePcsBytes(address, pcsBytes, entry.ByteLength);
                }
                else
                {
                    // 写入扩展区域，重定向指针
                    int newAddress = AllocateSpace(pcsBytes.Count);
                    WritePcsBytes(newAddress, pcsBytes, pcsBytes.Count);

                    // 更新所有指针源
                    foreach (var ptrSrc in entry.PointerSources)
                    {
                        int ptrAddress = Convert.ToInt32(ptrSrc.Substring(2), 16);
                        WritePointer(ptrAddress, newAddress);
                    }
                    redirected++;
                }
            }
            else
            {
                // 表格内联文本：直接写入，截断到 byte_length
                var truncatedCount = Math.Min(pcsBytes.Count, entry.ByteLength);
                for (int i = 0; i < truncatedCount; i++)
                {
                    if (address + i >= _model.Count) break;
                    _model[address + i] = pcsBytes[i];
                }
                // 如果有剩余空间，用 0xFF 填充
                for (int i = truncatedCount; i < entry.ByteLength; i++)
                {
                    if (address + i >= _model.Count) break;
                    _model[address + i] = 0xFF;
                }
            }

            written++;
            if (written % 500 == 0)
                Console.Error.WriteLine($"  Written: {written}, Redirected: {redirected}, Skipped: {skipped}");
        }

        Console.Error.WriteLine($"\nCompleted: Written={written}, Redirected={redirected}, Skipped={skipped}");
        return written;
    }

    private void WritePcsBytes(int address, IReadOnlyList<byte> pcsBytes, int maxLength)
    {
        var limit = Math.Min(pcsBytes.Count, maxLength);
        for (int i = 0; i < limit; i++)
        {
            if (address + i >= _model.Count) break;
            _model[address + i] = pcsBytes[i];
        }
        // 用 0x00 填充剩余空间（字库补丁用 0x00 作为空闲标记）
        for (int i = limit; i < maxLength; i++)
        {
            if (address + i >= _model.Count) break;
            _model[address + i] = 0x00;
        }
    }

    private int AllocateSpace(int size)
    {
        int address = _nextFreeAddress;
        _nextFreeAddress += size;
        return address;
    }

    /// <summary>
    /// 写入 GBA 指针（地址 + 0x08000000，小端序 4 字节）
    /// </summary>
    private void WritePointer(int ptrAddress, int targetAddress)
    {
        int pointer = targetAddress + GBA_BANK_OFFSET;
        _model[ptrAddress + 0] = (byte)(pointer & 0xFF);
        _model[ptrAddress + 1] = (byte)((pointer >> 8) & 0xFF);
        _model[ptrAddress + 2] = (byte)((pointer >> 16) & 0xFF);
        _model[ptrAddress + 3] = (byte)((pointer >> 24) & 0xFF);
    }
}

