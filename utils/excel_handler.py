#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel文件处理工具
Excel File Handler
"""

import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Any
import io
import os


class ExcelProcessor:
    """Excel处理基类"""

    @staticmethod
    def read_excel_file(file_path_or_buffer, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """读取Excel文件，优先使用calamine引擎提升性能"""
        try:
            # 如果sheet_name是None，使用默认值0读取第一个工作表
            if sheet_name is None:
                sheet_name = 0

            # 尝试使用calamine引擎（性能更高）
            try:
                if isinstance(file_path_or_buffer, str):
                    # 文件路径
                    df = pd.read_excel(file_path_or_buffer, sheet_name=sheet_name, engine='calamine')
                else:
                    # 处理Streamlit上传的文件对象或文件缓冲区
                    # 重置文件指针到开头
                    if hasattr(file_path_or_buffer, 'seek'):
                        file_path_or_buffer.seek(0)
                    df = pd.read_excel(file_path_or_buffer, sheet_name=sheet_name, engine='calamine')

                # print("✅ 使用calamine引擎解析Excel")

            except Exception as calamine_error:
                # 降级到openpyxl引擎
                # print(f"⚠️ calamine解析失败，降级到openpyxl: {calamine_error}")

                if isinstance(file_path_or_buffer, str):
                    df = pd.read_excel(file_path_or_buffer, sheet_name=sheet_name, engine='openpyxl')
                else:
                    if hasattr(file_path_or_buffer, 'seek'):
                        file_path_or_buffer.seek(0)
                    df = pd.read_excel(file_path_or_buffer, sheet_name=sheet_name, engine='openpyxl')

            # 验证返回的是DataFrame
            if not isinstance(df, pd.DataFrame):
                raise ValueError(f"pandas.read_excel返回了意外的类型: {type(df)}，这通常是因为sheet_name参数问题")

            # 强力清理列名（去除所有不可见字符）
            if hasattr(df, 'columns'):
                # 清理步骤：
                # 1. 转为字符串
                # 2. 去除 BOM (U+FEFF)
                # 3. 去除首尾空白字符
                # 4. 去除零宽字符和其他不可见字符
                cleaned_columns = []
                for col in df.columns:
                    col_str = str(col)
                    # 去除 BOM 和其他不可见字符
                    col_str = col_str.replace('\ufeff', '')  # BOM
                    col_str = col_str.replace('\u200b', '')  # 零宽空格
                    col_str = col_str.replace('\xa0', ' ')   # 不间断空格转为普通空格
                    col_str = col_str.strip()  # 去除首尾空白
                    cleaned_columns.append(col_str)

                df.columns = cleaned_columns

                # 打印调试信息（可选）
                # print(f"原始列名: {list(df.columns)}")
                # print(f"清理后列名: {cleaned_columns}")
            else:
                raise ValueError(f"返回的对象没有columns属性: {type(df)}")

            return df
        except Exception as e:
            raise ValueError(f"读取Excel文件失败: {e}")

    @staticmethod
    def save_to_excel(data: List[Dict[str, Any]], filename: str, sheet_name: str = 'Sheet1') -> str:
        """将数据保存为Excel文件"""
        try:
            df = pd.DataFrame(data)
            output_path = os.path.join('data', filename)

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            df.to_excel(output_path, sheet_name=sheet_name, index=False)
            return output_path
        except Exception as e:
            raise ValueError(f"保存Excel文件失败: {e}")


class AccountExcelProcessor(ExcelProcessor):
    """账号Excel处理器"""

    def __init__(self):
        # 定义必需的列名
        self.required_columns = ['移动账户', '账号类型']
        self.optional_columns = ['使用状态']

    def process_account_import(self, file_buffer) -> Tuple[List[Dict[str, Any]], List[str]]:
        """处理账号导入Excel文件"""
        try:
            df = self.read_excel_file(file_buffer)
            errors = []

            # 验证必需列
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"缺少必需列: {', '.join(missing_columns)}")

            # 处理数据
            processed_accounts = []

            for index, row in df.iterrows():
                try:
                    account_data = {
                        '账号': str(row['移动账户']).strip(),
                        '账号类型': str(row['账号类型']).strip(),
                        '状态': str(row.get('使用状态', '未使用')).strip()
                    }

                    # 数据验证
                    if not account_data['账号']:
                        errors.append(f"第{index+2}行: 移动账户不能为空")
                        continue

                    if not account_data['账号类型']:
                        errors.append(f"第{index+2}行: 账号类型不能为空")
                        continue

                    processed_accounts.append(account_data)

                except Exception as e:
                    errors.append(f"第{index+2}行处理错误: {e}")

            return processed_accounts, errors

        except Exception as e:
            return [], [f"文件处理错误: {e}"]


class BindingExcelProcessor(ExcelProcessor):
    """绑定详情Excel处理器"""

    def __init__(self):
        self.required_columns = ['用户账号', '移动账号', '到期日期']
        self.optional_columns = ['绑定套餐', '绑定资费组']

    def process_binding_import(self, file_buffer) -> Tuple[List[Dict[str, Any]], List[str]]:
        """处理绑定详情Excel文件"""
        try:
            df = self.read_excel_file(file_buffer)
            errors = []

            # 验证必需列
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"缺少必需列: {', '.join(missing_columns)}")

            processed_bindings = []

            for index, row in df.iterrows():
                try:
                    # 过滤掉移动账号为空的记录
                    移动账号 = str(row.get('移动账号', '')).strip()
                    if not 移动账号 or 移动账号.lower() in ['nan', 'none', '']:
                        continue

                    binding_data = {
                        '用户账号': str(row['用户账号']).strip(),
                        '移动账号': 移动账号,
                        '到期日期': self._parse_date(row['到期日期']),
                        '绑定套餐': str(row.get('绑定套餐', '')).strip(),
                        '绑定资费组': str(row.get('绑定资费组', '')).strip()
                    }

                    processed_bindings.append(binding_data)

                except Exception as e:
                    errors.append(f"第{index+2}行处理错误: {e}")

            return processed_bindings, errors

        except Exception as e:
            return [], [f"文件处理错误: {e}"]

    def _parse_date(self, date_value) -> Optional[date]:
        """解析日期"""
        if pd.isna(date_value):
            return None

        if isinstance(date_value, datetime):
            return date_value.date()

        if isinstance(date_value, date):
            return date_value

        # 尝试解析字符串日期
        try:
            return datetime.strptime(str(date_value), '%Y-%m-%d').date()
        except:
            try:
                return datetime.strptime(str(date_value), '%Y/%m/%d').date()
            except:
                return None


class PaymentExcelProcessor(ExcelProcessor):
    """缴费Excel处理器"""

    def __init__(self, auto_convert_utc_to_beijing=False):
        self.required_columns = ['用户账号', '收费时间']
        self.amount_column_candidates = ['收费金额', '收费金额（元）', '金额']
        self.optional_columns = ['移动账号']
        self.auto_convert_utc_to_beijing = auto_convert_utc_to_beijing  # 是否自动将 UTC 转换为北京时间（默认关闭）

    def process_payment_import(self, file_buffer, last_import_time: Optional[datetime] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """处理缴费Excel文件"""
        try:
            df = self.read_excel_file(file_buffer)
            errors = []

            # 列名映射（兼容不同的导出格式）
            column_mapping = {
                '学号': '用户账号',
                '缴费时间': '收费时间',
                '缴费金额': '收费金额',
                '收费金额（元）': '收费金额',  # 带单位的格式
                '记录ID': None,  # 忽略这些列
                '处理状态': None,
                '创建时间': None,
                '处理时间': None,
            }

            # 应用列名映射（只映射存在的列）
            rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns and v is not None}
            df.rename(columns=rename_dict, inplace=True)

            # 验证必需列
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                # 提供更详细的错误信息
                raise ValueError(f"缺少必需列: {', '.join(missing_columns)}，当前列: {list(df.columns)}")

            # 智能识别收费金额列
            amount_column = None
            for candidate in self.amount_column_candidates:
                if candidate in df.columns:
                    amount_column = candidate
                    break

            if not amount_column:
                raise ValueError(f"缺少收费金额列，支持的列名: {', '.join(self.amount_column_candidates)}")

            processed_payments = []

            for index, row in df.iterrows():
                try:
                    缴费时间 = self._parse_datetime(row['收费时间'])
                    if not 缴费时间:
                        errors.append(f"第{index+2}行: 收费时间格式错误，原始值: {row['收费时间']}")
                        continue

                    # 增量过滤：只处理新于上次导入时间的记录
                    if last_import_time and 缴费时间 <= last_import_time:
                        continue

                    payment_data = {
                        '学号': str(row['用户账号']).strip(),
                        '缴费时间': 缴费时间,
                        '缴费金额': float(row[amount_column])
                    }

                    # 数据验证
                    if not payment_data['学号']:
                        errors.append(f"第{index+2}行: 用户账号不能为空")
                        continue

                    if payment_data['缴费金额'] <= 0:
                        errors.append(f"第{index+2}行: 缴费金额必须大于0")
                        continue

                    processed_payments.append(payment_data)

                except Exception as e:
                    errors.append(f"第{index+2}行处理错误: {e}")

            return processed_payments, errors

        except Exception as e:
            return [], [f"文件处理错误: {e}"]

    def _parse_datetime(self, datetime_value) -> Optional[datetime]:
        """解析日期时间，支持多种格式包括带毫秒的格式

        注意：如果 auto_convert_utc_to_beijing=True，会自动将 UTC 时间转换为北京时间（UTC+8）
        """
        from datetime import timedelta

        if pd.isna(datetime_value):
            return None

        parsed_dt = None

        # 如果是 pandas Timestamp 对象，直接转换为 datetime
        if isinstance(datetime_value, pd.Timestamp):
            parsed_dt = datetime_value.to_pydatetime().replace(tzinfo=None)

        elif isinstance(datetime_value, datetime):
            parsed_dt = datetime_value.replace(tzinfo=None)

        else:
            # 转换为字符串并清理
            datetime_str = str(datetime_value).strip()

            # 尝试多种日期时间格式
            formats = [
                '%Y-%m-%d %H:%M:%S.%f',  # 2025-10-01 14:02:37.0
                '%Y-%m-%d %H:%M:%S',     # 2025-10-01 14:02:37
                '%Y/%m/%d %H:%M:%S.%f',  # 2025/10/01 14:02:37.0
                '%Y/%m/%d %H:%M:%S',     # 2025/10/01 14:02:37
                '%Y-%m-%d',              # 2025-10-01
                '%Y/%m/%d',              # 2025/10/01
            ]

            for fmt in formats:
                try:
                    parsed_dt = datetime.strptime(datetime_str, fmt)
                    break
                except:
                    continue

        if parsed_dt is None:
            return None

        # 如果启用了 UTC 到北京时间的自动转换
        if self.auto_convert_utc_to_beijing:
            # 将 UTC 时间转换为北京时间（+8 小时）
            parsed_dt = parsed_dt + timedelta(hours=8)

        return parsed_dt


class ExportExcelProcessor(ExcelProcessor):
    """导出Excel处理器"""

    def create_binding_export_file(self, binding_data, filename: str = None) -> str:
        """创建绑定导出文件

        Args:
            binding_data: 可以是元组列表 [(学号, 移动账号)] 或字典列表 [{'学号': ..., '移动账号': ..., ...}]
        """
        if filename is None:
            filename = f'绑定导出_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        # 构造导出数据
        export_data = []
        for item in binding_data:
            if isinstance(item, dict):
                # 字典格式（新版，包含套餐信息）
                export_data.append({
                    '账号': item.get('学号', ''),
                    '移动账号': item.get('移动账号', ''),
                    '移动密码': '',  # 留空
                    '联通账号': '',  # 留空
                    '联通密码': '',  # 留空
                    '电信账号': '',  # 留空
                    '电信密码': '',  # 留空
                    '套餐类型': item.get('套餐类型', ''),
                    '到期日期': item.get('到期日期', ''),
                    '缴费金额': item.get('缴费金额', '')
                })
            else:
                # 元组格式（旧版兼容）
                学号, 移动账号 = item
                export_data.append({
                    '账号': 学号,
                    '移动账号': 移动账号,
                    '移动密码': '',
                    '联通账号': '',
                    '联通密码': '',
                    '电信账号': '',
                    '电信密码': ''
                })

        return self.save_to_excel(export_data, filename, '批量修改')

    def create_template_file(self, template_type: str) -> str:
        """创建模板文件"""
        templates = {
            'account_import': {
                'filename': '账号导入模板.xlsx',
                'data': [{'移动账户': '示例账号', '账号类型': '202409', '使用状态': '未使用'}],
                'sheet_name': '账号导入'
            },
            'payment_import': {
                'filename': '缴费导入模板.xlsx',
                'data': [{'用户账号': '示例学号', '收费时间': '2024-01-01 10:00:00', '收费金额': 30.0}],
                'sheet_name': '缴费记录'
            },
            'binding_import': {
                'filename': '绑定详情模板.xlsx',
                'data': [{'用户账号': '示例学号', '移动账号': '示例移动账号', '到期日期': '2024-12-31'}],
                'sheet_name': '绑定详情'
            }
        }

        if template_type not in templates:
            raise ValueError(f"不支持的模板类型: {template_type}")

        template = templates[template_type]
        return self.save_to_excel(template['data'], template['filename'], template['sheet_name'])


# 创建处理器实例
account_processor = AccountExcelProcessor()
binding_processor = BindingExcelProcessor()
payment_processor = PaymentExcelProcessor()
export_processor = ExportExcelProcessor()


if __name__ == "__main__":
    # 测试Excel处理器
    print("Excel处理器测试...")

    # 创建模板文件
    try:
        template_path = export_processor.create_template_file('account_import')
        print(f"账号导入模板已创建: {template_path}")
    except Exception as e:
        print(f"模板创建失败: {e}")

    print("Excel处理器初始化完成")
