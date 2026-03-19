using System.Text.RegularExpressions;

namespace MeowthBridge;

/// <summary>
/// Decomp 改版（重编译工程）字库补丁器
/// 参考 gui_related/font_patch.py 的 RecompilaciónEmeraldfontPatch 实现
/// </summary>
public class DecompFontPatcher
{
    private readonly string _romPath;
    private byte[] _romData;

    public DecompFontPatcher(string romPath)
    {
        _romPath = romPath;
        _romData = File.ReadAllBytes(romPath);
    }

    /// <summary>
    /// 检测 ROM 版本
    /// </summary>
    public static string DetectVersion(string romPath)
    {
        using var fs = new FileStream(romPath, FileMode.Open, FileAccess.Read);
        var header = new byte[0xC0];
        fs.Read(header, 0, header.Length);

        var title = System.Text.Encoding.ASCII.GetString(header, 0xA0, 12);
        var gameCode = System.Text.Encoding.ASCII.GetString(header, 0xAC, 4);

        // 验证 header checksum（0xA0-0xBC 的校验和）
        byte checksum = 0;
        for (int i = 0xA0; i < 0xBD; i++)
            checksum = (byte)(checksum - header[i] - 1);
        bool isVanilla = checksum == header[0xBD];

        if (gameCode == "BPEE")
            return isVanilla ? "美版绿宝石" : "重编译工程美版绿宝石";
        if (gameCode == "BPRE")
            return isVanilla ? "美版火红" : "重编译工程美版火红";
        if (gameCode == "BPGE")
            return "叶绿";
        if (gameCode == "AXVE")
            return "红宝石";
        if (gameCode == "AXPE")
            return "蓝宝石";

        return "未知版本";
    }

    /// <summary>
    /// 应用 Decomp 绿宝石字库补丁
    /// </summary>
    public void ApplyDecompEmeraldPatch()
    {
        Console.Error.WriteLine("Applying Decomp Emerald font patch...");

        // Step 1: 定位 text 函数入口
        var step1Pattern = HexStringToBytes("3068037801303060181cf838072800d9");
        var step1Addresses = FindPattern(step1Pattern);

        int step1Address;
        if (step1Addresses.Count > 0 && step1Addresses[0] <= 0xFFFF)
        {
            step1Address = step1Addresses[0];
        }
        else
        {
            // 备用方案
            var altPattern = HexStringToBytes("0003707fb077");
            var altAddresses = FindPattern(altPattern);
            step1Address = altAddresses[0] + 6;
        }

        Console.Error.WriteLine($"  Text function entry: 0x{step1Address:X}");

        // Step 2: 定位字库数据位置
        var step2Pattern = HexStringToBytes("f0d6b0fdf0ffb0d5606a606f606f606f000000000000000000000000000000006055606a606f606fa0aff0fff0ff000000000000000000000000000000000000b0f5f0dbf0ff6055a06af06ff06fb05500000000000000000000000000000000b06af06ff06f6055a0aaf0fff0ff000000000000000000000000000000000000f0f6b0ddf0ff6055a06af06ff06fb05500000000000000000000000000000000b06af06ff06f6055a0aaf0fff0ff000000000000000000000000000000000000606fa0aff0ff6055a06af06ff06fb05500000000000000000000000000000000b06af06ff06f6055a0aaf0fff0ff000000000000000000000000000000000000f0d6b0fdf0ff6055a0a6f0f6f0f6f0f600000000000000000000000000000000f0f6f0f6f0f66055a0aaf0fff0ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000f0f6b0ddf0ff6055a0a6f0f6f0f6f0f600000000000000000000000000000000f0f6f0f6f0f66055a0aaf0fff0ff000000000000000000000000000000000000606fa0aff0ff6055a0a6f0f6f0f6f0f600000000000000000000000000000000f0f6f0f6f0f66055a0aaf0fff0ff000000000000000000000000000000000000f0d6b0fdf0ffb0d5606a606f606f606f00000000000000000000000000000000606f606f606fa095b0eaf0ff0000000000000000000000000000000000000000b0f5f0dbf0ffb0d5606a606f606f606f00000000000000000000000000000000606f606f606fa095b0eaf0ff0000000000000000000000000000000000000000f0f6b0ddf0ffb0d5606a606f606f606f00000000000000000000000000000000606f606f606fa095b0eaf0ff0000000000000000000000000000000000000000ffffffffffff56d66a696f6e6f6f566f000000000000000000000000000000006a6f6f6f6f6d5696aaebffffffff000000000000000000000000000000000000f0d6b0fdf0ff606f606f606f606f606f00000000000000000000000000000000606f606f606fa095b0eaf0fff0ff000000000000000000000000000000000000b0f5f0dbf0ff606f606f606f606f606f00000000000000000000000000000000606f606f606fa095b0eaf0fff0ff000000000000000000000000000000000000f0f6b0ddf0ff606f606f606f606f606f00000000000000000000000000000000606f606f606fa095b0eaf0fff0ff000000000000000000000000000000000000d0d6606df0ff606f605b605b60666066000000000000000000000000000000006069606d606e606fa0aff0fff0ff000000000000000000000000000000000000f0fff0fff0fff056b069b06db06df05600000000000000000000000000000000b069606ea06db06ef0aff0fff0ff000000000000000000000000000000000000f0fff0fff0fff0d6b0fdf0ffb0d560ea0000000000000000000000000000000060d5606a606f6095a0eaf0fff0ff000000000000000000000000000000000000f0fff0fff0ffb0f5f0dbf0ffb0d560ea0000000000000000000000000000000060d5606a606f6095a0eaf0fff0ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000f0fff0fff0fff0fff0fff0ffb0d5606a00000000000000000000000000000000f06f606fa095f0e6b0f9b0d6f0ea000000000000000000000000000000000000f0fff0fff0fff0d6b0fdf0ffb0d5606a000000000000000000000000000000006055b06a606fa095b0eaf0fff0ff000000000000000000000000000000000000f0fff0fff0ffb0f5f0dbf0ffb0d5606a000000000000000000000000000000006055b06a606fa095b0eaf0fff0ff000000000000000000000000000000000000f0fff0fff0fff0f6b0ddf0ffb0d5606a000000000000000000000000000000006055b06a606fa095b0eaf0fff0ff000000000000000000000000000000000000f0fff0fff0ff606fa0aff0ffb0d5606a000000000000000000000000000000006055b06a606fa095b0eaf0fff0ff000000000000000000000000000000000000f0fff0fff0fff0d6b0fdf0fff0f6f0f600000000000000000000000000000000f0f6f0f6f0f6f0f6f0faf0fff0ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000f0fff0fff0fff0f6b0ddf0fff0f6f0f600000000000000000000000000000000f0f6f0f6f0f6f0f6f0faf0fff0ff000000000000000000000000000000000000f0fff0fff0ff606fa0aff0fff0f6f0f600000000000000000000000000000000f0f6f0f6f0f6f0f6f0faf0fff0ff000000000000000000000000000000000000f0fff0fff0fff0d6b0fdf0ffb0d5606a00000000000000000000000000000000606f606f606fa095b0eaf0fff0ff000000000000000000000000000000000000f0fff0fff0ffb0f5f0dbf0ffb0d5606a00000000000000000000000000000000606f606f606fa095b0eaf0fff0ff000000000000000000000000000000000000f0fff0fff0fff0f6b0ddf0ffb0d5606a00000000000000000000000000000000606f606f606fa095b0eaf0fff0ff000000000000000000000000000000000000ffffffffffffffffffffffff5bd6a66900000000000000000000000000000000566dab6db66d5a96abebffffffff000000000000000000000000000000000000f0fff0fff0fff0d6b0fdf0ff606f606f00000000000000000000000000000000606f606f606f6095a0eaf0fff0ff000000000000000000000000000000000000f0fff0fff0ffb0f5f0dbf0ff606f606f00000000000000000000000000000000606f606f606f6095a0eaf0fff0ff000000000000000000000000000000000000f0fff0fff0fff0f6b0ddf0ff606f606f00000000000000000000000000000000606f606f606f6095a0eaf0fff0ff000000000000000000000000000000000000f0fff0fff0ffd0d6606df0ffb055606a00000000000000000000000000000000606f606f606f606fa0aff0fff0ff000000000000000000000000000000000000f0ffb0d5606a606f606fa095b0eaf0ff00000000000000000000000000000000f0fff0fff0fff0fff0fff0fff0ff000000000000000000000000000000000000f0ffb0d5b069b06db06d6096a0ebf0ff00000000000000000000000000000000f0fff0fff0fff0fff0fff0fff0ff000000000000000000000000000000000000ffffd9d696699a55db6a9b95ebeaffff00c00080008000c000c000c000c000c0ffffffffffffffffffffffffffff000000c000c000c000c000c000c000c00000fcfffcfffcfffcf6bcd9bcd9fce66cf600000000000000000000000000000000acd9bc69bc6d6c96acebfcfffcff000000000000000000000000000000000000f0fff0fff0fff0fff0fff0f6f0f6605500000000000000000000000000000000a0a6f0f6f0faf0fff0fff0fff0ff0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000ffffffffffffffffffffff6fff6fff6f00f000f000f000f000f000f000f000f0d96fd96fd96fa655baaaffffffff000000b000b000b000b000f000f000f00000ffffffffffffffffffffffff5bd5abea00000000000000000000000000000000ffff5bd5abeaffffffffffffffff000000000000000000000000000000000000ffffffffffffffffffffffffffffffd7ffffffffffffffffffffffffffffffffffd6ffeaffd7ffe6ffdaffebffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7ffd9ff6dbf66bf9affeffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff55d5ffffffffffffffffffffffffffffff5faaeaffffffffffffffffffffffffffffffabfffffffffffffffffffffffffffffffffffffffffffffffffffffff55fdaffffffffffffffffffffffffffdfff6ba56bfaafffffffffffffffffffffffffffafffbffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd7ffe5fff9bffebffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd7ffd6ffe6ffdaffebfffffffffffffffffffffffffffffffffffffffffffffffffffdbffdbffdbffdbffdbffdffffffffffffffffffffffffffffffffbffefffdbffdbffeffffffffffffffffffffffffffffffffffffffffffffffffffffffff7ff59fdadbdb6bebaffdbffdffffffffffffffffffffffffffffffffbffdbffefffdbffdbffeffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd7ffffffffffffffffffffffffffffffffffd6ffeaffd7ffd6ffeaffffffffffffffffffffffffffffffffffffffffffff");
        var step2Addresses = FindPattern(step2Pattern);
        var step2Address = step2Addresses[0];
        var step2Ptr = IntToPointer(step2Address);

        Console.Error.WriteLine($"  Font data location: 0x{step2Address:X}");

        // Step 3: 查找字库空间
        var step3Address = FindFreeSpace(0xED788);
        if (step3Address == -1)
        {
            step3Address = FindFreeSpace(0x80008);
            Console.Error.WriteLine("  Using half font size");
        }
        else
        {
            Console.Error.WriteLine("  Using full font size");
        }

        step3Address = AlignTo4(step3Address) + 4;
        var step3Ptr1 = IntToPointer(step3Address);
        var step3Ptr2 = IntToPointer(step3Address + 0x80000);

        Console.Error.WriteLine($"  Font space: 0x{step3Address:X}");

        // Step 4: 定位补丁位置
        var sitelist = new int[4];

        var site0Pattern = HexStringToBytes("80000149401800688746");
        var site0Addresses = FindPattern(site0Pattern);
        sitelist[0] = site0Addresses[3];

        var site1Pattern = HexStringToBytes("80000149401800688746");
        var site1Regex = new Regex("80000149401800688746" + string.Concat(Enumerable.Repeat(".{4}0008", 9)));
        var site1Matches = FindPatternRegex(site1Regex);
        sitelist[1] = site1Matches[3] - 10;

        var site2Pattern = HexStringToBytes("e0301c21300178");
        var site2Addresses = FindPattern(site2Pattern);
        sitelist[2] = site2Addresses[1];

        var site3Pattern = HexStringToBytes("0e180b4c0b481818");
        var site3Addresses = FindPattern(site3Pattern);
        sitelist[3] = site3Addresses[1];

        Console.Error.WriteLine($"  Patch sites: {string.Join(", ", sitelist.Select(s => $"0x{s:X}"))}");

        // 写入补丁
        var step1Write = HexStringToBytes("3068014b9f460000" + step2Ptr + "072800d9");
        WriteBytes(step1Address, step1Write);

        var step2Write = BuildStep2Data(sitelist, step3Ptr1, step3Ptr2);
        WriteBytes(step2Address, step2Write);

        // 写入字库数据
        var fontData = LoadFontData("绿宝石字库.bin");
        WriteBytes(step3Address, fontData);

        // 应用额外补丁
        ApplyExtraPatches();

        Console.Error.WriteLine("Decomp Emerald font patch applied successfully");
    }

    private byte[] BuildStep2Data(int[] sitelist, string ptr1, string ptr2)
    {
        var hex = "3068037801303060181c" +
                  "1e2804dc002802d0062800d031e0f838072800d901e004498f460448874606282adc00e00138013803e0" +
                  IntToPointer(sitelist[0]) + IntToPointer(sitelist[1]) +
                  "01023068037801303060591807488646f0b5890125682d072d0f002d0ad00126004801e0" +
                  ptr1 + "014ca746" +
                  IntToPointer(sitelist[2]) + IntToPointer(sitelist[3]) +
                  "02260148f6e70000" + ptr2 +
                  "1b28cbd0d2e71b28d3d90138d1e7";

        return HexStringToBytes(hex);
    }

    private void ApplyExtraPatches()
    {
        // Patch 1
        try
        {
            var pattern1 = HexStringToBytes("00000000030606");
            var addresses1 = FindPattern(pattern1);
            if (addresses1.Count > 0)
            {
                WriteBytes(addresses1[0], HexStringToBytes("00000000030c0a"));
                Console.Error.WriteLine($"  Extra patch 1 applied at 0x{addresses1[0]:X}");
            }
        }
        catch { Console.Error.WriteLine("  Extra patch 1 failed"); }

        // Patch 2
        try
        {
            var pattern2 = HexStringToBytes("00000000030606");
            var addresses2 = FindPattern(pattern2);
            if (addresses2.Count > 1)
            {
                WriteBytes(addresses2[1], HexStringToBytes("00000000030c0a"));
                Console.Error.WriteLine($"  Extra patch 2 applied at 0x{addresses2[1]:X}");
            }
        }
        catch { Console.Error.WriteLine("  Extra patch 2 failed"); }
    }

    private byte[] LoadFontData(string filename)
    {
        var projectRoot = FindProjectRoot();
        var fontPath = Path.Combine(projectRoot, "gui_related", "settings", filename);

        if (!File.Exists(fontPath))
        {
            throw new FileNotFoundException($"Font data not found: {fontPath}");
        }

        return File.ReadAllBytes(fontPath);
    }

    private static string FindProjectRoot()
    {
        var current = Directory.GetCurrentDirectory();
        while (current != null)
        {
            if (File.Exists(Path.Combine(current, "Meowth.sln")))
                return current;
            current = Directory.GetParent(current)?.FullName;
        }
        throw new DirectoryNotFoundException("Project root not found");
    }

    private List<int> FindPattern(byte[] pattern)
    {
        var results = new List<int>();
        for (int i = 0; i <= _romData.Length - pattern.Length; i++)
        {
            bool match = true;
            for (int j = 0; j < pattern.Length; j++)
            {
                if (_romData[i + j] != pattern[j])
                {
                    match = false;
                    break;
                }
            }
            if (match)
            {
                results.Add(i);
            }
        }
        return results;
    }

    private List<int> FindPatternRegex(Regex regex)
    {
        var hexString = BitConverter.ToString(_romData).Replace("-", "").ToLower();
        var matches = regex.Matches(hexString);
        return matches.Select(m => m.Index / 2).ToList();
    }

    private int FindFreeSpace(int requiredSize)
    {
        var ffPattern = new byte[requiredSize];
        Array.Fill(ffPattern, (byte)0xFF);

        var addresses = FindPattern(ffPattern);
        return addresses.Count > 0 ? addresses[0] : -1;
    }

    private int AlignTo4(int address)
    {
        return address + (4 - address % 4) % 4;
    }

    private string IntToPointer(int address)
    {
        var bankByte = address >= 0x1000000 ? 0x09 : 0x08;
        return $"{address & 0xFF:X2}{(address >> 8) & 0xFF:X2}{(address >> 16) & 0xFF:X2}{bankByte:X2}";
    }

    private void WriteBytes(int address, byte[] data)
    {
        Array.Copy(data, 0, _romData, address, data.Length);
    }

    private static byte[] HexStringToBytes(string hex)
    {
        hex = hex.Replace(" ", "").Replace("-", "");
        var bytes = new byte[hex.Length / 2];
        for (int i = 0; i < bytes.Length; i++)
        {
            bytes[i] = Convert.ToByte(hex.Substring(i * 2, 2), 16);
        }
        return bytes;
    }

    public void Save()
    {
        File.WriteAllBytes(_romPath, _romData);
    }
}
