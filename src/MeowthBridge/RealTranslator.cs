using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Encodings.Web;
using System.Net.Http;
using System.Text;
using System.Security.Cryptography;

namespace MeowthBridge;

public class RealTranslator
{
    private readonly HttpClient _httpClient;
    private readonly string _apiKey;
    private readonly string _apiUrl;
    private readonly string _model;
    private readonly string _cacheDir;
    private int _requestCount = 0;
    private int _totalTokens = 0;
    private int _cacheHits = 0;

    private const string SystemPrompt = @"你是一个专业的宝可梦游戏本地化翻译专家。请将以下宝可梦游戏的英文文本翻译成简体中文。

核心规则：
1. 控制码占位符（如 {C0}, {C1} 等）必须原样保留，不得修改、删除或增加
2. 占位符的数量和顺序必须与原文完全一致
3. 使用宝可梦官方简体中文译名
4. POKéMON / Pokémon 翻译为""宝可梦""
5. 保持游戏对话的自然口语风格
6. 只返回翻译结果，不要任何解释
7. 翻译时不要插入任何换行符，输出纯文本即可，系统会自动排版
8. 保留所有 \. 等待标记
9. 保留 {PARA} 段落分隔标记，原样输出
10. 保留 {SEMNL} 语义换行标记，原样输出
11. ""rival"" 翻译为""劲敌""，不要翻译为具体人名

多条文本用 ||| 分隔，请逐条翻译并用 ||| 分隔返回。";

    public RealTranslator(string apiKey, string apiUrl = "https://api.deepseek.com/v1/chat/completions", string model = "deepseek-chat")
    {
        _httpClient = new HttpClient();
        _apiKey = apiKey;
        _apiUrl = apiUrl;
        _model = model;
        _httpClient.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiKey}");
        _cacheDir = Path.Combine("work", "cache");
        Directory.CreateDirectory(_cacheDir);
    }

    private string GetCacheKey(string text)
    {
        using var md5 = MD5.Create();
        var hash = md5.ComputeHash(Encoding.UTF8.GetBytes(text));
        return BitConverter.ToString(hash).Replace("-", "").ToLower();
    }

    private string? GetFromCache(string text)
    {
        var cacheFile = Path.Combine(_cacheDir, $"{GetCacheKey(text)}.txt");
        if (File.Exists(cacheFile))
        {
            try { return CleanResponse(File.ReadAllText(cacheFile)); }
            catch { return null; }
        }
        return null;
    }

    private void SaveToCache(string originalText, string translatedText)
    {
        var cacheFile = Path.Combine(_cacheDir, $"{GetCacheKey(originalText)}.txt");
        try { File.WriteAllText(cacheFile, translatedText); }
        catch (Exception ex) { Console.Error.WriteLine($"Warning: cache save failed: {ex.Message}"); }
    }

    /// <summary>
    /// 批量翻译 API 调用：多条预处理后的文本用 ||| 分隔。
    /// 如果 LLM 返回的分割数量不匹配，回退到逐条翻译。
    /// </summary>
    private async Task<string[]> TranslateBatchAsync(string[] preprocessedTexts)
    {
        var joined = string.Join(" ||| ", preprocessedTexts);

        var translated = await CallApiAsync(joined);
        var parts = translated.Split("|||").Select(s => s.Trim()).ToArray();

        if (parts.Length == preprocessedTexts.Length)
            return parts;

        // 分割不匹配 — 逐条翻译
        Console.Error.WriteLine($"  Warning: batch split mismatch (expected {preprocessedTexts.Length}, got {parts.Length}), falling back to individual translation");
        var results = new string[preprocessedTexts.Length];
        for (int i = 0; i < preprocessedTexts.Length; i++)
        {
            results[i] = await CallApiAsync(preprocessedTexts[i]);
        }
        return results;
    }

    /// <summary>
    /// 单次 API 调用
    /// </summary>
    private async Task<string> CallApiAsync(string userContent)
    {
        var requestBody = new
        {
            model = _model,
            messages = new[]
            {
                new { role = "system", content = SystemPrompt },
                new { role = "user", content = userContent }
            },
            temperature = 0.3
        };

        var jsonContent = JsonSerializer.Serialize(requestBody);
        var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

        var response = await _httpClient.PostAsync(_apiUrl, content);
        response.EnsureSuccessStatusCode();

        var responseJson = await response.Content.ReadAsStringAsync();
        var result = JsonSerializer.Deserialize<OpenAIResponse>(responseJson);

        Interlocked.Increment(ref _requestCount);
        if (result?.Usage != null)
            Interlocked.Add(ref _totalTokens, result.Usage.TotalTokens);

        return CleanResponse(result?.Choices?[0]?.Message?.Content?.Trim() ?? userContent);
    }

    /// <summary>
    /// 清理 LLM 返回的多余内容（尾部 |||、前导解释文字等）
    /// </summary>
    private static string CleanResponse(string text)
    {
        // LLM 有时在单条翻译末尾也加 |||
        text = text.TrimEnd('|').TrimEnd();
        return text;
    }
    /// <summary>
    /// 三阶段翻译流水线：预处理 → 批量API翻译 → 后处理
    /// </summary>
    public async Task TranslateJsonFileAsync(string inputPath, string outputPath, int batchSize = 30, int delayMs = 500)
    {
        Console.Error.WriteLine($"Reading: {inputPath}");
        var json = File.ReadAllText(inputPath);

        var jsonOptions = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            WriteIndented = true,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
        };

        var data = JsonSerializer.Deserialize<OutputData>(json, jsonOptions);
        if (data?.Entries == null)
        {
            Console.Error.WriteLine("Failed to parse JSON");
            return;
        }

        Console.Error.WriteLine($"Translating {data.Entries.Count} entries (batch={batchSize}, delay={delayMs}ms)");

        // Phase 1: 预处理所有条目
        var preprocessed = new List<(int index, string cleanText, Dictionary<string, string> codeMap)>();
        var cachedResults = new Dictionary<int, string>(); // index → cached translation

        for (int i = 0; i < data.Entries.Count; i++)
        {
            var entry = data.Entries[i];
            var (cleanText, codeMap) = TextPreprocessor.Preprocess(entry.Original);

            // 检查缓存
            var cached = GetFromCache(cleanText);
            if (cached != null)
            {
                Interlocked.Increment(ref _cacheHits);
                var postprocessed = TextPreprocessor.Postprocess(cached, codeMap);
                cachedResults[i] = postprocessed;
            }
            else
            {
                preprocessed.Add((i, cleanText, codeMap));
            }
        }

        Console.Error.WriteLine($"  Cache hits: {_cacheHits}, Need translation: {preprocessed.Count}");

        // 应用缓存结果
        foreach (var (idx, translated) in cachedResults)
        {
            data.Entries[idx].Translated = translated;
        }

        // Phase 2: 批量翻译未缓存的条目
        int translated_count = 0;
        for (int batchStart = 0; batchStart < preprocessed.Count; batchStart += batchSize)
        {
            var batch = preprocessed.Skip(batchStart).Take(batchSize).ToList();
            var textsToTranslate = batch.Select(b => b.cleanText).ToArray();

            try
            {
                var results = await TranslateBatchAsync(textsToTranslate);

                // Phase 3: 后处理每条翻译结果
                for (int j = 0; j < batch.Count; j++)
                {
                    var (entryIndex, cleanText, codeMap) = batch[j];
                    var translatedText = results[j];

                    // 保存到缓存（预处理后的翻译结果）
                    SaveToCache(cleanText, translatedText);

                    // 后处理：还原控制码 + 自动换行 + 加引号
                    var final = TextPreprocessor.Postprocess(translatedText, codeMap);

                    // 验证控制码完整性
                    var warnings = TextPreprocessor.ValidateCodes(
                        data.Entries[entryIndex].Original, final, codeMap);
                    foreach (var w in warnings)
                        Console.Error.WriteLine($"  Warning [{data.Entries[entryIndex].Id}]: {w}");

                    data.Entries[entryIndex].Translated = final;
                    translated_count++;
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"  Batch error: {ex.Message}");
                // 失败的条目保留原文
                foreach (var (entryIndex, _, _) in batch)
                {
                    if (string.IsNullOrEmpty(data.Entries[entryIndex].Translated))
                        data.Entries[entryIndex].Translated = data.Entries[entryIndex].Original;
                }
            }

            Console.Error.WriteLine($"  Translated {translated_count}/{preprocessed.Count} (API calls: {_requestCount}, tokens: {_totalTokens})");

            if (batchStart + batchSize < preprocessed.Count)
                await Task.Delay(delayMs);
        }

        // 写出结果
        Console.Error.WriteLine($"Writing: {outputPath}");
        Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
        var outputJson = JsonSerializer.Serialize(data, jsonOptions);
        File.WriteAllText(outputPath, outputJson);

        Console.Error.WriteLine($"\nDone! API calls: {_requestCount}, Cache hits: {_cacheHits}, Tokens: {_totalTokens}");
    }

    // OpenAI API 响应模型
    private class OpenAIResponse
    {
        [JsonPropertyName("choices")]
        public Choice[]? Choices { get; set; }
        [JsonPropertyName("usage")]
        public Usage? Usage { get; set; }
    }

    private class Choice
    {
        [JsonPropertyName("message")]
        public Message? Message { get; set; }
    }

    private class Message
    {
        [JsonPropertyName("content")]
        public string? Content { get; set; }
    }

    private class Usage
    {
        [JsonPropertyName("total_tokens")]
        public int TotalTokens { get; set; }
    }
}


