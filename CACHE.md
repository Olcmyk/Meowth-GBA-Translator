# 缓存功能说明

## 功能特性

✅ **自动缓存**：翻译结果自动保存到 `work/cache/` 目录
✅ **智能读取**：重新运行时自动从缓存读取已翻译的文本
✅ **断点续传**：翻译中断后可以继续，不会重复翻译
✅ **节省费用**：避免重复调用 API，节省翻译费用

## 工作原理

1. **缓存键生成**：使用 MD5 哈希原文生成唯一的缓存键
2. **缓存存储**：每个翻译结果保存为 `work/cache/{md5}.txt`
3. **缓存读取**：翻译前先检查缓存，如果存在则直接使用
4. **缓存更新**：新翻译的结果自动保存到缓存

## 使用方法

### 正常翻译（自动使用缓存）

```bash
dotnet run --project src/MeowthBridge translate testgba/firered_extracted.json -o testgba/firered_cn.json
```

**输出示例**：
```
Reading: testgba/firered_extracted.json
Translating 4355 entries...
Batch size: 10, Delay: 1000ms
Cache directory: work/cache
  Processed 10/4355 (Requests: 10, Cache hits: 0, Tokens: 1234)
  Processed 20/4355 (Requests: 20, Cache hits: 0, Tokens: 2456)
  ...
```

### 中断后继续翻译

如果翻译过程中断（Ctrl+C 或网络错误），直接重新运行相同的命令：

```bash
dotnet run --project src/MeowthBridge translate testgba/firered_extracted.json -o testgba/firered_cn.json
```

程序会：
- ✅ 跳过已翻译的文本（从缓存读取）
- ✅ 只翻译未完成的文本
- ✅ 显示缓存命中次数

**输出示例**（续传）：
```
Reading: testgba/firered_extracted.json
Translating 4355 entries...
Batch size: 10, Delay: 1000ms
Cache directory: work/cache
  Processed 10/4355 (Requests: 0, Cache hits: 10, Tokens: 0)    ← 全部来自缓存
  Processed 20/4355 (Requests: 0, Cache hits: 20, Tokens: 0)    ← 全部来自缓存
  Processed 30/4355 (Requests: 5, Cache hits: 25, Tokens: 567)  ← 5个新翻译，25个缓存
  ...
```

### 清理缓存（重新翻译）

如果想要重新翻译所有文本：

```bash
# 删除缓存目录
rm -rf work/cache

# 重新翻译
dotnet run --project src/MeowthBridge translate testgba/firered_extracted.json -o testgba/firered_cn.json
```

### 查看缓存统计

```bash
# 查看缓存文件数量
ls work/cache | wc -l

# 查看缓存目录大小
du -sh work/cache
```

## 缓存文件格式

每个缓存文件：
- **文件名**：`{md5_hash}.txt`（原文的 MD5 哈希）
- **内容**：翻译后的文本（纯文本）
- **位置**：`work/cache/`

**示例**：
```
work/cache/
├── 5d41402abc4b2a76b9719d911017c592.txt  ← "Hello" 的翻译
├── 7d793037a0760186574b0282f2f435e7.txt  ← "World" 的翻译
└── ...
```

## 优势

### 1. 节省费用
- 重复文本只翻译一次
- 中断后不需要重新翻译已完成的部分
- 多次运行不会产生额外费用

### 2. 提高速度
- 缓存命中时无需等待 API 响应
- 大幅减少网络请求
- 批量翻译更快完成

### 3. 可靠性
- 翻译结果持久化保存
- 不怕程序崩溃或网络中断
- 随时可以继续未完成的翻译

## 注意事项

1. **缓存不会自动过期**：如果修改了翻译提示词或模型，需要手动清理缓存
2. **缓存基于原文**：修改原文后会生成新的缓存
3. **缓存目录**：默认为 `work/cache/`，会自动创建

## 完整示例

### 首次翻译

```bash
$ dotnet run --project src/MeowthBridge translate testgba/firered_extracted.json -o testgba/firered_cn.json

Reading: testgba/firered_extracted.json
Translating 4355 entries...
Batch size: 10, Delay: 1000ms
Cache directory: work/cache
  Processed 10/4355 (Requests: 10, Cache hits: 0, Tokens: 1234)
  Processed 20/4355 (Requests: 20, Cache hits: 0, Tokens: 2456)
  ...
  Processed 100/4355 (Requests: 100, Cache hits: 0, Tokens: 12345)
^C  ← 用户中断
```

### 继续翻译

```bash
$ dotnet run --project src/MeowthBridge translate testgba/firered_extracted.json -o testgba/firered_cn.json

Reading: testgba/firered_extracted.json
Translating 4355 entries...
Batch size: 10, Delay: 1000ms
Cache directory: work/cache
  Processed 10/4355 (Requests: 0, Cache hits: 10, Tokens: 0)     ← 从缓存读取
  Processed 20/4355 (Requests: 0, Cache hits: 20, Tokens: 0)     ← 从缓存读取
  ...
  Processed 100/4355 (Requests: 0, Cache hits: 100, Tokens: 0)   ← 从缓存读取
  Processed 110/4355 (Requests: 10, Cache hits: 100, Tokens: 1234) ← 继续新翻译
  ...
  Processed 4350/4355 (Requests: 4250, Cache hits: 100, Tokens: 98765)
Writing: testgba/firered_cn.json

Done!
  Total requests: 4250  ← 只调用了 4250 次 API（节省了 100 次）
  Cache hits: 100       ← 100 次从缓存读取
  Total tokens: 98765
  Translated: 4355 entries
  Cache saved to: work/cache
```

## 故障排除

### 问题：缓存文件太多

**解决**：定期清理旧缓存
```bash
# 删除 7 天前的缓存
find work/cache -name "*.txt" -mtime +7 -delete
```

### 问题：翻译质量不好，想重新翻译

**解决**：清理缓存后重新翻译
```bash
rm -rf work/cache
dotnet run --project src/MeowthBridge translate testgba/firered_extracted.json -o testgba/firered_cn.json
```

### 问题：缓存占用空间太大

**解决**：压缩缓存目录
```bash
tar -czf work/cache_backup.tar.gz work/cache
rm -rf work/cache
```
