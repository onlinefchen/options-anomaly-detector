# 批量数据生成与邮件发送指南

## 问题背景

当你运行 **强制生成最近3天数据** 时，如果最后一天失败，前面2天仍然会发邮件。

### 为什么会这样？

```
generate_historical_data.py 处理流程：
┌─────────────┐
│   Day 1     │ ✓ CSV下载成功 → 创建标记文件 NEW_DATA_GENERATED_2025-11-13
├─────────────┤
│   Day 2     │ ✓ CSV下载成功 → 创建标记文件 NEW_DATA_GENERATED_2025-11-14
├─────────────┤
│   Day 3     │ ✗ CSV下载失败 → 不创建标记文件
└─────────────┘
        ↓
run_ai_email.py 处理流程：
  • 发现 2 个标记文件 (Day 1, Day 2) 
  • 发送 2 封邮件 ✓
  • Day 3 因为没有标记文件，所以没有邮件 ✗
```

**结果**：部分邮件发送，容易造成不一致的数据状态

---

## 解决方案

### 方案 A：独立处理（默认，建议日常使用）

**行为**：每个日期独立处理
- Day 1 成功 → 发送邮件 ✓
- Day 2 成功 → 发送邮件 ✓
- Day 3 失败 → 不发送邮件 ✓

**优点**：
- 容错性强，部分失败不影响其他日期
- 适合日常自动化 workflow

**使用**：
```bash
# 默认模式（BATCH_PROCESSING_MODE=normal）
python generate_historical_data.py --days 3

# 明确指定
BATCH_PROCESSING_MODE=normal python generate_historical_data.py --days 3
```

---

### 方案 B：严格批处理（待实现，适合精细化控制）

**行为**：批量处理所有或全都跳过
- 如果任何一天失败 → 整个批次标记为失败，所有天都不发邮件
- 所有天都成功 → 所有天都发邮件

**优点**：
- 强制一致性，避免部分邮件的混乱
- 便于重试整个批次

**使用**（预计支持）：
```bash
BATCH_PROCESSING_MODE=strict python generate_historical_data.py --days 3
```

---

## 实际应用建议

### 日常定时运行（GitHub Actions）
```yaml
# 默认单一天数据，部分失败影响最小
python main.py
```

### 补充历史数据（手动触发）
```bash
# 方案A：快速补充，容错强
python generate_historical_data.py --days 3

# 观察输出的 "Batch Processing Summary"：
# ✅ All success → 邮件已发送
# ⚠️  Some failed → 失败的日期没有邮件，可手动重试
```

### 重试失败日期
```bash
# 重新生成最近3天（force_overwrite=true）
FORCE_OVERWRITE=true python generate_historical_data.py --days 3

# 观察哪些日期因为CSV不可用而失败
# 这些日期如果仍然失败，可能是 Polygon 还未上传 CSV
# 可稍后再试或联系 Polygon 支持
```

---

## 改进说明

### run_ai_email.py 的改进

**新增功能**：
1. **批量模式检测**：自动识别是否为批量处理
   - 1 个文件 → 单个模式
   - 多个文件 + 时间相近（5分钟内） → 批量模式

2. **批量处理总结**：
   ```
   📊 Batch Processing Summary
   ├─ Total files: 3
   ├─ Success: 2
   ├─ Failed: 1
   └─ Failed dates: 2025-11-15 (not sent)
   
   💡 Tips to avoid partial email sends:
      1. Check if CSV files exist for failed dates
      2. Re-run with force_overwrite=true to retry all dates
   ```

3. **失败列表明确显示**：知道哪些日期没有发邮件，便于排查

### generate_historical_data.py 的改进

**新增功能**：
1. **失败计数**：区分"跳过"（已存在）和"失败"（CSV不可用）
2. **批量模式提示**：
   ```
   ✅ BATCH PROCESSING SUCCESS:
      • 所有 3 个日期都成功生成并创建了标记文件
      • 邮件将在 AI Analysis & Email 步骤中发送
   ```
   或
   ```
   ⚠️  BATCH PROCESSING NOTICE:
      • 批量处理中出现 1 个失败
      • 已为 2 个成功日期生成了标记文件
      • 失败的日期不会发送邮件
   ```

---

## 故障排查

### 问题：Run 完成后邮件数量 < 期望数量

**检查步骤**：

1. 查看 `run_ai_email.py` 的输出
   ```
   📊 Batch Processing Summary
      Total files: 3
      Success: 2
      Failed: 1
      Failed dates: 2025-11-15 (not sent)
   ```

2. 检查失败日期的 JSON 文件是否存在
   ```bash
   ls -la output/2025-11-15.json
   ```

3. 如果不存在，说明 `generate_historical_data.py` 中该日期没有生成成功
   - 可能是 CSV 不可用
   - 可能是网络问题
   - 可能是 API 限流

4. 重试失败的日期
   ```bash
   # 重新下载该日期的CSV并分析
   FORCE_OVERWRITE=true python generate_historical_data.py --date 2025-11-15
   
   # 手动运行邮件发送
   python scripts/run_ai_email.py
   ```

---

## 最佳实践

### ✅ 推荐做法

1. **日常自动运行**：使用默认模式，无需特殊配置
2. **补充历史数据**：
   ```bash
   # 生成最近 5 个交易日
   python generate_historical_data.py --days 5
   
   # 观察输出，确认成功数量
   # 如果有失败，稍后重试
   ```

3. **邮件发送**：自动在 AI Analysis & Email 步骤中处理
   - 成功的日期 → 发邮件
   - 失败的日期 → 跳过（log 中清晰显示）

### ❌ 避免做法

1. ❌ 手动删除标记文件来控制邮件发送
   - 容易出错和混乱
   - 用 `generate_historical_data.py` 来控制生成哪些日期

2. ❌ 期望所有日期都成功
   - 网络、API 限流、CSV 延迟是正常状态
   - 失败日期可在下次重试

3. ❌ 强制覆盖后立即检查邮件数量
   - 邮件可能需要几秒钟才能发送
   - 等待 workflow 完全完成

---

## 常见问题

### Q: 为什么有些日期的 CSV 不可用？

A: Polygon 在美国东部时间 16:00-17:00（北京时间次日 4:00-5:00）上传 CSV。如果该时间还未上传，就会显示不可用。稍后重试即可。

### Q: 如何只为特定日期生成数据？

A: 
```bash
# 单个日期
python generate_historical_data.py --date 2025-11-13

# 日期区间
python generate_historical_data.py --start 2025-11-10 --end 2025-11-15
```

### Q: 重新生成会覆盖旧邮件吗？

A: 不会。邮件一旦发送就无法取消。重新生成会覆盖 JSON/HTML 文件，但不会再次发邮件（需要删除标记文件后重新生成）。

### Q: 如何禁用邮件发送，只生成报告？

A: 不创建标记文件或删除标记文件：
```bash
# 删除所有标记文件
rm output/NEW_DATA_GENERATED_*

# 然后邮件步骤就不会处理任何文件
```

---

## 环境变量参考

| 变量 | 值 | 说明 |
|-----|-----|------|
| `FORCE_OVERWRITE` | `true`/`false` | 是否强制重新生成已存在的数据 |
| `BATCH_PROCESSING_MODE` | `normal`/`strict` | 批量处理模式（strict 功能待实现） |

---

## 更新日志

### v1.0 (2025-11-15)
- ✅ 添加批量模式检测
- ✅ 改进邮件发送的失败显示
- ✅ 区分"跳过"和"失败"
- 🔜 待实现：strict 批处理模式

