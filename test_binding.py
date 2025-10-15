#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绑定功能测试脚本 - 用于诊断问题
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.business_logic import payment_processor_logic
from database.operations import PaymentOperations
from database.models import get_db_stats

print("=" * 60)
print("绑定功能诊断测试")
print("=" * 60)

# 1. 检查数据库状态
print("\n【1】数据库状态检查:")
stats = get_db_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")

# 2. 检查待处理缴费
print("\n【2】待处理缴费记录:")
pending = PaymentOperations.get_pending_payments()
print(f"  待处理数量: {len(pending)}")
if pending:
    print(f"  第一条: 学号={pending[0]['学号']}, 金额={pending[0]['缴费金额']}")

# 3. 检查失败记录
print("\n【3】失败缴费记录:")
failed = PaymentOperations.get_failed_payments()
print(f"  失败数量: {len(failed)}")

# 4. 执行绑定测试
print("\n【4】执行绑定测试:")
print("  开始执行...")

try:
    result = payment_processor_logic.process_pending_payments_and_generate_export()
    
    print(f"\n  ✅ 执行完成!")
    print(f"  成功: {result.get('success')}")
    print(f"  消息: {result.get('message')}")
    print(f"  处理数: {result.get('processed_count')}")
    print(f"  失败数: {result.get('failed_count')}")
    print(f"  导出文件: {result.get('export_file')}")
    
    if result.get('binding_data'):
        print(f"  绑定数据: {len(result['binding_data'])} 条")
        
except Exception as e:
    print(f"\n  ❌ 执行失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
