#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日期工具模块
Date Utilities
"""

from datetime import datetime, date, timedelta
from typing import Optional, Tuple, Any
from dateutil.relativedelta import relativedelta
import re


class DateCalculator:
    """日期计算工具类"""

    @staticmethod
    def parse_datetime_value(value: Any) -> Optional[datetime]:
        """
        将各种形式的时间值统一解析为 datetime

        Args:
            value: 可能是 datetime/date/字符串

        Returns:
            datetime 对象或 None（解析失败）
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())

        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return None

            # 优先尝试 ISO 格式
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                pass

            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M",
                "%Y-%m-%d",
                "%Y/%m/%d"
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(candidate, fmt)
                except ValueError:
                    continue

        return None

    @staticmethod
    def parse_account_type_to_dates(账号类型: str) -> Tuple[Optional[date], Optional[date]]:
        """
        根据账号类型计算生命周期日期

        Args:
            账号类型: 如 "202409", "0元账号"

        Returns:
            (生命周期开始日期, 生命周期结束日期)
        """
        if 账号类型 == "0元账号":
            # 0元账号使用系统配置中的日期
            return None, None  # 由业务逻辑层处理

        # 匹配年月格式 (如 "202409")
        match = re.match(r'(\d{4})(\d{2})', 账号类型.strip())
        if match:
            year = int(match.group(1))
            month = int(match.group(2))

            if 1 <= month <= 12:
                生命周期开始日期 = date(year, month, 1)

                # 生命周期结束日期为下一年同月1日
                if month == 12:
                    生命周期结束日期 = date(year + 1, 1, 1)
                else:
                    生命周期结束日期 = date(year + 1, month, 1)

                return 生命周期开始日期, 生命周期结束日期

        # 如果无法解析，返回None
        return None, None

    @staticmethod
    def calculate_subscription_expiry(缴费时间: datetime, 缴费金额: float) -> Tuple[str, Optional[date]]:
        """
        根据缴费金额计算套餐类型和到期日期

        Args:
            缴费时间: 缴费时间
            缴费金额: 缴费金额

        Returns:
            (套餐类型, 到期日期)
            - 30元 → ("包月", 缴费时间 + 1个月)
            - 300元 → ("包年", 缴费时间 + 1年)
            - 其他 → ("未知套餐", None)
        """
        parsed_datetime = DateCalculator.parse_datetime_value(缴费时间)
        if parsed_datetime is None:
            raise ValueError(f"无法解析缴费时间: {缴费时间}")

        缴费日期 = parsed_datetime.date()

        # 根据金额判断套餐类型
        if 缴费金额 == 30:
            套餐类型 = "包月"
            到期日期 = 缴费日期 + relativedelta(months=1)
        elif 缴费金额 == 300:
            套餐类型 = "包年"
            到期日期 = 缴费日期 + relativedelta(years=1)
        else:
            套餐类型 = f"{int(缴费金额)}元套餐"
            到期日期 = None

        return 套餐类型, 到期日期

    @staticmethod
    def is_account_expired(生命周期结束日期: Optional[date]) -> bool:
        """判断账号是否已过期"""
        if 生命周期结束日期 is None:
            return False
        return 生命周期结束日期 < date.today()

    @staticmethod
    def is_binding_expired(绑定的套餐到期日: Optional[date]) -> bool:
        """判断绑定是否已过期"""
        if 绑定的套餐到期日 is None:
            return False
        return 绑定的套餐到期日 < date.today()

    @staticmethod
    def days_until_expiry(expiry_date: Optional[date]) -> Optional[int]:
        """计算距离过期还有多少天"""
        if expiry_date is None:
            return None

        delta = expiry_date - date.today()
        return delta.days

    @staticmethod
    def format_date_for_display(date_obj: Optional[date]) -> str:
        """格式化日期用于显示"""
        if date_obj is None:
            return "无期限"
        return date_obj.strftime("%Y-%m-%d")

    @staticmethod
    def parse_date_from_string(date_str: str) -> Optional[date]:
        """从字符串解析日期"""
        if not date_str or date_str.strip() == "":
            return None

        # 尝试各种日期格式
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
            "%m/%d/%Y",
            "%d/%m/%Y"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None


class BusinessDateHelper:
    """业务日期辅助类"""

    @staticmethod
    def get_zero_cost_account_expiry(system_setting_value: Optional[str]) -> Optional[date]:
        """获取0元账号到期日"""
        if not system_setting_value:
            return None

        return DateCalculator.parse_date_from_string(system_setting_value)

    @staticmethod
    def should_auto_release_binding(绑定的套餐到期日: Optional[date],
                                   生命周期结束日期: Optional[date]) -> bool:
        """判断是否应该自动释放绑定"""
        # 套餐已过期但账号生命周期未结束
        if DateCalculator.is_binding_expired(绑定的套餐到期日):
            if not DateCalculator.is_account_expired(生命周期结束日期):
                return True
        return False

    @staticmethod
    def should_auto_expire_account(生命周期结束日期: Optional[date]) -> bool:
        """判断是否应该自动过期账号"""
        return DateCalculator.is_account_expired(生命周期结束日期)

    @staticmethod
    def get_maintenance_summary(released_count: int, expired_count: int) -> str:
        """获取维护操作摘要"""
        summary_parts = []

        if released_count > 0:
            summary_parts.append(f"释放了{released_count}个过期绑定")

        if expired_count > 0:
            summary_parts.append(f"标记了{expired_count}个过期账号")

        if not summary_parts:
            return "无需要维护的账号"

        return "，".join(summary_parts)


# 创建工具实例
date_calculator = DateCalculator()
business_date_helper = BusinessDateHelper()


if __name__ == "__main__":
    # 测试日期工具
    print("日期工具测试...")

    # 测试账号类型解析
    test_types = ["202409", "202410", "0元账号", "invalid"]

    for account_type in test_types:
        start, end = date_calculator.parse_account_type_to_dates(account_type)
        print(f"账号类型 '{account_type}': 开始={start}, 结束={end}")

    print("日期工具初始化完成")
