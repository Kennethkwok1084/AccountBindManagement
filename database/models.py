#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型定义
Database Models
"""

import sqlite3
import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any

class DatabaseManager:
    """数据库管理类"""

    def __init__(self, db_path: str = "data/account_manager.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()

    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def _init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 创建上网账号表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS isp_accounts (
                    账号 TEXT PRIMARY KEY,
                    账号类型 TEXT NOT NULL,
                    状态 TEXT NOT NULL DEFAULT '未使用',
                    生命周期开始日期 DATE,
                    生命周期结束日期 DATE,
                    绑定的学号 TEXT,
                    绑定的套餐到期日 DATE,
                    创建时间 TIMESTAMP,
                    更新时间 TIMESTAMP
                )
            ''')

            # 创建缴费记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_logs (
                    记录ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    学号 TEXT NOT NULL,
                    缴费时间 TIMESTAMP NOT NULL,
                    缴费金额 REAL NOT NULL,
                    处理状态 TEXT NOT NULL DEFAULT '待处理',
                    创建时间 TIMESTAMP,
                    处理时间 TIMESTAMP
                )
            ''')

            # 创建用户列表表（实际绑定关系 - 支持三大运营商）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_list (
                    用户账号 TEXT PRIMARY KEY,
                    绑定套餐 TEXT,
                    用户姓名 TEXT,
                    用户类别 TEXT,
                    移动账号 TEXT,
                    联通账号 TEXT,
                    电信账号 TEXT,
                    到期日期 DATE,
                    导入时间 TIMESTAMP,
                    更新时间 TIMESTAMP
                )
            ''')

            # 创建系统设置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    配置项 TEXT PRIMARY KEY,
                    配置值 TEXT,
                    描述 TEXT,
                    更新时间 TIMESTAMP
                )
            ''')

            # 创建账号类型规则表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_type_rules (
                    账号类型 TEXT PRIMARY KEY,
                    允许绑定 INTEGER NOT NULL DEFAULT 1,
                    生命周期月份 INTEGER,
                    自定义开始日期 DATE,
                    自定义结束日期 DATE,
                    更新时间 TIMESTAMP
                )
            ''')

            # 插入默认系统设置
            default_settings = [
                ('上次缴费导入时间', '1970-01-01 00:00:00', '最后一次导入缴费记录的时间'),
                ('0元账号启用状态', '启用', '0元账号是否启用'),
                ('0元账号有效期', '2025-12-31', '0元账号的统一到期日'),
                ('上次用户列表导入时间', '1970-01-01 00:00:00', '最后一次导入用户列表的时间'),
                ('上次自动维护执行时间', '1970-01-01 00:00:00', '最后一次执行自动维护的时间')
            ]

            cursor.executemany('''
                INSERT OR IGNORE INTO system_settings (配置项, 配置值, 描述)
                VALUES (?, ?, ?)
            ''', default_settings)

            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_isp_accounts_status ON isp_accounts(状态)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_isp_accounts_type ON isp_accounts(账号类型)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_isp_accounts_student ON isp_accounts(绑定的学号)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payment_logs_status ON payment_logs(处理状态)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payment_logs_student ON payment_logs(学号)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_list_mobile ON user_list(移动账号)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_list_unicom ON user_list(联通账号)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_list_telecom ON user_list(电信账号)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_list_category ON user_list(用户类别)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_list_package ON user_list(绑定套餐)')

            conn.commit()
            print(f"数据库初始化完成: {self.db_path}")

    def get_connection(self, enable_performance_mode: bool = False):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以按列名访问

        # 如果启用性能模式，应用优化参数
        if enable_performance_mode:
            self._apply_performance_settings(conn)

        return conn

    def _apply_performance_settings(self, conn):
        """应用SQLite性能优化设置"""
        cursor = conn.cursor()

        # 提升写入性能的设置
        cursor.execute("PRAGMA synchronous = NORMAL")      # 减少磁盘同步频率
        cursor.execute("PRAGMA journal_mode = WAL")        # 启用WAL模式
        cursor.execute("PRAGMA cache_size = 10000")        # 增大缓存到10MB
        cursor.execute("PRAGMA temp_store = memory")       # 临时表存储在内存
        cursor.execute("PRAGMA mmap_size = 268435456")     # 启用内存映射(256MB)

        cursor.close()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """执行更新操作并返回受影响的行数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """批量执行操作"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount

    def execute_batch_with_performance(self, operations: List[tuple]) -> int:
        """高性能批量执行多种操作"""
        total_affected = 0

        with self.get_connection(enable_performance_mode=True) as conn:
            cursor = conn.cursor()

            # 开始事务
            cursor.execute("BEGIN TRANSACTION")

            try:
                for operation_type, query, params in operations:
                    if operation_type == 'many':
                        cursor.executemany(query, params)
                    else:
                        cursor.execute(query, params)

                    total_affected += cursor.rowcount

                # 提交事务
                cursor.execute("COMMIT")
                return total_affected

            except Exception as e:
                # 回滚事务
                cursor.execute("ROLLBACK")
                raise e

    def bulk_upsert_accounts(self, accounts_data: List[tuple]) -> int:
        """批量插入或更新账号"""
        upsert_query = '''
            INSERT INTO isp_accounts (账号, 账号类型, 状态, 生命周期开始日期, 生命周期结束日期, 创建时间, 更新时间)
            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
            ON CONFLICT(账号) DO UPDATE SET
                账号类型 = excluded.账号类型,
                状态 = excluded.状态,
                生命周期开始日期 = excluded.生命周期开始日期,
                生命周期结束日期 = excluded.生命周期结束日期,
                更新时间 = datetime('now', 'localtime')
        '''

        with self.get_connection(enable_performance_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")

            try:
                cursor.executemany(upsert_query, accounts_data)
                affected_rows = cursor.rowcount
                cursor.execute("COMMIT")
                return affected_rows

            except Exception as e:
                cursor.execute("ROLLBACK")
                raise e


# 创建全局数据库管理实例
db_manager = DatabaseManager()


def get_db_stats() -> Dict[str, int]:
    """获取数据库统计信息"""
    stats = {}

    # 账号统计
    account_stats = db_manager.execute_query('''
        SELECT 状态, COUNT(*) as count
        FROM isp_accounts
        GROUP BY 状态
    ''')

    for stat in account_stats:
        stats[f'账号_{stat["状态"]}'] = stat['count']

    # 总账号数
    total_accounts = db_manager.execute_query('SELECT COUNT(*) as count FROM isp_accounts')
    stats['总账号数'] = total_accounts[0]['count'] if total_accounts else 0

    # 待处理缴费记录
    pending_payments = db_manager.execute_query('''
        SELECT COUNT(*) as count
        FROM payment_logs
        WHERE 处理状态 = '待处理'
    ''')
    stats['待处理缴费'] = pending_payments[0]['count'] if pending_payments else 0

    return stats


if __name__ == "__main__":
    # 测试数据库初始化
    print("数据库模型测试...")
    stats = get_db_stats()
    print("数据库统计:", stats)
