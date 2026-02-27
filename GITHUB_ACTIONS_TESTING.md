# GitHub Actions 测试指南

## 推送已完成 ✅

代码已成功推送到 GitHub：https://github.com/Olcmyk/Meowth-GBA-Translator

## 查看工作流运行状态

### 方法 1：通过 GitHub 网页界面

1. **访问 Actions 页面**
   ```
   https://github.com/Olcmyk/Meowth-GBA-Translator/actions
   ```

2. **查看运行中的工作流**
   - 左侧会显示所有工作流：
     - ✅ Tests（应该已经自动触发）
     - Build MeowthBridge
     - Publish to PyPI

3. **点击具体的工作流运行**
   - 可以看到每个 job 的状态
   - 点击 job 可以查看详细日志
   - 绿色 ✓ = 成功
   - 红色 ✗ = 失败
   - 黄色 ⊙ = 运行中

### 方法 2：使用 GitHub CLI（如果已安装）

```bash
# 查看最近的工作流运行
gh run list

# 查看特定工作流的运行状态
gh run view

# 实时查看日志
gh run watch
```

## 当前应该触发的工作流

根据我们的配置，推送到 main 分支后：

### ✅ Tests 工作流（应该自动运行）
- **触发条件**: `push` 到 `main` 分支
- **运行内容**:
  - 在 Ubuntu、macOS、Windows 上测试
  - Python 3.10、3.11、3.12
  - 构建 MeowthBridge
  - 测试二进制加载器
  - 测试 CLI 命令

**预期结果**:
- ✅ 所有平台和 Python 版本都应该通过
- 如果失败，查看日志找出原因

### ⚠️ Build MeowthBridge 工作流（不会自动运行）
- **触发条件**:
  - 修改 `src/MeowthBridge/**` 文件
  - 修改 `.github/workflows/build-csharp.yml`
  - 手动触发（workflow_dispatch）

**如何手动触发**:
1. 访问 https://github.com/Olcmyk/Meowth-GBA-Translator/actions/workflows/build-csharp.yml
2. 点击右上角 "Run workflow" 按钮
3. 选择分支（main）
4. 点击 "Run workflow"

### ⚠️ Publish to PyPI 工作流（不会自动运行）
- **触发条件**:
  - 创建 Release
  - 手动触发（workflow_dispatch）

**暂时不要运行这个**，因为：
- 需要先配置 PyPI 可信发布
- 需要先测试构建是否成功

## 测试步骤建议

### 第 1 步：等待 Tests 工作流完成（约 10-15 分钟）

访问：https://github.com/Olcmyk/Meowth-GBA-Translator/actions

**如果成功** ✅:
- 所有测试通过
- 说明代码在所有平台上都能正常工作
- 可以继续下一步

**如果失败** ❌:
- 点击失败的 job 查看日志
- 找出错误原因
- 修复后重新推送

### 第 2 步：手动触发 Build MeowthBridge 工作流

1. 访问 https://github.com/Olcmyk/Meowth-GBA-Translator/actions/workflows/build-csharp.yml
2. 点击 "Run workflow"
3. 等待构建完成（约 5-10 分钟）

**检查构建结果**:
- 应该生成 4 个 artifacts：
  - `meowth-bridge-windows`
  - `meowth-bridge-macos`
  - `meowth-bridge-linux`
  - `meowth-bridge-binaries`（合并的）
- 点击 artifact 可以下载查看
- 检查文件大小是否合理（15-30MB）

### 第 3 步：测试 PyPI 发布工作流（使用 TestPyPI）

**⚠️ 在测试前需要配置 TestPyPI**

1. **注册 TestPyPI 账号**（如果还没有）
   - 访问 https://test.pypi.org/account/register/

2. **配置可信发布**
   - 访问 https://test.pypi.org/manage/account/publishing/
   - 点击 "Add a new pending publisher"
   - 填写：
     - PyPI Project Name: `meowth-translator`
     - Owner: `Olcmyk`
     - Repository name: `Meowth-GBA-Translator`
     - Workflow name: `publish-pypi.yml`
     - Environment name: 留空
   - 保存

3. **手动触发发布工作流**
   - 访问 https://github.com/Olcmyk/Meowth-GBA-Translator/actions/workflows/publish-pypi.yml
   - 点击 "Run workflow"
   - ✅ 勾选 "Publish to TestPyPI instead of PyPI"
   - 点击 "Run workflow"

4. **验证发布**
   - 等待工作流完成
   - 访问 https://test.pypi.org/project/meowth-translator/
   - 应该能看到 0.2.0 版本

5. **测试安装**
   ```bash
   # 在干净的环境中测试
   python -m venv test_env
   source test_env/bin/activate  # Windows: test_env\Scripts\activate

   # 从 TestPyPI 安装
   pip install -i https://test.pypi.org/simple/ meowth-translator

   # 测试
   meowth --help
   python -c "from meowth.binaries import find_meowth_bridge; print(find_meowth_bridge())"
   ```

## 常见问题排查

### 问题 1：Tests 工作流失败

**可能原因**:
- MeowthBridge 构建失败（缺少 .NET SDK）
- Python 依赖安装失败
- 导入错误

**解决方法**:
- 查看失败的 job 日志
- 在本地复现问题
- 修复后重新推送

### 问题 2：Build MeowthBridge 工作流失败

**可能原因**:
- C# 代码编译错误
- 发布配置错误
- macOS lipo 命令失败

**解决方法**:
- 检查 `src/MeowthBridge` 代码
- 本地测试构建：`./build-binaries.sh`
- 查看工作流日志

### 问题 3：Publish to PyPI 工作流失败

**可能原因**:
- 未配置可信发布
- 二进制文件未包含在包中
- 版本号冲突

**解决方法**:
- 检查 PyPI 可信发布配置
- 查看 "Check package contents" 步骤的输出
- 确保版本号唯一

## 查看工作流日志

### 通过网页界面

1. 访问 Actions 页面
2. 点击具体的工作流运行
3. 点击失败的 job
4. 展开失败的步骤
5. 查看详细日志

### 使用 GitHub CLI

```bash
# 查看最新运行的日志
gh run view --log

# 查看特定运行的日志
gh run view <run-id> --log

# 下载日志
gh run download <run-id>
```

## 监控工作流状态

### 实时监控

```bash
# 使用 GitHub CLI 实时监控
gh run watch

# 或者使用 watch 命令定期检查
watch -n 10 'gh run list --limit 5'
```

### 邮件通知

GitHub 会自动发送邮件通知：
- ✅ 工作流成功
- ❌ 工作流失败
- 检查你的 GitHub 注册邮箱

## 下一步行动

### 如果所有测试都通过 ✅

1. **继续 Phase 3**：开发 NiceGUI 界面
2. **或者发布 0.2.0-beta**：
   - 创建 GitHub Release
   - 自动触发 PyPI 发布
   - 让用户测试

### 如果有测试失败 ❌

1. 查看失败日志
2. 在本地修复问题
3. 重新推送
4. 等待测试通过

## 有用的链接

- **Actions 页面**: https://github.com/Olcmyk/Meowth-GBA-Translator/actions
- **Tests 工作流**: https://github.com/Olcmyk/Meowth-GBA-Translator/actions/workflows/test.yml
- **Build 工作流**: https://github.com/Olcmyk/Meowth-GBA-Translator/actions/workflows/build-csharp.yml
- **Publish 工作流**: https://github.com/Olcmyk/Meowth-GBA-Translator/actions/workflows/publish-pypi.yml
- **TestPyPI**: https://test.pypi.org/
- **PyPI**: https://pypi.org/

## 总结

✅ 代码已推送到 GitHub
⏳ Tests 工作流应该正在运行
📋 按照上述步骤逐步测试每个工作流
🐛 如有问题，查看日志并修复

现在可以访问 GitHub Actions 页面查看运行状态了！
