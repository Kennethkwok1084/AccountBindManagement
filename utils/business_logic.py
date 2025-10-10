#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心业务逻辑模块
Core Business Logic
"""

from datetime import datetime, date
from typing import List, Dict, Tuple, Optional, Any
import os

# 导入数据库操作
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import (
    ISPAccountOperations, PaymentOperations, SystemSettingsOperations,
    MaintenanceOperations
)

# 导入Excel处理器
from utils.excel_handler import (
    account_processor, binding_processor, payment_processor, export_processor
)

# 导入日期工具
from utils.date_utils import date_calculator, business_date_helper


class AccountManager:
    """账号管理业务逻辑"""

    @staticmethod
    def import_accounts_from_excel(file_buffer) -> Dict[str, Any]:
        """从Excel导入账号（高性能批量版本）"""
        return AccountManager._import_accounts_batch_optimized(file_buffer)

    @staticmethod
    def _import_accounts_batch_optimized(file_buffer) -> Dict[str, Any]:
        """批量优化的账号导入逻辑"""
        from database.models import db_manager

        result = {
            'success': False,
            'message': '',
            'processed_count': 0,
            'error_count': 0,
            'errors': []
        }

        try:
            # 解析Excel文件
            accounts_data, parsing_errors = account_processor.process_account_import(file_buffer)

            if parsing_errors:
                result['errors'].extend(parsing_errors)
                result['error_count'] = len(parsing_errors)

            if not accounts_data:
                result['message'] = "没有有效的账号数据"
                return result

            # 按账号分组，处理重复记录，以最新生命周期为准
            accounts_dict = {}
            for account_data in accounts_data:
                账号 = account_data['账号']
                账号类型 = account_data['账号类型']

                # 解析账号类型获取生命周期时间
                account_time = None
                if 账号类型 and 账号类型 != '0元账号':
                    try:
                        import re
                        match = re.match(r'(\d{6})', 账号类型.strip())
                        if match:
                            account_time = int(match.group(1))
                    except:
                        pass

                if 账号 in accounts_dict:
                    existing_time = accounts_dict[账号].get('_account_time', 0)
                    current_time = account_time or 0
                    if current_time > existing_time:
                        accounts_dict[账号] = account_data
                        accounts_dict[账号]['_account_time'] = current_time
                else:
                    accounts_dict[账号] = account_data
                    accounts_dict[账号]['_account_time'] = account_time or 0

            # 预处理所有账号数据
            processed_accounts = []
            for account_data in accounts_dict.values():
                try:
                    # 计算生命周期日期
                    start_date, end_date = date_calculator.parse_account_type_to_dates(
                        account_data['账号类型']
                    )

                    # 处理0元账号的特殊情况
                    if account_data['账号类型'] == '0元账号':
                        zero_cost_expiry = SystemSettingsOperations.get_setting('0元账号有效期')
                        if zero_cost_expiry:
                            end_date = business_date_helper.get_zero_cost_account_expiry(zero_cost_expiry)

                    # 状态处理逻辑
                    原始状态 = account_data['状态']
                    最终状态 = 原始状态

                    # 如果状态为空，需要判断生命周期
                    if not 原始状态 or 原始状态.lower() in ['nan', '', 'null', 'none']:
                        if end_date:
                            if business_date_helper.should_auto_expire_account(end_date):
                                最终状态 = '已停机'
                            else:
                                最终状态 = '未使用'
                        else:
                            最终状态 = '未使用'

                    processed_accounts.append((
                        account_data['账号'],
                        account_data['账号类型'],
                        最终状态,
                        start_date,
                        end_date
                    ))

                except Exception as e:
                    result['error_count'] += 1
                    result['errors'].append(f"账号 {account_data['账号']} 预处理异常: {e}")

            # 使用批量upsert操作
            if processed_accounts:
                try:
                    affected_rows = db_manager.bulk_upsert_accounts(processed_accounts)
                    result['processed_count'] = affected_rows
                    result['success'] = True
                    result['message'] = f"批量处理完成：{affected_rows} 个账号"

                except Exception as e:
                    result['message'] = f"批量数据库操作失败: {e}"
                    result['error_count'] += len(processed_accounts)

            if result['error_count'] > 0:
                result['message'] += f"，{result['error_count']} 个失败"

        except Exception as e:
            result['message'] = f"导入失败: {e}"

        return result

    @staticmethod
    def sync_binding_details_from_excel(file_buffer) -> Dict[str, Any]:
        """从Excel同步绑定详情"""
        result = {
            'success': False,
            'message': '',
            'updated_count': 0,
            'error_count': 0,
            'errors': []
        }

        try:
            # 解析Excel文件
            binding_data, parsing_errors = binding_processor.process_binding_import(file_buffer)

            if parsing_errors:
                result['errors'].extend(parsing_errors)
                result['error_count'] = len(parsing_errors)

            if not binding_data:
                result['message'] = "没有有效的绑定数据"
                return result

            # 处理绑定数据
            for binding in binding_data:
                try:
                    # 查找对应的账号
                    account = ISPAccountOperations.get_account(binding['移动账号'])

                    if account:
                        # 更新账号绑定信息
                        success = ISPAccountOperations.update_account(
                            binding['移动账号'],
                            状态='已使用',
                            绑定的学号=binding['用户账号'],
                            绑定的套餐到期日=binding['到期日期']
                        )

                        if success:
                            result['updated_count'] += 1
                        else:
                            result['error_count'] += 1
                            result['errors'].append(f"更新账号 {binding['移动账号']} 失败")
                    else:
                        result['error_count'] += 1
                        result['errors'].append(f"账号 {binding['移动账号']} 不存在")

                except Exception as e:
                    result['error_count'] += 1
                    result['errors'].append(f"绑定记录处理异常: {e}")

            result['success'] = result['updated_count'] > 0
            result['message'] = f"成功同步 {result['updated_count']} 条绑定记录"

            if result['error_count'] > 0:
                result['message'] += f"，{result['error_count']} 条失败"

            # 更新同步时间
            SystemSettingsOperations.set_setting(
                '上次数据校准时间',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )

        except Exception as e:
            result['message'] = f"同步失败: {e}"

        return result


class PaymentProcessor:
    """缴费处理业务逻辑"""

    @staticmethod
    def import_payments_from_excel(file_buffer) -> Dict[str, Any]:
        """从Excel导入缴费记录"""
        result = {
            'success': False,
            'message': '',
            'new_count': 0,
            'error_count': 0,
            'errors': []
        }

        try:
            # 获取上次导入时间
            last_import_time_str = SystemSettingsOperations.get_setting('上次缴费导入时间')
            last_import_time = None

            if last_import_time_str and last_import_time_str != '1970-01-01 00:00:00':
                try:
                    last_import_time = datetime.strptime(last_import_time_str, '%Y-%m-%d %H:%M:%S')
                except:
                    pass

            # 解析Excel文件
            payment_data, parsing_errors = payment_processor.process_payment_import(
                file_buffer, last_import_time
            )

            if parsing_errors:
                result['errors'].extend(parsing_errors)
                result['error_count'] = len(parsing_errors)

            if not payment_data:
                result['message'] = "没有新的缴费记录"
                return result

            # 处理缴费数据
            latest_payment_time = None

            for payment in payment_data:
                try:
                    payment_id = PaymentOperations.add_payment(
                        payment['学号'],
                        payment['缴费时间'],
                        payment['缴费金额']
                    )

                    if payment_id:
                        result['new_count'] += 1
                        # 记录最新的缴费时间
                        if latest_payment_time is None or payment['缴费时间'] > latest_payment_time:
                            latest_payment_time = payment['缴费时间']
                    else:
                        result['error_count'] += 1
                        result['errors'].append(f"学号 {payment['学号']} 缴费记录添加失败")

                except Exception as e:
                    result['error_count'] += 1
                    result['errors'].append(f"缴费记录处理异常: {e}")

            result['success'] = result['new_count'] > 0
            result['message'] = f"成功导入 {result['new_count']} 条新缴费记录"

            if result['error_count'] > 0:
                result['message'] += f"，{result['error_count']} 条失败"

            # 更新导入时间
            if latest_payment_time:
                SystemSettingsOperations.set_setting(
                    '上次缴费导入时间',
                    latest_payment_time.strftime('%Y-%m-%d %H:%M:%S')
                )

        except Exception as e:
            result['message'] = f"导入失败: {e}"

        return result

    @staticmethod
    def process_pending_payments_and_generate_export() -> Dict[str, Any]:
        """处理待处理的缴费记录并生成导出文件"""
        result = {
            'success': False,
            'message': '',
            'processed_count': 0,
            'failed_count': 0,
            'export_file': None,
            'binding_data': []
        }

        try:
            # 获取待处理的缴费记录
            pending_payments = PaymentOperations.get_pending_payments()

            if not pending_payments:
                result['message'] = "没有待处理的缴费记录"
                return result

            binding_pairs = []

            for payment in pending_payments:
                try:
                    # 根据缴费金额计算套餐类型和到期日期
                    套餐类型, 到期日期 = date_calculator.calculate_subscription_expiry(
                        payment['缴费时间'], payment['缴费金额']
                    )

                    # 寻找可用账号
                    available_accounts = ISPAccountOperations.get_available_accounts(limit=1)

                    if available_accounts:
                        account = available_accounts[0]

                        # 绑定账号到学生，并设置套餐到期日
                        bind_success = ISPAccountOperations.update_account(
                            account['账号'],
                            状态='已使用',
                            绑定的学号=payment['学号'],
                            绑定的套餐到期日=到期日期
                        )

                        if bind_success:
                            # 清理之前占用同一账号的用户记录，避免重复绑定
                            from database.models import db_manager
                            db_manager.execute_update(
                                '''
                                UPDATE user_list
                                SET 移动账号 = NULL,
                                    更新时间 = datetime('now', 'localtime')
                                WHERE 移动账号 = ?
                                  AND 用户账号 != ?
                                ''',
                                (account['账号'], payment['学号'])
                            )

                            # 更新用户列表：设置移动账号、套餐类型、到期日期
                            db_manager.execute_update('''
                                UPDATE user_list
                                SET 移动账号 = ?, 联通账号 = NULL, 电信账号 = NULL,
                                    绑定套餐 = ?, 到期日期 = ?,
                                    更新时间 = datetime('now', 'localtime')
                                WHERE 用户账号 = ?
                            ''', (account['账号'], 套餐类型, 到期日期, payment['学号']))

                            # 更新缴费记录状态
                            PaymentOperations.update_payment_status(
                                payment['记录ID'], '已处理'
                            )

                            # 添加到导出数据（包含套餐信息）
                            binding_pairs.append({
                                '学号': payment['学号'],
                                '移动账号': account['账号'],
                                '套餐类型': 套餐类型,
                                '到期日期': 到期日期.strftime('%Y-%m-%d') if 到期日期 else '',
                                '缴费金额': payment['缴费金额']
                            })
                            result['processed_count'] += 1
                        else:
                            PaymentOperations.update_payment_status(
                                payment['记录ID'], '处理失败'
                            )
                            result['failed_count'] += 1
                    else:
                        # 没有可用账号
                        PaymentOperations.update_payment_status(
                            payment['记录ID'], '处理失败'
                        )
                        result['failed_count'] += 1

                except Exception as e:
                    PaymentOperations.update_payment_status(
                        payment['记录ID'], '处理失败'
                    )
                    result['failed_count'] += 1

            # 生成导出文件
            if binding_pairs:
                try:
                    export_filename = f'绑定导出_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                    export_path = export_processor.create_binding_export_file(
                        binding_pairs, export_filename
                    )
                    result['export_file'] = export_path
                    result['binding_data'] = binding_pairs
                except Exception as e:
                    result['message'] += f"; 导出文件生成失败: {e}"

            result['success'] = result['processed_count'] > 0
            result['message'] = f"成功绑定 {result['processed_count']} 个账号"

            if result['failed_count'] > 0:
                result['message'] += f"，{result['failed_count']} 个失败"

        except Exception as e:
            result['message'] = f"处理失败: {e}"

        return result


class SystemMaintenance:
    """系统维护业务逻辑"""

    @staticmethod
    def run_daily_maintenance() -> Dict[str, Any]:
        """执行每日维护任务"""
        result = {
            'success': False,
            'message': '',
            'released_count': 0,
            'expired_count': 0,
            'subscription_expired_count': 0,
            'converted_count': 0,
            'duplicate_group_count': 0,
            'rebind_count': 0,
            'cleared_count': 0
        }

        try:
            (released_count,
             expired_count,
             subscription_expired_count,
             converted_count,
             duplicate_group_count,
             rebind_count,
             cleared_count) = MaintenanceOperations.run_daily_maintenance()

            result['released_count'] = released_count
            result['expired_count'] = expired_count
            result['subscription_expired_count'] = subscription_expired_count
            result['converted_count'] = converted_count
            result['duplicate_group_count'] = duplicate_group_count
            result['rebind_count'] = rebind_count
            result['cleared_count'] = cleared_count
            result['success'] = True

            # 构建维护摘要消息
            messages = []
            if released_count > 0:
                messages.append(f"释放 {released_count} 个过期绑定")
            if expired_count > 0:
                messages.append(f"标记 {expired_count} 个过期账号")
            if subscription_expired_count > 0:
                messages.append(f"标记 {subscription_expired_count} 个到期套餐")
            if converted_count > 0:
                messages.append(f"转换 {converted_count} 个已过期但被绑定账号")
            if rebind_count > 0:
                messages.append(f"换绑 {rebind_count} 个重复移动账号")
            if cleared_count > 0:
                messages.append(f"清理 {cleared_count} 个无法换绑的重复记录")

            result['message'] = "、".join(messages) if messages else "无需维护"

        except Exception as e:
            result['message'] = f"维护任务执行失败: {e}"

        return result

    @staticmethod
    def get_system_status() -> Dict[str, Any]:
        """获取系统状态信息"""
        try:
            # 获取数据库统计
            from database.models import get_db_stats
            stats = get_db_stats()

            # 获取系统设置
            settings = {
                '上次缴费导入时间': SystemSettingsOperations.get_setting('上次缴费导入时间'),
                '上次用户列表导入时间': SystemSettingsOperations.get_setting('上次用户列表导入时间'),
                '上次数据校准时间': SystemSettingsOperations.get_setting('上次数据校准时间'),
                '上次自动维护执行时间': SystemSettingsOperations.get_setting('上次自动维护执行时间'),
                '0元账号启用状态': SystemSettingsOperations.get_setting('0元账号启用状态'),
                '0元账号有效期': SystemSettingsOperations.get_setting('0元账号有效期')
            }

            return {
                'stats': stats,
                'settings': settings
            }

        except Exception as e:
            return {
                'error': f"获取系统状态失败: {e}"
            }


# 创建业务逻辑实例
account_manager = AccountManager()
payment_processor_logic = PaymentProcessor()
system_maintenance = SystemMaintenance()


if __name__ == "__main__":
    # 测试业务逻辑
    print("业务逻辑模块测试...")

    # 测试系统状态
    status = system_maintenance.get_system_status()
    print("系统状态:", status)

    print("业务逻辑模块初始化完成")
