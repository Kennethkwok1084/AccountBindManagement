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

            # 清理列名（去除空白字符）
            if hasattr(df, 'columns'):
                df.columns = df.columns.str.strip()
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
                        '到期日期': self._parse_date(row['到期日期'])
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

    def __init__(self):
        self.required_columns = ['用户账号', '收费时间', '收费金额']
        self.optional_columns = ['移动账号']

    def process_payment_import(self, file_buffer, last_import_time: Optional[datetime] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """处理缴费Excel文件"""
        try:
            df = self.read_excel_file(file_buffer)
            errors = []

            # 验证必需列
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"缺少必需列: {', '.join(missing_columns)}")

            processed_payments = []

            for index, row in df.iterrows():
                try:
                    缴费时间 = self._parse_datetime(row['收费时间'])
                    if not 缴费时间:
                        errors.append(f"第{index+2}行: 收费时间格式错误")
                        continue

                    # 增量过滤：只处理新于上次导入时间的记录
                    if last_import_time and 缴费时间 <= last_import_time:
                        continue

                    payment_data = {
                        '学号': str(row['用户账号']).strip(),
                        '缴费时间': 缴费时间,
                        '缴费金额': float(row['收费金额'])
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
        """解析日期时间"""
        if pd.isna(datetime_value):
            return None

        if isinstance(datetime_value, datetime):
            return datetime_value

        # 尝试解析字符串日期时间
        try:
            return datetime.strptime(str(datetime_value), '%Y-%m-%d %H:%M:%S')
        except:
            try:
                return datetime.strptime(str(datetime_value), '%Y/%m/%d %H:%M:%S')
            except:
                try:
                    # 如果只有日期，添加默认时间
                    return datetime.strptime(str(datetime_value), '%Y-%m-%d')
                except:
                    return None


class ExportExcelProcessor(ExcelProcessor):
    """导出Excel处理器"""

    def create_binding_export_file(self, binding_data: List[Tuple[str, str]], filename: str = None) -> str:
        """创建绑定导出文件"""
        if filename is None:
            filename = f'绑定导出_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        # 构造导出数据
        export_data = []
        for 学号, 移动账号 in binding_data:
            export_data.append({
                '账号': 学号,
                '移动账号': 移动账号,
                '移动密码': '',  # 留空
                '联通账号': '',  # 留空
                '联通密码': '',  # 留空
                '电信账号': '',  # 留空
                '电信密码': ''   # 留空
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