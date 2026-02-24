using HavenSoft.HexManiac.Core;
using HavenSoft.HexManiac.Core.Models;

namespace MeowthBridge;

public static class RomLoader
{
    public static async Task<HardcodeTablesModel> Load(string romPath)
    {
        var data = File.ReadAllBytes(romPath);
        var singletons = new Singletons();
        var model = new HardcodeTablesModel(singletons, data);
        await model.InitializationWorkload;
        return model;
    }

    public static async Task Save(IDataModel model, string outputPath)
    {
        // 等待所有待处理的工作完成
        if (model is HardcodeTablesModel htModel)
        {
            await htModel.InitializationWorkload;
        }

        // 保存 ROM 数据
        File.WriteAllBytes(outputPath, model.RawData.ToArray());
    }

    public static string GetGameCode(IDataModel model)
    {
        // GBA game code is at offset 0xAC, 4 bytes + version byte at 0xBC
        var code = "";
        for (int i = 0xAC; i < 0xB0; i++)
            code += (char)model.RawData[i];
        code += model.RawData[0xBC].ToString();
        return code;
    }
}
