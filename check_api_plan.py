#!/usr/bin/env python3
"""
检查 Polygon API 订阅等级和数据延迟
"""
import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def check_api_plan():
    api_key = os.getenv('POLYGON_API_KEY')

    if not api_key or api_key == 'YOUR_API_KEY_HERE':
        print("❌ 未设置 API Key")
        return

    print("=" * 70)
    print("Polygon API 订阅信息检查")
    print("=" * 70)
    print()

    # 测试 Snapshot API
    print("1️⃣ 测试 Options Snapshot API...")
    print("-" * 70)

    url = f"https://api.polygon.io/v3/snapshot/options/SPY"
    params = {'apiKey': api_key, 'limit': 1}

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get('status') == 'OK':
                results = data.get('results', [])
                print("✅ Options Snapshot API: 可用")
                print(f"   返回数据: {len(results)} 个合约")

                if results:
                    contract = results[0]
                    last_updated = contract.get('last_updated')

                    if last_updated:
                        # 转换时间戳（纳秒）
                        update_time = datetime.fromtimestamp(last_updated / 1_000_000_000)
                        current_time = datetime.now()
                        delay = (current_time - update_time).total_seconds() / 60

                        print(f"   最后更新: {update_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"   数据延迟: 约 {delay:.1f} 分钟")

                        if delay < 1:
                            print("   📊 数据等级: ✨ 实时数据（Advanced/Business）")
                        elif delay < 20:
                            print("   📊 数据等级: ⏰ 15分钟延迟（Starter/Developer）")
                        else:
                            print("   📊 数据等级: ⏳ 延迟较大")
            else:
                print(f"❌ API 返回错误: {data.get('error', 'Unknown error')}")
        elif response.status_code == 403:
            print("❌ Options Snapshot API: 无权限")
            print("   您的订阅等级不包含期权数据")
            print("   需要: Options Starter 或更高")
        else:
            print(f"❌ API 请求失败: HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    print()

    # 测试 Flat Files
    print("2️⃣ 测试 Flat Files API...")
    print("-" * 70)

    from datetime import timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    year, month = yesterday.split('-')[0], yesterday.split('-')[1]

    url = f"https://files.polygon.io/flatfiles/us_options_opra/day_aggs_v1/{year}/{month}/{yesterday}.csv.gz"
    params = {'apiKey': api_key}

    try:
        # 只检查文件是否存在（HEAD 请求）
        response = requests.head(url, params=params, timeout=10)

        if response.status_code == 200:
            print("✅ Flat Files API: 可用")
            print(f"   可以下载日终聚合数据")
            file_size = response.headers.get('Content-Length')
            if file_size:
                size_mb = int(file_size) / (1024 * 1024)
                print(f"   文件大小: {size_mb:.1f} MB")
        elif response.status_code == 403:
            print("❌ Flat Files API: 无权限")
            print("   您的订阅等级不包含 Flat Files")
        elif response.status_code == 404:
            print("⚠️  Flat Files API: 文件未找到")
            print(f"   {yesterday}.csv.gz 可能还未生成")
            print("   （通常在收盘后 1-2 小时生成）")
        else:
            print(f"❌ API 请求失败: HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    print()
    print("=" * 70)
    print("总结")
    print("=" * 70)
    print()
    print("盘中运行建议:")
    print("  - 如果有 Flat Files 权限: ⚠️  无法获取当日数据（只有前一日）")
    print("  - 如果只有 Snapshot API: ⏰ 可以获取延迟/实时数据")
    print()
    print("最佳运行时间:")
    print("  - 盘后（美东 6:00 PM 后，北京时间次日 6:00 AM）")
    print("  - 数据完整且是最终值")
    print()

if __name__ == '__main__':
    check_api_plan()
