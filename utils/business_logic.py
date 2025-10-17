#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心业务逻辑模块
Core Business Logic
"""

from datetime import datetime, date
from typing import List, Dict, Tuple, Optional, Any
import logging
import os
import re
import json

# 导入数据库操作
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import (
    ISPAccountOperations, PaymentOperations, SystemSettingsOperations,
    MaintenanceOperations, AccountTypeRuleOperations,
    OperationLogOperations, AccountChangeLogOperations
)

# 导入Excel处理器
from utils.excel_handler import (
    account_processor, binding_processor, payment_processor, export_processor
)

# 导入日期工具
from utils.date_utils import date_calculator, business_date_helper


logger = logging.getLogger(__name__)


class AccountManager:
    """账号管理业务逻辑"""

    @staticmethod
    def import_accounts_from_excel(file_buffer, progress_callback=None) -> Dict[str, Any]:
        """从Excel导入账号（高性能批量版本）
        
        Args:
            file_buffer: Excel文件缓冲区
            progress_callback: 可选的进度回调函数，接收字典参数：
                {
                    'current': 当前进度,
                    'total': 总数,
                    'success': 成功数,
                    'failed': 失败数,
                    'message': 状态消息,
                    'step': 当前步骤
                }
        """
        return AccountManager._import_accounts_batch_optimized(file_buffer, progress_callback)

    @staticmethod
    def _import_accounts_batch_optimized(file_buffer, progress_callback=None) -> Dict[str, Any]:
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
            # 步骤1: 解析Excel文件
            if progress_callback:
                progress_callback({
                    'current': 0,
                    'total': 100,
                    'success': 0,
                    'failed': 0,
                    'message': '正在读取Excel文件...',
                    'step': '文件解析'
                })
            
            accounts_data, parsing_errors = account_processor.process_account_import(file_buffer)

            if parsing_errors:
                result['errors'].extend(parsing_errors)
                result['error_count'] = len(parsing_errors)

            if not accounts_data:
                result['message'] = "没有有效的账号数据"
                return result
            
            total_accounts = len(accounts_data)
            if progress_callback:
                progress_callback({
                    'current': 10,
                    'total': 100,
                    'success': 0,
                    'failed': 0,
                    'message': f'已读取 {total_accounts} 条账号数据',
                    'step': '数据预处理'
                })

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
            total_to_process = len(accounts_dict)
            processed_count = 0
            
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

                    # 应用账号类型规则
                    start_date, end_date = AccountTypeRuleOperations.calculate_lifecycle(
                        account_data['账号类型'],
                        start_date,
                        end_date
                    )

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
                    
                    processed_count += 1
                    
                    # 更新进度（每处理10个或完成时更新）
                    if progress_callback and (processed_count % 10 == 0 or processed_count == total_to_process):
                        progress_percent = 10 + int((processed_count / total_to_process) * 40)  # 10-50%
                        progress_callback({
                            'current': progress_percent,
                            'total': 100,
                            'success': processed_count,
                            'failed': result['error_count'],
                            'message': f'正在预处理账号: {account_data["账号"]}',
                            'step': '数据预处理'
                        })

                except Exception as e:
                    result['error_count'] += 1
                    result['errors'].append(f"账号 {account_data['账号']} 预处理异常: {e}")

            # 使用批量upsert操作
            if processed_accounts:
                try:
                    if progress_callback:
                        progress_callback({
                            'current': 50,
                            'total': 100,
                            'success': len(processed_accounts),
                            'failed': result['error_count'],
                            'message': '正在查询现有账号...',
                            'step': '数据库写入'
                        })
                    
                    account_ids = [item[0] for item in processed_accounts]
                    existing_accounts = {}
                    if account_ids:
                        chunk_size = 900
                        for index in range(0, len(account_ids), chunk_size):
                            chunk = account_ids[index:index + chunk_size]
                            placeholders = ','.join(['?'] * len(chunk))
                            query = f'''
                                SELECT 账号, 账号类型, 状态, 生命周期开始日期, 生命周期结束日期, 绑定的学号
                                FROM isp_accounts
                                WHERE 账号 IN ({placeholders})
                            '''
                            rows = db_manager.execute_query(query, tuple(chunk))
                            for row in rows:
                                existing_accounts[row['账号']] = row
                    
                    if progress_callback:
                        progress_callback({
                            'current': 70,
                            'total': 100,
                            'success': len(processed_accounts),
                            'failed': result['error_count'],
                            'message': f'正在写入 {len(processed_accounts)} 条账号数据...',
                            'step': '数据库写入'
                        })

                    affected_rows = db_manager.bulk_upsert_accounts(processed_accounts)
                    result['processed_count'] = affected_rows
                    result['success'] = affected_rows >= 0
                    result['message'] = f"批量处理完成：{affected_rows} 个账号"
                    
                    if progress_callback:
                        progress_callback({
                            'current': 90,
                            'total': 100,
                            'success': affected_rows,
                            'failed': result['error_count'],
                            'message': '正在记录操作日志...',
                            'step': '完成处理'
                        })

                    operation_id = OperationLogOperations.log_operation(
                        操作类型='导入账号',
                        操作人='系统自动',
                        操作详情={
                            '文件名': getattr(file_buffer, 'name', None),
                            '导入总数': len(processed_accounts),
                            '成功数': affected_rows,
                            '失败数': result['error_count']
                        },
                        影响记录数=affected_rows,
                        执行状态='成功' if affected_rows >= 0 else '失败'
                    )

                    for account_tuple in processed_accounts:
                        账号, 账号类型, 状态, start_date, end_date = account_tuple
                        new_values = {
                            '账号类型': 账号类型,
                            '状态': 状态,
                            '生命周期开始日期': start_date.isoformat() if isinstance(start_date, date) else start_date,
                            '生命周期结束日期': end_date.isoformat() if isinstance(end_date, date) else end_date
                        }

                        old_row = existing_accounts.get(账号)
                        if not old_row:
                            AccountChangeLogOperations.log_account_change(
                                账号=账号,
                                变更类型='创建',
                                变更字段='全部',
                                旧值=None,
                                新值=json.dumps(new_values, ensure_ascii=False),
                                操作来源='用户导入',
                                操作批次ID=operation_id
                            )
                            continue

                        for field, new_value in new_values.items():
                            AccountChangeLogOperations.log_account_change(
                                账号=账号,
                                变更类型='导入同步',
                                变更字段=field,
                                旧值=old_row.get(field),
                                新值=new_value,
                                关联学号=old_row.get('绑定的学号'),
                                操作来源='用户导入',
                                操作批次ID=operation_id
                            )

                except Exception as e:
                    result['message'] = f"批量数据库操作失败: {e}"
                    result['error_count'] += len(processed_accounts)

            if result['error_count'] > 0:
                result['message'] += f"，{result['error_count']} 个失败"
            
            # 最终进度回调
            if progress_callback:
                progress_callback({
                    'current': 100,
                    'total': 100,
                    'success': result['processed_count'],
                    'failed': result['error_count'],
                    'message': result['message'],
                    'step': '完成'
                })

        except Exception as e:
            result['message'] = f"导入失败: {e}"
            if progress_callback:
                progress_callback({
                    'current': 0,
                    'total': 100,
                    'success': 0,
                    'failed': 0,
                    'message': f'错误: {e}',
                    'step': '错误'
                })

        return result

    @staticmethod
    def sync_binding_details_from_excel(file_buffer, progress_callback=None) -> Dict[str, Any]:
        """从Excel同步绑定详情
        
        Args:
            file_buffer: Excel文件缓冲区
            progress_callback: 可选的进度回调函数
        """
        result = {
            'success': False,
            'message': '',
            'updated_count': 0,
            'released_count': 0,
            'error_count': 0,
            'errors': []
        }

        try:
            if progress_callback:
                progress_callback({
                    'current': 0,
                    'total': 100,
                    'success': 0,
                    'failed': 0,
                    'message': '正在读取Excel文件...',
                    'step': '文件解析'
                })
            
            # 解析Excel文件
            binding_data, parsing_errors = binding_processor.process_binding_import(file_buffer)

            if parsing_errors:
                result['errors'].extend(parsing_errors)
                result['error_count'] = len(parsing_errors)

            if not binding_data:
                result['message'] = "没有有效的绑定数据"
                return result
            
            total_bindings = len(binding_data)
            if progress_callback:
                progress_callback({
                    'current': 10,
                    'total': 100,
                    'success': 0,
                    'failed': 0,
                    'message': f'已读取 {total_bindings} 条绑定记录',
                    'step': '数据处理'
                })

            # 处理绑定数据
            expired_package_pattern = re.compile(r'^(本科|专科)20\d{2}')
            operation_id = OperationLogOperations.log_operation(
                操作类型='绑定同步',
                操作人='系统自动',
                操作详情={
                    '文件名': getattr(file_buffer, 'name', None),
                    '记录总数': len(binding_data)
                },
                执行状态='进行中'
            )

            for idx, binding in enumerate(binding_data, 1):
                try:
                    # 更新进度（每5条或完成时更新）
                    if progress_callback and (idx % 5 == 0 or idx == total_bindings):
                        progress_percent = 10 + int((idx / total_bindings) * 80)  # 10-90%
                        progress_callback({
                            'current': progress_percent,
                            'total': 100,
                            'success': result['updated_count'] + result['released_count'],
                            'failed': result['error_count'],
                            'message': f'正在处理: {binding.get("移动账号", "unknown")}',
                            'step': f'同步进度 - {idx}/{total_bindings}'
                        })
                    
                    package_label = binding.get('绑定资费组') or binding.get('绑定套餐')
                    if package_label and expired_package_pattern.match(package_label):
                        # 资费组标记为本科/专科202X，视为已到期，释放账号
                        if ISPAccountOperations.release_account(
                                binding['移动账号'],
                                log_context={
                                    '操作来源': '缴费绑定同步',
                                    '操作批次ID': operation_id,
                                    '关联学号': binding.get('用户账号')
                                }):
                            result['released_count'] += 1
                        else:
                            result['error_count'] += 1
                            result['errors'].append(
                                f"账号 {binding['移动账号']} 未找到可释放的绑定记录"
                            )
                        continue

                    # 查找对应的账号
                    account = ISPAccountOperations.get_account(binding['移动账号'])

                    if account:
                        # 更新账号绑定信息
                        success = ISPAccountOperations.update_account(
                            binding['移动账号'],
                            log_context={
                                '操作来源': '缴费绑定同步',
                                '操作批次ID': operation_id,
                                '关联学号': binding.get('用户账号')
                            },
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

            result['success'] = (result['updated_count'] + result['released_count']) > 0

            message_parts = []
            if result['updated_count'] > 0:
                message_parts.append(f"成功同步 {result['updated_count']} 条绑定记录")
            if result['released_count'] > 0:
                message_parts.append(f"释放 {result['released_count']} 个已到期绑定")
            if not message_parts:
                message_parts.append("未同步新的绑定记录")

            if result['error_count'] > 0:
                message_parts.append(f"{result['error_count']} 条失败")

            result['message'] = "，".join(message_parts)

            # 更新同步时间
            SystemSettingsOperations.set_setting(
                '上次数据校准时间',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )

            if operation_id:
                OperationLogOperations.update_operation_log(
                    operation_id,
                    操作详情={
                        '文件名': getattr(file_buffer, 'name', None),
                        '记录总数': len(binding_data),
                        '成功同步': result['updated_count'],
                        '释放账号': result['released_count'],
                        '失败条数': result['error_count']
                    },
                    影响记录数=result['updated_count'] + result['released_count'],
                    执行状态='成功' if result['success'] else '失败'
                )
            
            # 最终进度回调
            if progress_callback:
                progress_callback({
                    'current': 100,
                    'total': 100,
                    'success': result['updated_count'] + result['released_count'],
                    'failed': result['error_count'],
                    'message': result['message'],
                    'step': '完成'
                })

        except Exception as e:
            result['message'] = f"同步失败: {e}"
            operation_id = locals().get('operation_id')
            if operation_id:
                OperationLogOperations.update_operation_log(
                    operation_id,
                    执行状态='失败',
                    备注=str(e)
                )
            
            if progress_callback:
                progress_callback({
                    'current': 0,
                    'total': 100,
                    'success': 0,
                    'failed': 0,
                    'message': f'错误: {e}',
                    'step': '错误'
                })

        return result

    @staticmethod
    def recalculate_lifecycle_for_type(account_type: str) -> Dict[str, Any]:
        """根据规则重新计算指定账号类型的生命周期"""
        result = {
            'success': False,
            'message': '',
            'updated_count': 0
        }

        from datetime import datetime as _dt  # 避免与模块顶部命名冲突

        def _coerce_date(value: Any) -> Optional[date]:
            if value in (None, '', 'None'):
                return None
            if isinstance(value, date):
                return value
            try:
                return _dt.strptime(str(value), '%Y-%m-%d').date()
            except Exception:
                return None

        try:
            accounts = ISPAccountOperations.search_accounts(账号类型=account_type)
            if not accounts:
                result['message'] = "未找到对应账号"
                return result

            zero_cost_expiry = None
            if account_type == '0元账号':
                zero_cost_setting = SystemSettingsOperations.get_setting('0元账号有效期')
                if zero_cost_setting:
                    zero_cost_expiry = business_date_helper.get_zero_cost_account_expiry(zero_cost_setting)

            updated = 0
            today = date.today()

            for account in accounts:
                base_start, base_end = date_calculator.parse_account_type_to_dates(account_type)

                if base_start is None:
                    base_start = _coerce_date(account.get('生命周期开始日期'))

                if account_type == '0元账号' and zero_cost_expiry:
                    base_end = zero_cost_expiry

                if base_end is None:
                    base_end = _coerce_date(account.get('生命周期结束日期'))

                new_start, new_end = AccountTypeRuleOperations.calculate_lifecycle(
                    account_type,
                    base_start,
                    base_end
                )

                binding_student = account.get('绑定的学号')
                binding_expiry = _coerce_date(account.get('绑定的套餐到期日'))
                new_status = account.get('状态', '未使用')

                if new_end and new_end < today:
                    if binding_student:
                        if binding_expiry and binding_expiry >= today:
                            new_status = '已过期但被绑定'
                        else:
                            new_status = '已过期'
                    else:
                        new_status = '已过期'
                else:
                    if binding_student:
                        new_status = '已使用'
                    else:
                        new_status = '未使用'

                ISPAccountOperations.update_account(
                    account['账号'],
                    log_context={
                        '操作来源': '生命周期重算',
                        '关联学号': binding_student
                    },
                    生命周期开始日期=new_start,
                    生命周期结束日期=new_end,
                    状态=new_status
                )

                updated += 1

            result['success'] = True
            result['updated_count'] = updated
            result['message'] = f"已更新 {updated} 个账号的生命周期"
        except Exception as e:
            result['message'] = f"更新失败: {e}"

        return result


class PaymentProcessor:
    """缴费处理业务逻辑"""

    @staticmethod
    def import_payments_from_excel(file_buffer, progress_callback=None) -> Dict[str, Any]:
        """从Excel导入缴费记录
        
        Args:
            file_buffer: Excel文件缓冲区
            progress_callback: 可选的进度回调函数
        """
        result = {
            'success': False,
            'message': '',
            'new_count': 0,
            'error_count': 0,
            'errors': []
        }

        file_name = getattr(file_buffer, 'name', None)
        operation_id = OperationLogOperations.log_operation(
            操作类型='导入缴费记录',
            操作人='系统自动',
            操作详情={'文件名': file_name} if file_name else None,
            执行状态='进行中'
        )

        try:
            if progress_callback:
                progress_callback({
                    'current': 0,
                    'total': 100,
                    'success': 0,
                    'failed': 0,
                    'message': '正在读取Excel文件...',
                    'step': '文件解析'
                })
            
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
            
            total_payments = len(payment_data)
            if progress_callback:
                progress_callback({
                    'current': 20,
                    'total': 100,
                    'success': 0,
                    'failed': 0,
                    'message': f'已读取 {total_payments} 条缴费记录',
                    'step': '数据处理'
                })

            # 处理缴费数据
            latest_payment_time = None

            for idx, payment in enumerate(payment_data, 1):
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
                
                # 更新进度（每处理5条或完成时更新）
                if progress_callback and (idx % 5 == 0 or idx == total_payments):
                    progress_percent = 20 + int((idx / total_payments) * 70)  # 20-90%
                    progress_callback({
                        'current': progress_percent,
                        'total': 100,
                        'success': result['new_count'],
                        'failed': result['error_count'],
                        'message': f'正在处理学号: {payment.get("学号", "unknown")}',
                        'step': '数据写入'
                    })

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
            
            # 最终进度回调
            if progress_callback:
                progress_callback({
                    'current': 100,
                    'total': 100,
                    'success': result['new_count'],
                    'failed': result['error_count'],
                    'message': result['message'],
                    'step': '完成'
                })

        except Exception as e:
            result['message'] = f"导入失败: {e}"
            if progress_callback:
                progress_callback({
                    'current': 0,
                    'total': 100,
                    'success': 0,
                    'failed': 0,
                    'message': f'错误: {e}',
                    'step': '错误'
                })

        finally:
            if operation_id:
                detail_payload = {
                    '文件名': file_name,
                    '新增记录数': result['new_count'],
                    '失败记录数': result['error_count']
                }
                if locals().get('latest_payment_time'):
                    detail_payload['最新缴费时间'] = latest_payment_time.strftime('%Y-%m-%d %H:%M:%S')
                if result['errors']:
                    detail_payload['错误示例'] = result['errors'][:5]

                OperationLogOperations.update_operation_log(
                    operation_id,
                    操作详情=detail_payload,
                    影响记录数=result['new_count'],
                    执行状态='成功' if result['success'] else '失败',
                    备注=None if result['success'] else result['message']
                )

        return result

    @staticmethod
    def process_pending_payments_and_generate_export(progress_callback=None) -> Dict[str, Any]:
        """处理待处理的缴费记录并生成导出文件
        
        Args:
            progress_callback: 可选的进度回调函数，用于实时更新处理进度
        """
        result = {
            'success': False,
            'message': '',
            'processed_count': 0,
            'failed_count': 0,
            'export_file': None,
            'binding_data': []
        }

        try:
            logger.info("开始处理待处理的缴费记录...")
            
            if progress_callback:
                progress_callback({
                    'current': 0,
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'message': '正在获取待处理的缴费记录...',
                    'step': '初始化'
                })
            
            # 获取待处理的缴费记录
            pending_payments = PaymentOperations.get_pending_payments()
            logger.info(f"找到 {len(pending_payments)} 条待处理缴费记录")

            operation_id = OperationLogOperations.log_operation(
                操作类型='执行绑定任务',
                操作人='系统自动',
                操作详情={'待处理条数': len(pending_payments)},
                执行状态='进行中'
            )

            if not pending_payments:
                result['message'] = "没有待处理的缴费记录"
                logger.warning("没有待处理的缴费记录")
                if operation_id:
                    OperationLogOperations.update_operation_log(
                        operation_id,
                        操作详情={'待处理条数': 0, '成功绑定': 0, '失败条数': 0},
                        影响记录数=0,
                        执行状态='成功',
                        备注='无需处理'
                    )
                return result

            total_payments = len(pending_payments)
            binding_pairs = []
            
            if progress_callback:
                progress_callback({
                    'current': 0,
                    'total': total_payments,
                    'success': 0,
                    'failed': 0,
                    'message': f'准备处理 {total_payments} 条缴费记录',
                    'step': '开始处理'
                })

            for idx, payment in enumerate(pending_payments, 1):
                try:
                    if progress_callback:
                        progress_callback({
                            'current': idx,
                            'total': total_payments,
                            'success': result['processed_count'],
                            'failed': result['failed_count'],
                            'message': f'正在处理学号: {payment["学号"]}',
                            'step': f'处理第 {idx}/{total_payments} 条'
                        })
                    
                    # 根据缴费金额计算套餐类型和到期日期
                    套餐类型, 到期日期 = date_calculator.calculate_subscription_expiry(
                        payment['缴费时间'], payment['缴费金额']
                    )
                    
                    if progress_callback:
                        progress_callback({
                            'current': idx,
                            'total': total_payments,
                            'success': result['processed_count'],
                            'failed': result['failed_count'],
                            'message': f'查找可用账号 (学号: {payment["学号"]})',
                            'step': f'查找账号 - {idx}/{total_payments}'
                        })

                    # 寻找可用账号
                    available_accounts = ISPAccountOperations.get_available_accounts(limit=1)

                    if available_accounts:
                        account = available_accounts[0]
                        
                        if progress_callback:
                            progress_callback({
                                'current': idx,
                                'total': total_payments,
                                'success': result['processed_count'],
                                'failed': result['failed_count'],
                                'message': f'绑定账号 {account["账号"]} 到学号 {payment["学号"]}',
                                'step': f'执行绑定 - {idx}/{total_payments}'
                            })

                        # 使用事务确保所有操作的原子性
                        from database.models import db_manager
                        
                        try:
                            with db_manager.get_connection() as conn:
                                cursor = conn.cursor()
                                
                                try:
                                    # 1. 检查用户是否存在于用户列表
                                    cursor.execute(
                                        'SELECT 用户账号 FROM user_list WHERE 用户账号 = ?',
                                        (payment['学号'],)
                                    )
                                    user_exists = cursor.fetchone()
                                    
                                    if not user_exists:
                                        raise Exception(f"学号 {payment['学号']} 不存在于用户列表中")
                                    
                                    # 2. 更新账号表 - 绑定账号到学生
                                    cursor.execute(
                                        '''
                                        UPDATE isp_accounts
                                        SET 状态 = '已使用',
                                            绑定的学号 = ?,
                                            绑定的套餐到期日 = ?,
                                            更新时间 = datetime('now', 'localtime')
                                        WHERE 账号 = ?
                                        ''',
                                        (payment['学号'], 到期日期, account['账号'])
                                    )
                                    
                                    if cursor.rowcount == 0:
                                        raise Exception(f"账号 {account['账号']} 更新失败")
                                    
                                    # 3. 清理之前占用同一账号的其他用户记录
                                    cursor.execute(
                                        '''
                                        UPDATE user_list
                                        SET 移动账号 = NULL,
                                            更新时间 = datetime('now', 'localtime')
                                        WHERE 移动账号 = ?
                                          AND 用户账号 != ?
                                        ''',
                                        (account['账号'], payment['学号'])
                                    )
                                    
                                    # 4. 更新用户列表 - 设置移动账号、套餐类型、到期日期
                                    cursor.execute(
                                        '''
                                        UPDATE user_list
                                        SET 移动账号 = ?, 联通账号 = NULL, 电信账号 = NULL,
                                            绑定套餐 = ?, 到期日期 = ?,
                                            更新时间 = datetime('now', 'localtime')
                                        WHERE 用户账号 = ?
                                        ''',
                                        (account['账号'], 套餐类型, 到期日期, payment['学号'])
                                    )
                                    
                                    if cursor.rowcount == 0:
                                        raise Exception(f"学号 {payment['学号']} 用户列表更新失败")
                                    
                                    # 5. 更新缴费记录状态
                                    cursor.execute(
                                        '''
                                        UPDATE payment_logs
                                        SET 处理状态 = '已处理',
                                            处理时间 = datetime('now', 'localtime')
                                        WHERE 记录ID = ?
                                        ''',
                                        (payment['记录ID'],)
                                    )
                                    
                                    # 提交事务
                                    conn.commit()
                                    
                                    AccountChangeLogOperations.log_multiple_changes(
                                        账号=account['账号'],
                                        changes=[
                                            {
                                                '变更类型': '状态变更',
                                                '变更字段': '状态',
                                                '旧值': account.get('状态'),
                                                '新值': '已使用'
                                            },
                                            {
                                                '变更类型': '绑定',
                                                '变更字段': '绑定的学号',
                                                '旧值': account.get('绑定的学号'),
                                                '新值': payment['学号']
                                            },
                                            {
                                                '变更类型': '绑定',
                                                '变更字段': '绑定的套餐到期日',
                                                '旧值': account.get('绑定的套餐到期日'),
                                                '新值': 到期日期
                                            }
                                        ],
                                        关联学号=payment['学号'],
                                        操作来源='缴费绑定',
                                        操作批次ID=operation_id,
                                        备注=f"缴费金额: {payment['缴费金额']}"
                                    )

                                    # 添加到导出数据
                                    binding_pairs.append({
                                        '学号': payment['学号'],
                                        '移动账号': account['账号'],
                                        '套餐类型': 套餐类型,
                                        '到期日期': 到期日期.strftime('%Y-%m-%d') if 到期日期 else '',
                                        '缴费金额': payment['缴费金额']
                                    })
                                    result['processed_count'] += 1
                                    
                                except Exception as tx_error:
                                    # 回滚事务
                                    conn.rollback()
                                    raise tx_error
                                    
                        except Exception as e:
                            error_msg = f"绑定失败，账号 {account['账号']}、学号 {payment['学号']}，原因: {str(e)}"
                            logger.warning(error_msg)
                            print(f"⚠️ {error_msg}")
                            PaymentOperations.update_payment_status(
                                payment['记录ID'], '处理失败'
                            )
                            result['failed_count'] += 1
                    else:
                        error_msg = f"未找到可用账号，学号 {payment['学号']}、缴费金额 {payment['缴费金额']:.2f}"
                        logger.warning(error_msg)
                        print(f"⚠️ {error_msg}")
                        # 没有可用账号
                        PaymentOperations.update_payment_status(
                            payment['记录ID'], '处理失败'
                        )
                        result['failed_count'] += 1

                except Exception as e:
                    error_msg = f"处理缴费记录失败，学号 {payment.get('学号')}、缴费金额 {payment.get('缴费金额', 0.0):.2f}，错误: {str(e)}"
                    logger.exception(error_msg)
                    print(f"❌ {error_msg}")
                    PaymentOperations.update_payment_status(
                        payment['记录ID'], '处理失败'
                    )
                    result['failed_count'] += 1

            # 强制同步数据库到磁盘,确保所有事务已提交
            if progress_callback:
                progress_callback({
                    'current': total_payments,
                    'total': total_payments,
                    'success': result['processed_count'],
                    'failed': result['failed_count'],
                    'message': '正在同步数据库...',
                    'step': '数据库同步'
                })
            
            try:
                from database.models import db_manager
                with db_manager.get_connection() as conn:
                    # WAL checkpoint - 将WAL日志刷新到主数据库文件
                    conn.execute("PRAGMA wal_checkpoint(FULL)")
                    conn.commit()
                logger.info("数据库WAL checkpoint完成")
            except Exception as e:
                logger.warning(f"WAL checkpoint失败: {e}")

            # 生成导出文件
            if binding_pairs:
                if progress_callback:
                    progress_callback({
                        'current': total_payments,
                        'total': total_payments,
                        'success': result['processed_count'],
                        'failed': result['failed_count'],
                        'message': '正在生成导出文件...',
                        'step': '生成导出文件'
                    })
                
                try:
                    export_filename = f'绑定导��_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                    logger.info(f"开始生成导出文件: {export_filename}")
                    export_path = export_processor.create_binding_export_file(
                        binding_pairs, export_filename
                    )
                    result['export_file'] = export_path
                    result['binding_data'] = binding_pairs
                    logger.info(f"导出文件生成成功: {export_path}")

                    OperationLogOperations.log_operation(
                        操作类型='生成导出文件',
                        操作人='系统自动',
                        操作详情={
                            '文件名': export_filename,
                            '记录数': len(binding_pairs),
                            '关联绑定批次': operation_id
                        },
                        影响记录数=len(binding_pairs),
                        执行状态='成功'
                    )
                except Exception as e:
                    error_msg = f"导出文件生成失败: {e}"
                    logger.error(error_msg)
                    print(f"❌ {error_msg}")
                    result['message'] += f"; {error_msg}"

            result['success'] = result['processed_count'] > 0
            result['message'] = f"成功绑定 {result['processed_count']} 个账号"
            
            if progress_callback:
                progress_callback({
                    'current': total_payments,
                    'total': total_payments,
                    'success': result['processed_count'],
                    'failed': result['failed_count'],
                    'message': result['message'],
                    'step': '完成'
                })
            
            logger.info(f"处理完成: {result['message']}")
            print(f"✅ {result['message']}")

            if result['failed_count'] > 0:
                result['message'] += f"，{result['failed_count']} 个失败"
                logger.warning(f"有 {result['failed_count']} 个绑定失败")

            if operation_id:
                OperationLogOperations.update_operation_log(
                    operation_id,
                    操作详情={
                        '待处理条数': total_payments,
                        '成功绑定': result['processed_count'],
                        '失败条数': result['failed_count'],
                        '导出文件': result.get('export_file')
                    },
                    影响记录数=result['processed_count'],
                    执行状态='成功' if result['success'] else '失败',
                    备注=None if result['success'] else result['message']
                )

        except Exception as e:
            error_msg = f"处理失败: {e}"
            result['message'] = error_msg
            logger.exception(error_msg)
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            if progress_callback:
                progress_callback({
                    'current': 0,
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'message': f'错误: {e}',
                    'step': '错误'
                })

            operation_id = locals().get('operation_id')
            if operation_id:
                OperationLogOperations.update_operation_log(
                    operation_id,
                    操作详情={'错误': str(e)},
                    影响记录数=result['processed_count'],
                    执行状态='失败',
                    备注=result['message']
                )

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
