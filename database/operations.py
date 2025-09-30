#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库操作层
Database Operations
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from .models import db_manager


class ISPAccountOperations:
    """上网账号表操作类"""

    @staticmethod
    def create_account(账号: str, 账号类型: str, 状态: str = '未使用',
                      生命周期开始日期: Optional[date] = None,
                      生命周期结束日期: Optional[date] = None) -> bool:
        """创建新账号"""
        try:
            query = '''
                INSERT INTO isp_accounts (账号, 账号类型, 状态, 生命周期开始日期, 生命周期结束日期)
                VALUES (?, ?, ?, ?, ?)
            '''
            db_manager.execute_update(query, (
                账号, 账号类型, 状态, 生命周期开始日期, 生命周期结束日期
            ))
            return True
        except Exception as e:
            print(f"创建账号失败: {e}")
            return False

    @staticmethod
    def update_account(账号: str, **kwargs) -> bool:
        """更新账号信息"""
        try:
            # 构建动态更新语句
            set_clauses = []
            params = []

            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)

            if not set_clauses:
                return False

            params.append(账号)
            query = f'''
                UPDATE isp_accounts
                SET {', '.join(set_clauses)}, 更新时间 = CURRENT_TIMESTAMP
                WHERE 账号 = ?
            '''

            affected_rows = db_manager.execute_update(query, tuple(params))
            return affected_rows > 0
        except Exception as e:
            print(f"更新账号失败: {e}")
            return False

    @staticmethod
    def get_account(账号: str) -> Optional[Dict[str, Any]]:
        """获取单个账号信息（关联用户姓名）"""
        query = '''
            SELECT
                isp_accounts.*,
                user_list.用户姓名
            FROM isp_accounts
            LEFT JOIN user_list ON isp_accounts.绑定的学号 = user_list.用户账号
            WHERE isp_accounts.账号 = ?
        '''
        results = db_manager.execute_query(query, (账号,))
        return results[0] if results else None

    @staticmethod
    def get_available_accounts(limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取可用账号（未使用且未过期）"""
        query = '''
            SELECT * FROM isp_accounts
            WHERE 状态 = '未使用'
            AND (生命周期结束日期 IS NULL OR 生命周期结束日期 > date('now'))
            ORDER BY 创建时间
        '''

        if limit:
            query += f' LIMIT {limit}'

        return db_manager.execute_query(query)

    @staticmethod
    def search_accounts(状态: Optional[str] = None,
                       账号类型: Optional[str] = None,
                       绑定的学号: Optional[str] = None) -> List[Dict[str, Any]]:
        """搜索账号（关联用户姓名）"""
        conditions = []
        params = []

        if 状态:
            conditions.append('isp_accounts.状态 = ?')
            params.append(状态)
        if 账号类型:
            conditions.append('isp_accounts.账号类型 = ?')
            params.append(账号类型)
        if 绑定的学号:
            conditions.append('isp_accounts.绑定的学号 = ?')
            params.append(绑定的学号)

        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        query = f'''
            SELECT
                isp_accounts.*,
                user_list.用户姓名
            FROM isp_accounts
            LEFT JOIN user_list ON isp_accounts.绑定的学号 = user_list.用户账号
            WHERE {where_clause}
            ORDER BY isp_accounts.更新时间 DESC
        '''

        return db_manager.execute_query(query, tuple(params))

    @staticmethod
    def bind_account_to_student(账号: str, 学号: str) -> bool:
        """绑定账号到学生"""
        return ISPAccountOperations.update_account(账号, 状态='已使用', 绑定的学号=学号)

    @staticmethod
    def release_account(账号: str) -> bool:
        """释放账号（清除绑定信息）"""
        return ISPAccountOperations.update_account(
            账号, 状态='未使用', 绑定的学号=None, 绑定的套餐到期日=None
        )

    @staticmethod
    def expire_account(账号: str) -> bool:
        """将账号标记为已过期"""
        return ISPAccountOperations.update_account(账号, 状态='已过期')


class PaymentOperations:
    """缴费记录表操作类"""

    @staticmethod
    def add_payment(学号: str, 缴费时间: datetime, 缴费金额: float) -> Optional[int]:
        """添加缴费记录"""
        try:
            query = '''
                INSERT INTO payment_logs (学号, 缴费时间, 缴费金额)
                VALUES (?, ?, ?)
            '''
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (学号, 缴费时间, 缴费金额))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"添加缴费记录失败: {e}")
            return None

    @staticmethod
    def get_pending_payments() -> List[Dict[str, Any]]:
        """获取待处理的缴费记录"""
        query = '''
            SELECT * FROM payment_logs
            WHERE 处理状态 = '待处理'
            ORDER BY 缴费时间
        '''
        return db_manager.execute_query(query)

    @staticmethod
    def update_payment_status(记录ID: int, 处理状态: str) -> bool:
        """更新缴费记录状态"""
        try:
            query = '''
                UPDATE payment_logs
                SET 处理状态 = ?, 处理时间 = CURRENT_TIMESTAMP
                WHERE 记录ID = ?
            '''
            affected_rows = db_manager.execute_update(query, (处理状态, 记录ID))
            return affected_rows > 0
        except Exception as e:
            print(f"更新缴费状态失败: {e}")
            return False

    @staticmethod
    def get_failed_payments() -> List[Dict[str, Any]]:
        """获取处理失败的缴费记录"""
        query = '''
            SELECT * FROM payment_logs
            WHERE 处理状态 = '处理失败'
            ORDER BY 缴费时间 DESC
        '''
        return db_manager.execute_query(query)


class SystemSettingsOperations:
    """系统设置表操作类"""

    @staticmethod
    def get_setting(配置项: str) -> Optional[str]:
        """获取系统设置"""
        query = 'SELECT 配置值 FROM system_settings WHERE 配置项 = ?'
        results = db_manager.execute_query(query, (配置项,))
        return results[0]['配置值'] if results else None

    @staticmethod
    def set_setting(配置项: str, 配置值: str) -> bool:
        """设置系统配置"""
        try:
            query = '''
                INSERT OR REPLACE INTO system_settings (配置项, 配置值, 更新时间)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            '''
            db_manager.execute_update(query, (配置项, 配置值))
            return True
        except Exception as e:
            print(f"设置系统配置失败: {e}")
            return False

    @staticmethod
    def get_all_settings() -> List[Dict[str, Any]]:
        """获取所有系统设置"""
        query = 'SELECT * FROM system_settings ORDER BY 配置项'
        return db_manager.execute_query(query)


class MaintenanceOperations:
    """系统维护操作类"""

    @staticmethod
    def auto_release_expired_bindings() -> int:
        """自动释放套餐到期的账号绑定"""
        query = '''
            UPDATE isp_accounts
            SET 状态 = '未使用', 绑定的学号 = NULL, 绑定的套餐到期日 = NULL,
                更新时间 = CURRENT_TIMESTAMP
            WHERE 状态 = '已使用'
            AND 绑定的套餐到期日 < date('now')
            AND (生命周期结束日期 IS NULL OR 生命周期结束日期 > date('now'))
        '''
        return db_manager.execute_update(query)

    @staticmethod
    def auto_expire_lifecycle_ended() -> int:
        """自动将生命周期结束的账号标记为已过期（区分是否仍被绑定）"""
        # 情况1：生命周期过期且套餐也过期（或没有绑定）-> 标记为「已过期」
        query_expired = '''
            UPDATE isp_accounts
            SET 状态 = '已过期', 更新时间 = CURRENT_TIMESTAMP
            WHERE 生命周期结束日期 < date('now')
            AND 状态 NOT IN ('已过期', '已过期但被绑定')
            AND (绑定的套餐到期日 IS NULL OR 绑定的套餐到期日 < date('now'))
        '''
        count1 = db_manager.execute_update(query_expired)

        # 情况2：生命周期过期但套餐还没过期 -> 标记为「已过期但被绑定」
        query_expired_but_bound = '''
            UPDATE isp_accounts
            SET 状态 = '已过期但被绑定', 更新时间 = CURRENT_TIMESTAMP
            WHERE 生命周期结束日期 < date('now')
            AND 状态 NOT IN ('已过期', '已过期但被绑定')
            AND 绑定的套餐到期日 IS NOT NULL
            AND 绑定的套餐到期日 >= date('now')
        '''
        count2 = db_manager.execute_update(query_expired_but_bound)

        return count1 + count2

    @staticmethod
    def auto_mark_expired_subscriptions() -> int:
        """自动标记套餐已到期的用户"""
        query = '''
            UPDATE user_list
            SET 绑定套餐 = '已到期', 更新时间 = CURRENT_TIMESTAMP
            WHERE 到期日期 < date('now')
            AND 绑定套餐 != '已到期'
            AND 绑定套餐 IS NOT NULL
            AND 绑定套餐 != ''
        '''
        return db_manager.execute_update(query)

    @staticmethod
    def auto_convert_expired_but_bound_to_expired() -> int:
        """自动将「已过期但被绑定」且套餐也过期的账号转换为「已过期」"""
        query = '''
            UPDATE isp_accounts
            SET 状态 = '已过期', 更新时间 = CURRENT_TIMESTAMP
            WHERE 状态 = '已过期但被绑定'
            AND (绑定的套餐到期日 IS NULL OR 绑定的套餐到期日 < date('now'))
        '''
        return db_manager.execute_update(query)

    @staticmethod
    def run_daily_maintenance() -> Tuple[int, int, int, int]:
        """执行每日维护任务"""
        released_count = MaintenanceOperations.auto_release_expired_bindings()
        expired_count = MaintenanceOperations.auto_expire_lifecycle_ended()
        subscription_expired_count = MaintenanceOperations.auto_mark_expired_subscriptions()
        converted_count = MaintenanceOperations.auto_convert_expired_but_bound_to_expired()

        # 更新维护时间
        SystemSettingsOperations.set_setting('上次自动维护执行时间',
                                           datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        return released_count, expired_count, subscription_expired_count, converted_count


if __name__ == "__main__":
    # 测试数据库操作
    print("测试数据库操作...")

    # 测试系统设置
    print("系统设置:")
    settings = SystemSettingsOperations.get_all_settings()
    for setting in settings:
        print(f"  {setting['配置项']}: {setting['配置值']}")

    # 测试账号统计
    from .models import get_db_stats
    stats = get_db_stats()
    print("数据库统计:", stats)