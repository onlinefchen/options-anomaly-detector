#!/bin/bash
#
# Options Anomaly Detector - 一键运行脚本
# 自动检查环境、安装依赖、运行分析
#

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_header() {
    echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}  ${CYAN}📊 Options Anomaly Detector - 期权市场异常分析${NC}           ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 打印标题
print_header

# Step 1: 检查 Python 版本
print_step "检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    print_error "未找到 Python 3，请先安装 Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_success "Python $PYTHON_VERSION"

# Step 2: 检查虚拟环境
print_step "检查虚拟环境..."
if [ ! -d "venv" ]; then
    print_warning "虚拟环境不存在，正在创建..."
    python3 -m venv venv
    print_success "虚拟环境创建成功"
else
    print_success "虚拟环境已存在"
fi

# 激活虚拟环境
source venv/bin/activate

# Step 3: 检查并安装依赖
print_step "检查依赖包..."
if ! pip show requests &> /dev/null; then
    print_warning "依赖包未安装，正在安装..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    print_success "依赖包安装完成"
else
    print_success "依赖包已安装"
fi

# Step 4: 检查 .env 文件和 API Key
print_step "检查配置文件..."
if [ ! -f ".env" ]; then
    print_error ".env 文件不存在"
    echo ""
    echo -e "${YELLOW}请执行以下操作：${NC}"
    echo "  1. 复制示例文件: cp .env.example .env"
    echo "  2. 编辑 .env 文件，填入你的 Polygon API Key"
    echo "  3. 重新运行此脚本"
    exit 1
fi

# 检查 API Key 是否设置
if grep -q "YOUR_API_KEY_HERE" .env 2>/dev/null; then
    print_error "Polygon API Key 未设置"
    echo ""
    echo -e "${YELLOW}请编辑 .env 文件，将 YOUR_API_KEY_HERE 替换为真实的 API Key${NC}"
    exit 1
fi

print_success "配置文件检查通过"

# Step 5: 创建必要的目录
print_step "检查目录结构..."
mkdir -p data output
print_success "目录结构完整"

# Step 6: 显示运行信息
echo ""
echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}准备开始分析...${NC}"
echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
echo ""

# 获取当前时间（美东时间和东八区）
CURRENT_TIME=$(TZ='America/New_York' date '+%Y-%m-%d %H:%M:%S %Z')
CURRENT_TIME_CN=$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')

echo -e "  ${BLUE}美东时间:${NC} $CURRENT_TIME"
echo -e "  ${BLUE}东八区时间:${NC} $CURRENT_TIME_CN"
echo ""

# Step 7: 运行主程序
print_step "运行分析程序..."
echo ""

if python3 main.py; then
    # 成功
    echo ""
    echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ 分析完成！${NC}"
    echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
    echo ""

    # 显示输出文件
    if [ -f "output/anomaly_report.html" ]; then
        REPORT_SIZE=$(du -h output/anomaly_report.html | cut -f1)
        echo -e "${CYAN}📊 报告文件:${NC}"
        echo -e "   ${GREEN}output/anomaly_report.html${NC} (${REPORT_SIZE})"
        echo ""

        # 尝试在浏览器中打开报告
        print_step "打开报告..."
        if command -v xdg-open &> /dev/null; then
            xdg-open output/anomaly_report.html &> /dev/null &
            print_success "报告已在浏览器中打开"
        elif command -v open &> /dev/null; then
            open output/anomaly_report.html &> /dev/null &
            print_success "报告已在浏览器中打开"
        else
            print_warning "无法自动打开浏览器，请手动打开 output/anomaly_report.html"
        fi
    fi

    # 显示历史数据信息
    if ls output/*.json &> /dev/null; then
        JSON_COUNT=$(ls output/*.json 2>/dev/null | wc -l)
        echo ""
        echo -e "${CYAN}💾 历史数据:${NC}"
        echo -e "   共有 ${GREEN}$JSON_COUNT${NC} 个历史数据文件"
        echo -e "   位置: ${GREEN}output/*.json${NC}"
    fi

    # 显示 CSV 缓存信息
    if ls data/*.csv.gz &> /dev/null 2>&1; then
        CSV_COUNT=$(ls data/*.csv.gz 2>/dev/null | wc -l)
        CSV_SIZE=$(du -sh data/ 2>/dev/null | cut -f1)
        echo ""
        echo -e "${CYAN}📦 CSV 缓存:${NC}"
        echo -e "   共有 ${GREEN}$CSV_COUNT${NC} 个缓存文件 (总大小: ${GREEN}$CSV_SIZE${NC})"
        echo -e "   位置: ${GREEN}data/*.csv.gz${NC}"
        echo -e "   ${YELLOW}提示: CSV 文件不会提交到 Git，仅用于本地缓存${NC}"
    fi

    echo ""
    echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"

else
    # 失败
    echo ""
    echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}❌ 分析失败${NC}"
    echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    print_error "请检查上方的错误信息"
    exit 1
fi
