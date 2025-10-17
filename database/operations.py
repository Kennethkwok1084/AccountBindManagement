#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库操作层
Database Operations
"""

import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from dateutil.relativedelta import relativedelta
from .models import db_manager


class OperationLogOperations:
    """操作日志表操作类"""

    @staticmethod
    def log_operation(操作类型: str,
                      操作人: str = '系统自动',
                      操作详情: Optional[Dict[str, Any]] = None,
                      影响记录数: Optional[int] = None,
                      执行状态: str = '成功',
                      备注: Optional[str] = None) -> Optional[int]:
        """记录操作日志"""
        try:
            details_json = (
                json.dumps(操作详情, ensure_ascii=False)
                if 操作详情 is not None else None
            )
            query = '''
                INSERT INTO operation_logs (
                    操作类型, 操作人, 操作详情, 影响记录数, 执行状态, 备注, 操作时间
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            '''
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    操作类型,
                    操作人,
                    details_json,
                    影响记录数,
                    执行状态,
                    备注
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as exc:
            print(f"记录操作日志失败: {exc}")
            return None

    @staticmethod
    def get_recent_logs(limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的操作日志"""
        query = '''
            SELECT * FROM operation_logs
            ORDER BY 操作时间 DESC
            LIMIT ?
        '''
        return db_manager.execute_query(query, (limit,))

    @staticmethod
    def update_operation_log(operation_id: int,
                             操作详情: Optional[Dict[str, Any]] = None,
                             影响记录数: Optional[int] = None,
                             执行状态: Optional[str] = None,
                             备注: Optional[str] = None) -> bool:
        """更新已存在的操作日志"""
        set_clauses = []
        params: List[Any] = []

        if 操作详情 is not None:
            set_clauses.append("操作详情 = ?")
            params.append(json.dumps(操作详情, ensure_ascii=False))
        if 影响记录数 is not None:
            set_clauses.append("影响记录数 = ?")
            params.append(影响记录数)
        if 执行状态 is not None:
            set_clauses.append("执行状态 = ?")
            params.append(执行状态)
        if 备注 is not None:
            set_clauses.append("备注 = ?")
            params.append(备注)

        if not set_clauses:
            return False

        set_clauses.append("操作时间 = datetime('now', 'localtime')")
        params.append(operation_id)

        query = f'''
            UPDATE operation_logs
            SET {', '.join(set_clauses)}
            WHERE id = ?
        '''
        try:
            affected = db_manager.execute_update(query, tuple(params))
            return affected > 0
        except Exception as exc:
            print(f"更新操作日志失败: {exc}")
            return False


class AccountChangeLogOperations:
    """账号变更日志操作类"""

    @staticmethod
    def _normalize_value(value: Any) -> Optional[str]:
        """统一转换存储的值"""
        if value is None:
            return None
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _should_log_change(old_value: Any, new_value: Any) -> bool:
        """判断是否需要记录变更"""
        return AccountChangeLogOperations._normalize_value(old_value) != \
            AccountChangeLogOperations._normalize_value(new_value)

    @staticmethod
    def log_account_change(账号: str,
                           变更类型: str,
                           变更字段: str,
                           旧值: Any,
                           新值: Any,
                           关联学号: Optional[str] = None,
                           操作来源: str = '手动操作',
                           操作批次ID: Optional[int] = None,
                           备注: Optional[str] = None) -> None:
        """记录账号变更日志"""
        if not AccountChangeLogOperations._should_log_change(旧值, 新值):
            return

        query = '''
            INSERT INTO account_change_logs (
                账号, 变更类型, 变更字段, 旧值, 新值,
                关联学号, 操作来源, 操作批次ID, 备注, 变更时间
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        '''
        db_manager.execute_update(query, (
            账号,
            变更类型,
            变更字段,
            AccountChangeLogOperations._normalize_value(旧值),
            AccountChangeLogOperations._normalize_value(新值),
            关联学号,
            操作来源,
            操作批次ID,
            备注
        ))

    @staticmethod
    def log_multiple_changes(账号: str,
                             changes: List[Dict[str, Any]],
                             关联学号: Optional[str] = None,
                             操作来源: str = '手动操作',
                             操作批次ID: Optional[int] = None,
                             备注: Optional[str] = None) -> None:
        """批量记录同一账号的多个字段变更"""
        for change in changes:
            AccountChangeLogOperations.log_account_change(
                账号=账号,
                变更类型=change.get('变更类型', '更新'),
                变更字段=change.get('变更字段', ''),
                旧值=change.get('旧值'),
                新值=change.get('新值'),
                关联学号=关联学号,
                操作来源=操作来源,
                操作批次ID=操作批次ID,
                备注=备注
            )

    @staticmethod
    def get_account_history(账号: str) -> List[Dict[str, Any]]:
        """查询账号的完整变更历史"""
        query = '''
            SELECT *
            FROM account_change_logs
            WHERE 账号 = ?
            ORDER BY 变更时间 DESC, id DESC
        '''
        return db_manager.execute_query(query, (账号,))

    @staticmethod
    def get_student_related_changes(学号: str) -> List[Dict[str, Any]]:
        """查询与学号相关的账号变更"""
        query = '''
            SELECT *
            FROM account_change_logs
            WHERE 关联学号 = ?
            ORDER BY 变更时间 DESC, id DESC
        '''
        return db_manager.execute_query(query, (学号,))

    @staticmethod
    def get_changes_by_time_range(开始时间: datetime,
                                  结束时间: datetime) -> List[Dict[str, Any]]:
        """按时间范围查询变更"""
        query = '''
            SELECT *
            FROM account_change_logs
            WHERE 变更时间 BETWEEN ? AND ?
            ORDER BY 变更时间 DESC, id DESC
        '''
        return db_manager.execute_query(
            query,
            (
                开始时间.strftime('%Y-%m-%d %H:%M:%S'),
                结束时间.strftime('%Y-%m-%d %H:%M:%S')
            )
        )

    @staticmethod
    def get_changes_by_operation(operation_id: int) -> List[Dict[str, Any]]:
        """按操作批次查询变更记录"""
        query = '''
            SELECT *
            FROM account_change_logs
            WHERE 操作批次ID = ?
            ORDER BY 变更时间 DESC, id DESC
        '''
        return db_manager.execute_query(query, (operation_id,))


class ISPAccountOperations:
    """上网账号表操作类"""

    @staticmethod
    def create_account(账号: str,
                      账号类型: str,
                      状态: str = '未使用',
                      生命周期开始日期: Optional[date] = None,
                      生命周期结束日期: Optional[date] = None,
                      log_context: Optional[Dict[str, Any]] = None) -> bool:
        """创建新账号"""
        try:
            query = '''
                INSERT INTO isp_accounts (账号, 账号类型, 状态, 生命周期开始日期, 生命周期结束日期, 创建时间, 更新时间)
                VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
            '''
            affected = db_manager.execute_update(query, (
                账号, 账号类型, 状态, 生命周期开始日期, 生命周期结束日期
            ))
            if affected > 0:
                snapshot = {
                    '账号类型': 账号类型,
                    '状态': 状态,
                    '生命周期开始日期': 生命周期开始日期,
                    '生命周期结束日期': 生命周期结束日期
                }
                context = log_context or {}
                AccountChangeLogOperations.log_account_change(
                    账号=账号,
                    变更类型='创建',
                    变更字段='全部',
                    旧值=None,
                    新值=json.dumps(snapshot, ensure_ascii=False),
                    关联学号=context.get('关联学号'),
                    操作来源=context.get('操作来源', '账号创建'),
                    操作批次ID=context.get('操作批次ID'),
                    备注=context.get('备注')
                )
            return affected > 0
        except Exception as e:
            print(f"创建账号失败: {e}")
            return False

    @staticmethod
    def update_account(账号: str,
                      log_context: Optional[Dict[str, Any]] = None,
                      **kwargs) -> bool:
        """更新账号信息"""
        try:
            old_account = ISPAccountOperations.get_account(账号)
            if not old_account:
                return False

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
            if affected_rows > 0:
                context = log_context or {}
                new_student = kwargs.get('绑定的学号')
                base_student = context.get('关联学号')
                related_student = base_student if base_student is not None else (
                    new_student if new_student is not None else old_account.get('绑定的学号')
                )

                for field, new_value in kwargs.items():
                    AccountChangeLogOperations.log_account_change(
                        账号=账号,
                        变更类型='更新',
                        变更字段=field,
                        旧值=old_account.get(field),
                        新值=new_value,
                        关联学号=related_student,
                        操作来源=context.get('操作来源', '直接更新'),
                        操作批次ID=context.get('操作批次ID'),
                        备注=context.get('备注')
                    )
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
    def bind_account_to_student(账号: str,
                               学号: str,
                               套餐到期日: Optional[date] = None,
                               log_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        绑定账号到学生（事务安全）
        确保账号表和用户表的数据一致性
        """
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    cursor.execute(
                        '''
                        SELECT 状态, 绑定的学号, 绑定的套餐到期日
                        FROM isp_accounts
                        WHERE 账号 = ?
                        LIMIT 1
                        ''',
                        (账号,)
                    )
                    account_record = cursor.fetchone()
                    if not account_record:
                        raise Exception(f"账号 {账号} 不存在，无法绑定")
                    old_account = dict(account_record)

                    # 1. 检查用户是否存在于用户列表
                    cursor.execute(
                        'SELECT 用户账号 FROM user_list WHERE 用户账号 = ?',
                        (学号,)
                    )
                    user_exists = cursor.fetchone()
                    
                    if not user_exists:
                        raise Exception(f"学号 {学号} 不存在于用户列表中，无法绑定")
                    
                    # 2. 清理之前占用同一账号的其他用户记录（避免重复绑定）
                    cursor.execute(
                        '''
                        UPDATE user_list
                        SET 移动账号 = NULL,
                            更新时间 = datetime('now', 'localtime')
                        WHERE 移动账号 = ?
                          AND 用户账号 != ?
                        ''',
                        (账号, 学号)
                    )
                    
                    # 3. 更新账号表 - 绑定账号到学生
                    cursor.execute(
                        '''
                        UPDATE isp_accounts
                        SET 状态 = '已使用',
                            绑定的学号 = ?,
                            绑定的套餐到期日 = ?,
                            更新时间 = datetime('now', 'localtime')
                        WHERE 账号 = ?
                        ''',
                        (学号, 套餐到期日, 账号)
                    )
                    
                    if cursor.rowcount == 0:
                        raise Exception(f"账号 {账号} 更新失败，可能账号不存在")
                    
                    # 4. 更新用户列表 - 设置移动账号
                    cursor.execute(
                        '''
                        UPDATE user_list
                        SET 移动账号 = ?,
                            更新时间 = datetime('now', 'localtime')
                        WHERE 用户账号 = ?
                        ''',
                        (账号, 学号)
                    )
                    
                    if cursor.rowcount == 0:
                        raise Exception(f"用户列表更新失败，学号 {学号}")
                    
                    # 提交事务
                    conn.commit()
                    context = log_context or {}
                    changes = [
                        {
                            '变更类型': '状态变更',
                            '变更字段': '状态',
                            '旧值': old_account.get('状态'),
                            '新值': '已使用'
                        },
                        {
                            '变更类型': '绑定',
                            '变更字段': '绑定的学号',
                            '旧值': old_account.get('绑定的学号'),
                            '新值': 学号
                        },
                        {
                            '变更类型': '绑定',
                            '变更字段': '绑定的套餐到期日',
                            '旧值': old_account.get('绑定的套餐到期日'),
                            '新值': 套餐到期日
                        }
                    ]
                    AccountChangeLogOperations.log_multiple_changes(
                        账号=账号,
                        changes=changes,
                        关联学号=context.get('关联学号', 学号),
                        操作来源=context.get('操作来源', '缴费绑定'),
                        操作批次ID=context.get('操作批次ID'),
                        备注=context.get('备注')
                    )
                    return True
                    
                except Exception as tx_error:
                    # 回滚事务
                    conn.rollback()
                    raise tx_error
                    
        except Exception as e:
            print(f"绑定账号失败: {e}")
            return False

    @staticmethod
    def release_account(账号: str,
                       log_context: Optional[Dict[str, Any]] = None) -> bool:
        """释放账号（清除绑定信息并同步用户列表）"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT 状态, 绑定的学号, 绑定的套餐到期日
                    FROM isp_accounts
                    WHERE 账号 = ?
                    LIMIT 1
                    ''',
                    (账号,)
                )
                account_row = cursor.fetchone()

                if not account_row:
                    return False

                old_account = dict(account_row)
                bound_student = old_account.get('绑定的学号')

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
                context = log_context or {}
                changes = [
                    {
                        '变更类型': '解绑',
                        '变更字段': '状态',
                        '旧值': old_account.get('状态'),
                        '新值': '未使用'
                    },
                    {
                        '变更类型': '解绑',
                        '变更字段': '绑定的学号',
                        '旧值': old_account.get('绑定的学号'),
                        '新值': None
                    },
                    {
                        '变更类型': '解绑',
                        '变更字段': '绑定的套餐到期日',
                        '旧值': old_account.get('绑定的套餐到期日'),
                        '新值': None
                    }
                ]
                AccountChangeLogOperations.log_multiple_changes(
                    账号=账号,
                    changes=changes,
                    关联学号=context.get('关联学号', bound_student),
                    操作来源=context.get('操作来源', '系统维护'),
                    操作批次ID=context.get('操作批次ID'),
                    备注=context.get('备注')
                )
                return True
        except Exception as e:
            print(f"释放账号失败: {e}")
            return False

    @staticmethod
    def expire_account(账号: str) -> bool:
        """将账号标记为已过期"""
        return ISPAccountOperations.update_account(
            账号,
            状态='已过期',
            log_context={'操作来源': '系统维护'}
        )


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
    def set_setting(配置项: str, 配置值: str, 操作人: str = '系统自动') -> bool:
        """设置系统配置"""
        old_value = SystemSettingsOperations.get_setting(配置项)
        try:
            query = '''
                INSERT OR REPLACE INTO system_settings (配置项, 配置值, 更新时间)
                VALUES (?, ?, datetime('now', 'localtime'))
            '''
            db_manager.execute_update(query, (配置项, 配置值))

            if old_value != 配置值:
                OperationLogOperations.log_operation(
                    操作类型='系统设置修改',
                    操作人=操作人,
                    操作详情={
                        '配置项': 配置项,
                        '旧值': old_value,
                        '新值': 配置值
                    },
                    影响记录数=1,
                    执行状态='成功'
                )

            return True
        except Exception as e:
            print(f"设置系统配置失败: {e}")
            OperationLogOperations.log_operation(
                操作类型='系统设置修改',
                操作人=操作人,
                操作详情={
                    '配置项': 配置项,
                    '旧值': old_value,
                    '新值': 配置值
                },
                影响记录数=0,
                执行状态='失败',
                备注=str(e)
            )
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
            SELECT 账号, 绑定的学号, 绑定的套餐到期日, 状态
            FROM isp_accounts
            WHERE 状态 = '已使用'
              AND 绑定的套餐到期日 < date('now', 'localtime')
              AND (生命周期结束日期 IS NULL OR 生命周期结束日期 > date('now', 'localtime'))
        '''

        release_targets: List[Dict[str, Any]] = []
        released_count = 0

        with db_manager.get_connection(enable_performance_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(selection_query)
            rows = cursor.fetchall()
            if not rows:
                conn.commit()
                return 0

            release_targets = [dict(row) for row in rows]

            account_ids = [row['账号'] for row in release_targets]

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
                for row in release_targets
                if row.get('绑定的学号')
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

        if released_count > 0:
            operation_id = OperationLogOperations.log_operation(
                操作类型='自动释放账号',
                操作详情={
                    '处理原因': '套餐到期自动释放',
                    '账号数量': released_count
                },
                影响记录数=released_count,
                执行状态='成功',
                操作人='系统自动'
            )

            for item in release_targets:
                AccountChangeLogOperations.log_multiple_changes(
                    账号=item['账号'],
                    changes=[
                        {
                            '变更类型': '解绑',
                            '变更字段': '状态',
                            '旧值': item.get('状态'),
                            '新值': '未使用'
                        },
                        {
                            '变更类型': '解绑',
                            '变更字段': '绑定的学号',
                            '旧值': item.get('绑定的学号'),
                            '新值': None
                        },
                        {
                            '变更类型': '解绑',
                            '变更字段': '绑定的套餐到期日',
                            '旧值': item.get('绑定的套餐到期日'),
                            '新值': None
                        }
                    ],
                    关联学号=item.get('绑定的学号'),
                    操作来源='系统维护',
                    操作批次ID=operation_id,
                    备注='套餐到期自动释放'
                )

            return released_count

    @staticmethod
    def auto_expire_lifecycle_ended() -> int:
        """自动将生命周期结束的账号标记为已过期（区分是否仍被绑定）"""
        selection_expired = '''
            SELECT 账号, 状态, 绑定的学号, 绑定的套餐到期日
            FROM isp_accounts
            WHERE 生命周期结束日期 < date('now', 'localtime')
              AND 状态 NOT IN ('已过期', '已过期但被绑定')
              AND (绑定的套餐到期日 IS NULL OR 绑定的套餐到期日 < date('now', 'localtime'))
        '''

        selection_expired_but_bound = '''
            SELECT 账号, 状态, 绑定的学号, 绑定的套餐到期日
            FROM isp_accounts
            WHERE 生命周期结束日期 < date('now', 'localtime')
              AND 状态 NOT IN ('已过期', '已过期但被绑定')
              AND 绑定的套餐到期日 IS NOT NULL
              AND 绑定的套餐到期日 >= date('now', 'localtime')
        '''

        expired_accounts: List[Dict[str, Any]] = []
        expired_but_bound_accounts: List[Dict[str, Any]] = []

        with db_manager.get_connection(enable_performance_mode=True) as conn:
            cursor = conn.cursor()

            cursor.execute(selection_expired)
            rows_expired = cursor.fetchall()
            if rows_expired:
                expired_accounts = [dict(row) for row in rows_expired]
                placeholders = ','.join(['?'] * len(expired_accounts))
                cursor.execute(
                    f'''
                    UPDATE isp_accounts
                    SET 状态 = '已过期', 更新时间 = datetime('now', 'localtime')
                    WHERE 账号 IN ({placeholders})
                    ''',
                    tuple(item['账号'] for item in expired_accounts)
                )

            cursor.execute(selection_expired_but_bound)
            rows_expired_but_bound = cursor.fetchall()
            if rows_expired_but_bound:
                expired_but_bound_accounts = [dict(row) for row in rows_expired_but_bound]
                placeholders = ','.join(['?'] * len(expired_but_bound_accounts))
                cursor.execute(
                    f'''
                    UPDATE isp_accounts
                    SET 状态 = '已过期但被绑定', 更新时间 = datetime('now', 'localtime')
                    WHERE 账号 IN ({placeholders})
                    ''',
                    tuple(item['账号'] for item in expired_but_bound_accounts)
                )

            conn.commit()

        total_updated = len(expired_accounts) + len(expired_but_bound_accounts)

        if total_updated > 0:
            operation_id = OperationLogOperations.log_operation(
                操作类型='自动更新生命周期状态',
                操作详情={
                    '标记为已过期': len(expired_accounts),
                    '标记为已过期但被绑定': len(expired_but_bound_accounts)
                },
                影响记录数=total_updated,
                执行状态='成功',
                操作人='系统自动'
            )

            for item in expired_accounts:
                AccountChangeLogOperations.log_account_change(
                    账号=item['账号'],
                    变更类型='状态变更',
                    变更字段='状态',
                    旧值=item.get('状态'),
                    新值='已过期',
                    关联学号=item.get('绑定的学号'),
                    操作来源='系统维护',
                    操作批次ID=operation_id,
                    备注='生命周期已结束'
                )

            for item in expired_but_bound_accounts:
                AccountChangeLogOperations.log_account_change(
                    账号=item['账号'],
                    变更类型='状态变更',
                    变更字段='状态',
                    旧值=item.get('状态'),
                    新值='已过期但被绑定',
                    关联学号=item.get('绑定的学号'),
                    操作来源='系统维护',
                    操作批次ID=operation_id,
                    备注='生命周期已结束但仍绑定'
                )

        return total_updated

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
        selection_query = '''
            SELECT 账号, 状态, 绑定的学号, 绑定的套餐到期日
            FROM isp_accounts
            WHERE 状态 = '已过期但被绑定'
              AND (绑定的套餐到期日 IS NULL OR 绑定的套餐到期日 < date('now', 'localtime'))
        '''

        targets: List[Dict[str, Any]] = []

        with db_manager.get_connection(enable_performance_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(selection_query)
            rows = cursor.fetchall()
            if not rows:
                conn.commit()
                return 0

            targets = [dict(row) for row in rows]
            placeholders = ','.join(['?'] * len(targets))
            cursor.execute(
                f'''
                UPDATE isp_accounts
                SET 状态 = '已过期', 更新时间 = datetime('now', 'localtime')
                WHERE 账号 IN ({placeholders})
                ''',
                tuple(item['账号'] for item in targets)
            )
            conn.commit()

        updated = len(targets)

        if updated > 0:
            operation_id = OperationLogOperations.log_operation(
                操作类型='自动恢复过期状态',
                操作详情={'账号数量': updated},
                影响记录数=updated,
                执行状态='成功',
                操作人='系统自动'
            )

            for item in targets:
                AccountChangeLogOperations.log_account_change(
                    账号=item['账号'],
                    变更类型='状态变更',
                    变更字段='状态',
                    旧值=item.get('状态'),
                    新值='已过期',
                    关联学号=item.get('绑定的学号'),
                    操作来源='系统维护',
                    操作批次ID=operation_id,
                    备注='套餐与生命周期均已到期'
                )

        return updated

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
            
            try:
                cursor.execute(duplicate_query)
                duplicate_accounts = cursor.fetchall()

                if not duplicate_accounts:
                    conn.commit()
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
                
            except Exception as e:
                conn.rollback()
                raise e

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
                    conn.rollback()
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
                    conn.rollback()
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

                conn.commit()
                return True, f"学号 {用户账号} 已换绑到账号 {new_account}", new_account

            except Exception as e:
                conn.rollback()
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

    @staticmethod
    def fix_data_integrity_issues() -> Dict[str, int]:
        """
        修复数据完整性问题
        - 孤立绑定：账号表显示已绑定但用户表中没有对应记录
        - 无效未使用：未使用状态的账号却有绑定信息
        - 无效已使用：已使用状态的账号却没有绑定信息
        """
        fixed_counts = {
            '孤立绑定': 0,
            '无效未使用': 0,
            '无效已使用': 0
        }
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 1. 修复孤立绑定 - 释放账号表中已绑定但用户表中没有记录的账号
                cursor.execute('''
                    UPDATE isp_accounts
                    SET 状态 = '未使用',
                        绑定的学号 = NULL,
                        绑定的套餐到期日 = NULL,
                        更新时间 = datetime('now', 'localtime')
                    WHERE 状态 = '已使用' 
                      AND 绑定的学号 IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM user_list ul 
                          WHERE ul.移动账号 = isp_accounts.账号 
                            AND ul.用户账号 = isp_accounts.绑定的学号
                      )
                ''')
                fixed_counts['孤立绑定'] = cursor.rowcount
                
                # 2. 修复无效未使用 - 清除未使用账号的绑定信息
                cursor.execute('''
                    UPDATE isp_accounts
                    SET 绑定的学号 = NULL,
                        绑定的套餐到期日 = NULL,
                        更新时间 = datetime('now', 'localtime')
                    WHERE 状态 = '未使用'
                      AND (绑定的学号 IS NOT NULL OR 绑定的套餐到期日 IS NOT NULL)
                ''')
                fixed_counts['无效未使用'] = cursor.rowcount
                
                # 3. 修复无效已使用 - 将已使用但无绑定信息的账号改为未使用
                cursor.execute('''
                    UPDATE isp_accounts
                    SET 状态 = '未使用',
                        更新时间 = datetime('now', 'localtime')
                    WHERE 状态 = '已使用'
                      AND 绑定的学号 IS NULL
                ''')
                fixed_counts['无效已使用'] = cursor.rowcount
                
                conn.commit()
                return fixed_counts
                
            except Exception as e:
                conn.rollback()
                print(f"修复数据完整性失败: {e}")
                raise e


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
