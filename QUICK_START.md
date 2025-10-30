# 快速开始 - Options Anomaly Detector

## 🚀 一键运行

### Linux / macOS

```bash
./run.sh
```

### Windows

```cmd
run.bat
```

## 📋 首次运行前准备

### 1. 配置 API Key

```bash
# 复制配置文件模板
cp .env.example .env

# 编辑 .env 文件，填入你的 Polygon API Key
nano .env  # 或使用其他编辑器
```

`.env` 文件内容示例：
```
POLYGON_API_KEY=your_actual_api_key_here
```

### 2. 获取 Polygon API Key

1. 访问 https://polygon.io/
2. 注册免费账户
3. 在 Dashboard 中找到你的 API Key
4. 复制 API Key 到 `.env` 文件

## 🎯 脚本功能

自动化运行脚本会帮你完成：

- ✅ 检查 Python 环境
- ✅ 创建/激活虚拟环境
- ✅ 安装所有依赖包
- ✅ 检查配置文件
- ✅ 创建必要的目录
- ✅ 运行数据分析
- ✅ 自动打开分析报告

## 📊 输出文件

运行完成后，你会得到：

### 主报告
- `output/anomaly_report.html` - 最新的分析报告（自动在浏览器中打开）

### 历史数据
- `output/YYYY-MM-DD.json` - 每日的原始分析数据
- `output/YYYY-MM-DD.html` - 每日的报告备份
- `output/archive.html` - 历史归档索引页

### CSV 缓存（本地保留）
- `data/YYYY-MM-DD_options_day_aggs.csv.gz` - 从 Polygon 下载的原始数据缓存
- **这些文件不会提交到 Git**（已在 `.gitignore` 中排除）
- 下次运行时会复用缓存，节省下载时间

## 💡 高级用法

### 手动运行（不使用脚本）

```bash
# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 运行分析
python main.py
```

### 清理 CSV 缓存

如果想清空本地 CSV 缓存（强制重新下载）：

```bash
rm -rf data/*.csv.gz
```

### 查看特定日期的历史数据

```bash
# 在浏览器中打开
open output/2025-10-30.html

# 查看 JSON 数据
cat output/2025-10-30.json | python -m json.tool
```

## 🔄 数据缓存逻辑

### 盘中运行（市场开放时间）
- **自动重新下载** CSV 文件
- 确保获取最新的实时数据
- 覆盖旧的缓存文件

### 盘后/休市时运行
- **使用本地缓存**（如果存在）
- 节省下载时间和 API 配额
- 避免重复下载相同数据

市场时间（美东时间）：
- **盘前**: 4:00 AM - 9:30 AM
- **盘中**: 9:30 AM - 4:00 PM ⚡ 自动重新下载
- **盘后**: 4:00 PM - 8:00 PM
- **休市**: 8:00 PM - 4:00 AM 💾 使用缓存

## 🆘 常见问题

### 问题1: 提示 Python 未找到

**解决方案**: 安装 Python 3.8 或更高版本
- Linux: `sudo apt install python3`
- macOS: `brew install python3`
- Windows: https://www.python.org/downloads/

### 问题2: API Key 错误

**解决方案**: 检查 `.env` 文件
1. 确保文件存在: `ls -la .env`
2. 检查内容: `cat .env`
3. 确认 API Key 正确（从 Polygon.io 复制）

### 问题3: CSV 下载失败

这是正常的！系统会自动回退到纯 API 模式：
- CSV 方法：快速，获取完整市场数据（需要 Polygon 订阅）
- API 方法：免费，获取 Top 48 活跃标的

### 问题4: 权限错误 (Linux/macOS)

```bash
chmod +x run.sh
./run.sh
```

## 📈 数据来源

- **CSV 数据**: Polygon.io Flat Files API (完整市场数据)
- **API 数据**: Polygon.io REST API (活跃标的数据)
- **历史数据**: 本地 JSON 文件（过去 10 个交易日）

## 🎨 报告内容

生成的 HTML 报告包含：

1. **📊 成交量 Top 30 排行**
   - Total Volume（总成交量）
   - C/P Volume Ratio（看涨/看跌成交比）
   - Open Interest（持仓量）
   - C/P OI Ratio（看涨/看跌持仓比）

2. **🔥 Top 3 活跃合约**
   - 每个标的的前 3 个最活跃期权合约
   - 显示行权价、到期日、持仓量占比

3. **🎯 主力价格区间**
   - 市场最集中的行权价区间
   - 核心行权价和持仓占比

4. **📅 10 日活跃度统计**
   - 过去 10 个交易日出现次数
   - 排名变化趋势（↑↓↔️）
   - 平均排名

5. **⚠️ 异常检测**
   - 成交量异常
   - C/P 比例异常
   - 持仓量异常

## 🔗 相关链接

- GitHub 仓库: https://github.com/onlinefchen/options-anomaly-detector
- 在线报告: https://onlinefchen.github.io/options-anomaly-detector/
- Polygon API 文档: https://polygon.io/docs/options

---

**享受分析！** 📊✨
