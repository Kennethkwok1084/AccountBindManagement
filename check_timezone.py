#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时区检查脚本 - 用于诊断时间问题
"""

from datetime import datetime
import sqlite3
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.operations import SystemSettingsOperations

print("=" * 80)
print("时区诊断报告")
print("=" * 80)

# 1. 系统时间
print(f"\n【系统时间】")
print(f"Python datetime.now(): {datetime.now()}")
print(f"环境变量 TZ: {os.environ.get('TZ', '未设置')}")

# 2. SQLite 时间函数
print(f"\n【SQLite 时间函数】")
conn = sqlite3.connect(':memory:')
cursor = conn.cursor()

cursor.execute("SELECT datetime('now')")
print(f"datetime('now') [UTC]: {cursor.fetchone()[0]}")

cursor.execute("SELECT datetime('now', 'localtime')")
print(f"datetime('now', 'localtime'): {cursor.fetchone()[0]}")

cursor.execute("SELECT date('now', 'localtime')")
print(f"date('now', 'localtime'): {cursor.fetchone()[0]}")

conn.close()

# 3. 系统设置中的时间戳
print(f"\n【系统设置时间戳】")
try:
    上次缴费导入 = SystemSettingsOperations.get_setting('上次缴费导入时间')
    上次用户列表导入 = SystemSettingsOperations.get_setting('上次用户列表导入时间')
    上次自动维护 = SystemSettingsOperations.get_setting('上次自动维护执行时间')

    print(f"上次缴费导入时间: {上次缴费导入}")
    print(f"上次用户列表导入时间: {上次用户列表导入}")
    print(f"上次自动维护执行时间: {上次自动维护}")
except Exception as e:
    print(f"读取系统设置失败: {e}")

# 4. 数据库时间戳示例
print(f"\n【数据库时间戳示例】")
try:
    from database.models import db_manager

    # 查看最近的缴费记录时间
    payments = db_manager.execute_query(
        "SELECT 缴费时间, 创建时间 FROM payment_logs ORDER BY 记录ID DESC LIMIT 3"
    )
    if payments:
        print("最近的缴费记录:")
        for p in payments:
            print(f"  - 缴费时间: {p['缴费时间']}, 创建时间: {p['创建时间']}")
    else:
        print("  (无缴费记录)")

    # 查看最近的账号更新时间
    accounts = db_manager.execute_query(
        "SELECT 账号, 更新时间 FROM isp_accounts WHERE 更新时间 IS NOT NULL ORDER BY 更新时间 DESC LIMIT 3"
    )
    if accounts:
        print("\n最近更新的账号:")
        for a in accounts:
            print(f"  - 账号: {a['账号']}, 更新时间: {a['更新时间']}")
    else:
        print("  (无账号记录)")

except Exception as e:
    print(f"查询数据库失败: {e}")

print("\n" + "=" * 80)
print("诊断建议:")
print("1. 检查上述所有时间是否与当前实际时间一致")
print("2. 如果 Python 时间正确但数据库时间错误，说明是 SQLite 时区问题")
print("3. 如果缴费时间比实际时间快，说明 Excel 导入时有时区转换问题")
print("=" * 80)
