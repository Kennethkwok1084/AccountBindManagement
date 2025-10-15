#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库操作层
Database Operations
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from dateutil.relativedelta import relativedelta
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
                INSERT INTO isp_accounts (账号, 账号类型, 状态, 生命周期开始日期, 生命周期结束日期, 创建时间, 更新时间)
                VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
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
                SET {', '.join(set_clauses)}, 更新时间 = datetime('now', 'localtime')
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
            SELECT ia.*
            FROM isp_accounts ia
            LEFT JOIN account_type_rules atr ON ia.账号类型 = atr.账号类型
            WHERE ia.状态 = '未使用'
              AND (ia.生命周期结束日期 IS NULL OR ia.生命周期结束日期 > date('now', 'localtime'))
              AND COALESCE(atr.允许绑定, 1) = 1
            ORDER BY ia.创建时间
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
        """释放账号（清除绑定信息并同步用户列表）"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT 绑定的学号
                    FROM isp_accounts
                    WHERE 账号 = ?
                    LIMIT 1
                    ''',
                    (账号,)
                )
                account_row = cursor.fetchone()

                if not account_row:
                    return False

                bound_student = account_row['绑定的学号']

                cursor.execute(
                    '''
                    UPDATE isp_accounts
                    SET 状态 = '未使用',
                        绑定的学号 = NULL,
                        绑定的套餐到期日 = NULL,
                        更新时间 = datetime('now', 'localtime')
                    WHERE 账号 = ?
                    ''',
                    (账号,)
                )

                if cursor.rowcount == 0:
                    conn.commit()
                    return False

                if bound_student:
                    cursor.execute(
                        '''
                        UPDATE user_list
                        SET 移动账号 = NULL,
                            更新时间 = datetime('now', 'localtime')
                        WHERE 用户账号 = ?
                          AND 移动账号 = ?
                        ''',
                        (bound_student, 账号)
                    )

                conn.commit()
                return True
        except Exception as e:
            print(f"释放账号失败: {e}")
            return False

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
                INSERT INTO payment_logs (学号, 缴费时间, 缴费金额, 创建时间)
                VALUES (?, ?, ?, datetime('now', 'localtime'))
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
                SET 处理状态 = ?, 处理时间 = datetime('now', 'localtime')
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
                VALUES (?, ?, datetime('now', 'localtime'))
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


class AccountTypeRuleOperations:
    """账号类型规则操作类"""

    @staticmethod
    def _normalize_rule(rule: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not rule:
            return None
        normalized = dict(rule)
        normalized['允许绑定'] = bool(rule.get('允许绑定', 1))
        return normalized

    @staticmethod
    def list_rules() -> List[Dict[str, Any]]:
        """获取所有账号类型规则"""
        query = 'SELECT * FROM account_type_rules ORDER BY 账号类型'
        rules = db_manager.execute_query(query)
        return [AccountTypeRuleOperations._normalize_rule(rule) for rule in rules]

    @staticmethod
    def get_rule(账号类型: str) -> Optional[Dict[str, Any]]:
        """获取指定账号类型的规则"""
        query = 'SELECT * FROM account_type_rules WHERE 账号类型 = ? LIMIT 1'
        results = db_manager.execute_query(query, (账号类型,))
        return AccountTypeRuleOperations._normalize_rule(results[0]) if results else None

    @staticmethod
    def upsert_rule(账号类型: str,
                    允许绑定: bool,
                    生命周期月份: Optional[int] = None,
                    自定义开始日期: Optional[date] = None,
                    自定义结束日期: Optional[date] = None) -> bool:
        """新增或更新账号类型规则"""
        try:
            query = '''
                INSERT INTO account_type_rules (
                    账号类型, 允许绑定, 生命周期月份, 自定义开始日期, 自定义结束日期, 更新时间
                )
                VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                ON CONFLICT(账号类型) DO UPDATE SET
                    允许绑定 = excluded.允许绑定,
                    生命周期月份 = excluded.生命周期月份,
                    自定义开始日期 = excluded.自定义开始日期,
                    自定义结束日期 = excluded.自定义结束日期,
                    更新时间 = excluded.更新时间
            '''
            params = (
                账号类型.strip(),
                1 if 允许绑定 else 0,
                生命周期月份,
                自定义开始日期.strftime('%Y-%m-%d') if 自定义开始日期 else None,
                自定义结束日期.strftime('%Y-%m-%d') if 自定义结束日期 else None
            )
            db_manager.execute_update(query, params)
            return True
        except Exception as e:
            print(f"保存账号类型规则失败: {e}")
            return False

    @staticmethod
    def delete_rule(账号类型: str) -> bool:
        """删除账号类型规则"""
        try:
            query = 'DELETE FROM account_type_rules WHERE 账号类型 = ?'
            db_manager.execute_update(query, (账号类型,))
            return True
        except Exception as e:
            print(f"删除账号类型规则失败: {e}")
            return False

    @staticmethod
    def is_binding_allowed(账号类型: Optional[str]) -> bool:
        """判断指定账号类型是否允许绑定"""
        if not 账号类型:
            return True
        rule = AccountTypeRuleOperations.get_rule(账号类型)
        if not rule:
            return True
        return bool(rule.get('允许绑定', True))

    @staticmethod
    def calculate_lifecycle(账号类型: str,
                           默认开始日期: Optional[date],
                           默认结束日期: Optional[date]) -> Tuple[Optional[date], Optional[date]]:
        """根据规则计算生命周期日期"""
        rule = AccountTypeRuleOperations.get_rule(账号类型)
        if not rule:
            return 默认开始日期, 默认结束日期

        start_date = 默认开始日期
        end_date = 默认结束日期

        custom_start = rule.get('自定义开始日期')
        if custom_start:
            try:
                start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
            except Exception:
                pass

        lifecycle_months = rule.get('生命周期月份')
        if lifecycle_months is not None and start_date:
            try:
                months = int(lifecycle_months)
                if months <= 0:
                    end_date = start_date
                else:
                    end_date = start_date + relativedelta(months=months)
            except Exception:
                pass

        custom_end = rule.get('自定义结束日期')
        if custom_end:
            try:
                end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
            except Exception:
                pass

        return start_date, end_date

class MaintenanceOperations:
    """系统维护操作类"""

    @staticmethod
    def auto_release_expired_bindings() -> int:
        """自动释放套餐到期的账号绑定"""
        selection_query = '''
            SELECT 账号, 绑定的学号
            FROM isp_accounts
            WHERE 状态 = '已使用'
              AND 绑定的套餐到期日 < date('now', 'localtime')
              AND (生命周期结束日期 IS NULL OR 生命周期结束日期 > date('now', 'localtime'))
        '''

        with db_manager.get_connection(enable_performance_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(selection_query)
            rows = cursor.fetchall()

            if not rows:
                return 0

            account_ids = [row['账号'] for row in rows]

            placeholders = ','.join(['?'] * len(account_ids))
            update_query = f'''
                UPDATE isp_accounts
                SET 状态 = '未使用',
                    绑定的学号 = NULL,
                    绑定的套餐到期日 = NULL,
                    更新时间 = datetime('now', 'localtime')
                WHERE 账号 IN ({placeholders})
            '''
            cursor.execute(update_query, tuple(account_ids))
            released_count = cursor.rowcount

            # 同步用户列表，移除已释放账号的移动账号字段
            sync_params = [
                (row['绑定的学号'], row['账号'])
                for row in rows
                if row['绑定的学号']
            ]

            if sync_params:
                cursor.executemany(
                    '''
                    UPDATE user_list
                    SET 移动账号 = NULL,
                        更新时间 = datetime('now', 'localtime')
                    WHERE 用户账号 = ?
                      AND 移动账号 = ?
                    ''',
                    sync_params
                )

            conn.commit()
            return released_count

    @staticmethod
    def auto_expire_lifecycle_ended() -> int:
        """自动将生命周期结束的账号标记为已过期（区分是否仍被绑定）"""
        # 情况1：生命周期过期且套餐也过期（或没有绑定）-> 标记为「已过期」
        query_expired = '''
            UPDATE isp_accounts
            SET 状态 = '已过期', 更新时间 = datetime('now', 'localtime')
            WHERE 生命周期结束日期 < date('now', 'localtime')
            AND 状态 NOT IN ('已过期', '已过期但被绑定')
            AND (绑定的套餐到期日 IS NULL OR 绑定的套餐到期日 < date('now', 'localtime'))
        '''
        count1 = db_manager.execute_update(query_expired)

        # 情况2：生命周期过期但套餐还没过期 -> 标记为「已过期但被绑定」
        query_expired_but_bound = '''
            UPDATE isp_accounts
            SET 状态 = '已过期但被绑定', 更新时间 = datetime('now', 'localtime')
            WHERE 生命周期结束日期 < date('now', 'localtime')
            AND 状态 NOT IN ('已过期', '已过期但被绑定')
            AND 绑定的套餐到期日 IS NOT NULL
            AND 绑定的套餐到期日 >= date('now', 'localtime')
        '''
        count2 = db_manager.execute_update(query_expired_but_bound)

        return count1 + count2

    @staticmethod
    def auto_mark_expired_subscriptions() -> int:
        """自动标记套餐已到期的用户"""
        query = '''
            UPDATE user_list
            SET 绑定套餐 = '已到期', 更新时间 = datetime('now', 'localtime')
            WHERE 到期日期 < date('now', 'localtime')
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
            SET 状态 = '已过期', 更新时间 = datetime('now', 'localtime')
            WHERE 状态 = '已过期但被绑定'
            AND (绑定的套餐到期日 IS NULL OR 绑定的套餐到期日 < date('now', 'localtime'))
        '''
        return db_manager.execute_update(query)

    @staticmethod
    def auto_fix_duplicate_mobile_bindings() -> Tuple[int, int, int]:
        """自动修复用户列表中的重复移动账号绑定"""
        duplicate_query = '''
            SELECT 移动账号
            FROM user_list
            WHERE 移动账号 IS NOT NULL
              AND 移动账号 != ''
            GROUP BY 移动账号
            HAVING COUNT(*) > 1
        '''

        with db_manager.get_connection(enable_performance_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(duplicate_query)
            duplicate_accounts = cursor.fetchall()

            if not duplicate_accounts:
                return 0, 0, 0

            processed_groups = 0
            rebind_count = 0
            cleared_count = 0

            for row in duplicate_accounts:
                mobile_account = row['移动账号']
                if not mobile_account:
                    continue

                processed_groups += 1

                cursor.execute(
                    '''
                    SELECT 用户账号, 到期日期, 更新时间
                    FROM user_list
                    WHERE 移动账号 = ?
                    ORDER BY 更新时间 DESC
                    ''',
                    (mobile_account,)
                )
                user_entries = cursor.fetchall()

                if not user_entries:
                    continue

                cursor.execute(
                    '''
                    SELECT 绑定的学号, 绑定的套餐到期日, 状态
                    FROM isp_accounts
                    WHERE 账号 = ?
                    ''',
                    (mobile_account,)
                )
                account_info = cursor.fetchone()

                keeper_user = None
                keeper_expiry = None
                if account_info and account_info['绑定的学号']:
                    keeper_user = account_info['绑定的学号']
                    keeper_expiry = account_info['绑定的套餐到期日']

                if keeper_user is None:
                    keeper_user = user_entries[0]['用户账号']
                    keeper_expiry = user_entries[0]['到期日期']

                if keeper_expiry is None:
                    for entry in user_entries:
                        if entry['用户账号'] == keeper_user:
                            keeper_expiry = entry['到期日期']
                            break

                # 确保原账号绑定保持一致
                cursor.execute(
                    '''
                    UPDATE isp_accounts
                    SET 绑定的学号 = ?,
                        绑定的套餐到期日 = ?,
                        状态 = CASE WHEN 状态 = '未使用' THEN '已使用' ELSE 状态 END,
                        更新时间 = datetime('now', 'localtime')
                    WHERE 账号 = ?
                    ''',
                    (keeper_user, keeper_expiry, mobile_account)
                )

                for entry in user_entries:
                    if entry['用户账号'] == keeper_user:
                        continue

                    cursor.execute(
                        '''
                        SELECT 账号
                        FROM isp_accounts
                        WHERE 状态 = '未使用'
                          AND (生命周期结束日期 IS NULL OR 生命周期结束日期 > date('now', 'localtime'))
                          AND COALESCE(
                                (SELECT 允许绑定 FROM account_type_rules WHERE 账号类型 = isp_accounts.账号类型),
                                1
                          ) = 1
                        ORDER BY 创建时间, 账号
                        LIMIT 1
                        '''
                    )
                    replacement = cursor.fetchone()

                    if replacement:
                        cursor.execute(
                            '''
                            UPDATE isp_accounts
                            SET 状态 = '已使用',
                                绑定的学号 = ?,
                                绑定的套餐到期日 = ?,
                                更新时间 = datetime('now', 'localtime')
                            WHERE 账号 = ?
                            ''',
                            (entry['用户账号'], entry['到期日期'], replacement['账号'])
                        )
                        cursor.execute(
                            '''
                            UPDATE user_list
                            SET 移动账号 = ?,
                                更新时间 = datetime('now', 'localtime')
                            WHERE 用户账号 = ?
                            ''',
                            (replacement['账号'], entry['用户账号'])
                        )
                        rebind_count += 1
                    else:
                        cursor.execute(
                            '''
                            UPDATE user_list
                            SET 移动账号 = NULL,
                                更新时间 = datetime('now', 'localtime')
                            WHERE 用户账号 = ?
                              AND 移动账号 = ?
                            ''',
                            (entry['用户账号'], mobile_account)
                        )
                        cleared_count += 1

            conn.commit()
            return processed_groups, rebind_count, cleared_count

    @staticmethod
    def get_duplicate_mobile_bindings() -> List[Dict[str, Any]]:
        """获取重复移动账号的详细信息"""
        duplicate_query = '''
            SELECT 移动账号
            FROM user_list
            WHERE 移动账号 IS NOT NULL
              AND 移动账号 != ''
            GROUP BY 移动账号
            HAVING COUNT(*) > 1
        '''

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(duplicate_query)
            duplicate_rows = cursor.fetchall()

            if not duplicate_rows:
                return []

            duplicate_accounts = [row['移动账号'] for row in duplicate_rows if row['移动账号']]
            placeholders = ','.join(['?'] * len(duplicate_accounts))

            detail_query = f'''
                SELECT
                    ul.移动账号,
                    ul.用户账号,
                    ul.用户姓名,
                    ul.用户类别,
                    ul.到期日期,
                    ul.更新时间,
                    ia.状态 AS 账号状态,
                    ia.绑定的学号 AS 账号绑定学号,
                    ia.绑定的套餐到期日 AS 账号绑定到期日
                FROM user_list ul
                LEFT JOIN isp_accounts ia ON ia.账号 = ul.移动账号
                WHERE ul.移动账号 IN ({placeholders})
                ORDER BY ul.移动账号, ul.更新时间 DESC
            '''

            cursor.execute(detail_query, tuple(duplicate_accounts))
            detail_rows = cursor.fetchall()

            groups: Dict[str, Dict[str, Any]] = {}
            for row in detail_rows:
                mobile_account = row['移动账号']
                if mobile_account not in groups:
                    groups[mobile_account] = {
                        '移动账号': mobile_account,
                        '账号状态': row['账号状态'],
                        '账号绑定学号': row['账号绑定学号'],
                        '账号绑定到期日': row['账号绑定到期日'],
                        '学生列表': []
                    }

                groups[mobile_account]['学生列表'].append({
                    '用户账号': row['用户账号'],
                    '用户姓名': row['用户姓名'],
                    '用户类别': row['用户类别'],
                    '到期日期': row['到期日期'],
                    '更新时间': row['更新时间'],
                    '是否账号当前绑定': (row['用户账号'] == row['账号绑定学号'])
                })

            return list(groups.values())

    @staticmethod
    def manual_rebind_duplicate_student(移动账号: str, 用户账号: str) -> Tuple[bool, str, Optional[str]]:
        """
        手动为重复绑定的学号换绑新的未使用账号

        Returns:
            (成功标记, 消息, 新账号)
        """
        with db_manager.get_connection(enable_performance_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")

            try:
                cursor.execute(
                    '''
                    SELECT 用户账号, 移动账号, 到期日期
                    FROM user_list
                    WHERE 用户账号 = ?
                      AND 移动账号 = ?
                    LIMIT 1
                    ''',
                    (用户账号, 移动账号)
                )
                user_entry = cursor.fetchone()

                if not user_entry:
                    cursor.execute("ROLLBACK")
                    return False, "未找到匹配的重复绑定记录", None

                cursor.execute(
                    '''
                    SELECT 账号
                    FROM isp_accounts
                    WHERE 状态 = '未使用'
                      AND (生命周期结束日期 IS NULL OR 生命周期结束日期 > date('now', 'localtime'))
                      AND COALESCE(
                            (SELECT 允许绑定 FROM account_type_rules WHERE 账号类型 = isp_accounts.账号类型),
                            1
                      ) = 1
                    ORDER BY 创建时间, 账号
                    LIMIT 1
                    '''
                )
                new_account_row = cursor.fetchone()

                if not new_account_row:
                    cursor.execute("ROLLBACK")
                    return False, "没有可用的未使用账号", None

                new_account = new_account_row['账号']

                cursor.execute(
                    '''
                    UPDATE isp_accounts
                    SET 状态 = '已使用',
                        绑定的学号 = ?,
                        绑定的套餐到期日 = ?,
                        更新时间 = datetime('now', 'localtime')
                    WHERE 账号 = ?
                    ''',
                    (用户账号, user_entry['到期日期'], new_account)
                )

                cursor.execute(
                    '''
                    UPDATE user_list
                    SET 移动账号 = ?,
                        更新时间 = datetime('now', 'localtime')
                    WHERE 用户账号 = ?
                    ''',
                    (new_account, 用户账号)
                )

                cursor.execute(
                    '''
                    SELECT 用户账号, 到期日期
                    FROM user_list
                    WHERE 移动账号 = ?
                    ORDER BY 更新时间 DESC
                    ''',
                    (移动账号,)
                )
                remaining_entries = cursor.fetchall()

                if remaining_entries:
                    keeper = remaining_entries[0]
                    cursor.execute(
                        '''
                        UPDATE isp_accounts
                        SET 状态 = '已使用',
                            绑定的学号 = ?,
                            绑定的套餐到期日 = ?,
                            更新时间 = datetime('now', 'localtime')
                        WHERE 账号 = ?
                        ''',
                        (keeper['用户账号'], keeper['到期日期'], 移动账号)
                    )
                else:
                    cursor.execute(
                        '''
                        UPDATE isp_accounts
                        SET 状态 = '未使用',
                            绑定的学号 = NULL,
                            绑定的套餐到期日 = NULL,
                            更新时间 = datetime('now', 'localtime')
                        WHERE 账号 = ?
                        ''',
                        (移动账号,)
                    )

                cursor.execute("COMMIT")
                return True, f"学号 {用户账号} 已换绑到账号 {new_account}", new_account

            except Exception as e:
                cursor.execute("ROLLBACK")
                return False, f"换绑失败: {e}", None

    @staticmethod
    def run_daily_maintenance() -> Tuple[int, int, int, int, int, int, int]:
        """执行每日维护任务"""
        released_count = MaintenanceOperations.auto_release_expired_bindings()
        expired_count = MaintenanceOperations.auto_expire_lifecycle_ended()
        subscription_expired_count = MaintenanceOperations.auto_mark_expired_subscriptions()
        converted_count = MaintenanceOperations.auto_convert_expired_but_bound_to_expired()
        duplicate_groups, rebind_count, cleared_count = MaintenanceOperations.auto_fix_duplicate_mobile_bindings()

        # 更新维护时间
        SystemSettingsOperations.set_setting('上次自动维护执行时间',
                                           datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        return (
            released_count,
            expired_count,
            subscription_expired_count,
            converted_count,
            duplicate_groups,
            rebind_count,
            cleared_count
        )


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
