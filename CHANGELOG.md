# 更新日志

## 2025-10-30 (v3)

### 新增功能

#### 📊 表格动态排序功能
- **功能**: 点击表头即可对任意列进行排序
- **支持的排序列**:
  - 股票代码（字母顺序）
  - 总成交量
  - C/P 成交比
  - 持仓量
  - C/P 持仓比
  - Put 成交量
  - Call 成交量
- **交互体验**:
  - 鼠标悬停表头时高亮显示
  - 点击一次降序，再次点击升序
  - 当前排序列显示金色箭头图标 (▲ 或 ▼)
  - 排名列自动重新编号

**数据生成逻辑说明**:
1. Python 后端：按总成交量降序排列取前30个ticker
2. 完整数据以JSON格式传递到HTML
3. JavaScript客户端：实现动态排序和表格渲染

**修改文件**:
- `src/report_generator.py`
  - 添加 `table_data_json` 参数传递完整数据
  - 修改表头添加 `sortable` class和数据属性
  - 添加 `sortTable()` JavaScript函数
  - 添加 `renderTable()` 动态渲染函数
  - 添加CSS样式：`.sortable`、`.sort-icon`、排序状态样式

---

## 2025-10-30 (v2)

### 优化功能

#### 🔄 智能 CSV 缓存策略
- **盘中时段**: 自动重新下载 CSV 以获取最新数据
- **盘后/休市**: 使用本地缓存，避免重复下载
- **智能判断**: 根据美东时间自动识别交易时段
- **日志优化**: 清晰显示使用缓存或重新下载的原因

**修改文件**:
- `src/csv_handler.py`
  - 导入 `get_market_times` 获取市场时段信息
  - 修改 `download_csv()` 添加智能缓存判断逻辑
  - 盘中删除旧缓存并重新下载
  - 盘后/休市直接使用缓存

---

## 2025-10-30 (v1)

### 新增功能

#### 1. 📦 CSV 文件本地缓存
- **功能**: 自动保存下载的 CSV 文件到本地磁盘
- **位置**: `data/YYYY-MM-DD_options_day_aggs.csv.gz`
- **优势**:
  - 首次下载后自动缓存
  - 第二次运行直接从本地加载，节省时间和 API 配额
  - 保留历史数据，便于回溯分析
  - 自动忽略 Git 提交（已配置 .gitignore）

**修改文件**:
- `src/csv_handler.py`
  - 新增 `_get_local_csv_path()` - 获取本地文件路径
  - 新增 `_save_csv_to_disk()` - 保存文件到磁盘
  - 修改 `download_csv()` - 支持本地缓存检查和保存

#### 2. 🌍 多时区时间显示
- **功能**: 同时显示美东时间和东八区时间
- **显示格式**:
  ```
  🔒 美东时间: 2025-10-29 20:42:21 EDT | 东八区时间: 2025-10-30 08:42:21 | 交易时段: 休市 (Market Closed)
  ```

**修改文件**:
- `requirements.txt` - 添加 `pytz>=2024.1` 依赖
- `src/utils.py` - 新增多个时区相关函数:
  - `get_market_session()` - 判断当前交易时段
  - `get_market_session_display()` - 获取时段显示文本
  - `get_market_times()` - 获取多时区时间信息
  - `format_market_time_html()` - 格式化 HTML 显示
  - 更新 `print_banner()` - 使用新的时区显示

#### 3. 📊 交易时段智能识别
- **功能**: 自动识别当前是盘前、盘中、盘后还是休市
- **时段定义**（美东时间）:
  - 🌅 盘前 (Pre-Market): 04:00 - 09:30
  - 📈 盘中 (Market Hours): 09:30 - 16:00
  - 🌙 盘后 (After Hours): 16:00 - 20:00
  - 🔒 休市 (Market Closed): 其他时间及周末

**修改文件**:
- `src/report_generator.py`
  - 导入时区转换函数
  - 更新 HTML 报告时间显示格式

### 测试结果

✅ 所有功能测试通过：
- ✓ 时区转换功能正常
- ✓ 交易时段判断准确
- ✓ CSV 保存路径生成正确
- ✓ data/ 目录自动创建

### 使用说明

#### CSV 缓存管理
```bash
# 查看已缓存的文件
ls -lh data/

# 清理旧数据（保留最近 30 天）
find data/ -name "*.csv.gz" -mtime +30 -delete
```

#### 手动清理缓存
```bash
# 删除所有缓存
rm -rf data/*.csv.gz

# 删除指定日期
rm data/2025-10-29_options_day_aggs.csv.gz
```

### 下一步计划
- [ ] 添加历史数据趋势分析
- [ ] 支持自定义时区显示
- [ ] CSV 数据压缩优化
