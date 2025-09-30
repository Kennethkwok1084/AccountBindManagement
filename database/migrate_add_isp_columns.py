#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加联通账号和电信账号字段
Migration Script - Add Unicom and Telecom Account Columns
"""

import sqlite3
import sys
import os

# Windows控制台UTF-8编码支持
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def migrate_database(db_path='data/account_manager.db'):
    """执行数据库迁移"""

    print(f"开始数据库迁移: {db_path}")

    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查是否已经有新字段
        cursor.execute("PRAGMA table_info(user_list)")
        columns = [col[1] for col in cursor.fetchall()]

        print(f"当前user_list表字段: {columns}")

        # 添加联通账号字段
        if '联通账号' not in columns:
            print("添加字段: 联通账号")
            cursor.execute("ALTER TABLE user_list ADD COLUMN 联通账号 TEXT")
            print("✅ 联通账号字段添加成功")
        else:
            print("⏭️  联通账号字段已存在，跳过")

        # 添加电信账号字段
        if '电信账号' not in columns:
            print("添加字段: 电信账号")
            cursor.execute("ALTER TABLE user_list ADD COLUMN 电信账号 TEXT")
            print("✅ 电信账号字段添加成功")
        else:
            print("⏭️  电信账号字段已存在，跳过")

        # 创建索引
        print("创建索引...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_list_unicom ON user_list(联通账号)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_list_telecom ON user_list(电信账号)")
        print("✅ 索引创建成功")

        # 提交更改
        conn.commit()

        # 验证迁移结果
        cursor.execute("PRAGMA table_info(user_list)")
        new_columns = [col[1] for col in cursor.fetchall()]
        print(f"\n迁移后字段列表: {new_columns}")

        conn.close()

        print("\n✅ 数据库迁移完成！")
        return True

    except Exception as e:
        print(f"\n❌ 数据库迁移失败: {e}")
        return False

if __name__ == "__main__":
    migrate_database()