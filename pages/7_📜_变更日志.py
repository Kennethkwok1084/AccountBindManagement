#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
变更日志页面 - 审计每一次账号与操作的变化
Change Log Page - Audit every account and operation change
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Any, Dict

import pandas as pd
import streamlit as st

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import (
    AccountChangeLogOperations,
    OperationLogOperations
)
from ui_components import (
    apply_global_style,
    render_page_header,
    render_section_divider,
    render_empty_state,
    show_error_message
)

st.set_page_config(
    page_title="变更日志 - 校园网账号管理系统",
    page_icon="📜",
    layout="wide"
)


def _format_log_dataframe(records, columns_map: Dict[str, str]) -> pd.DataFrame:
    """将日志记录转换为DataFrame并提取常用字段"""
    if not records:
        return pd.DataFrame(columns=columns_map.values())

    normalized = []
    for item in records:
        normalized_record: Dict[str, Any] = {}
        for key, label in columns_map.items():
            value = item.get(key)
            if key == '操作详情' and isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            normalized_record[label] = value
        normalized.append(normalized_record)

    return pd.DataFrame(normalized)


def render():
    """渲染变更日志主界面"""
    apply_global_style()

    render_page_header(
        "账号变更审计日志",
        "追踪账号生命周期、绑定操作与导入批次的完整历史，确保每次变化可回溯",
        "📜"
    )

    tab_account, tab_student, tab_range, tab_operations = st.tabs([
        "🔍 按账号查询",
        "🎓 按学号查询",
        "🗓️ 按时间范围",
        "📦 操作批次"
    ])

    with tab_account:
        render_section_divider("🔍 查询单个账号变更历史")
        account_id = st.text_input("输入账号（手机号）", key="audit_account_input")
        if account_id:
            history = AccountChangeLogOperations.get_account_history(account_id.strip())
            df = _format_log_dataframe(history, {
                '变更时间': '变更时间',
                '变更类型': '变更类型',
                '变更字段': '变更字段',
                '旧值': '旧值',
                '新值': '新值',
                '关联学号': '关联学号',
                '操作来源': '操作来源',
                '操作批次ID': '批次ID',
                '备注': '备注'
            })
            if df.empty:
                render_empty_state("未找到变更记录", ["检查账号是否存在或输入是否正确"])
            else:
                st.dataframe(df, use_container_width=True)
        else:
            render_empty_state("请输入账号以查询历史", ["支持手机号或宽带账号"])

    with tab_student:
        render_section_divider("🎓 按学号查看相关账号变更")
        student_id = st.text_input("输入学号", key="audit_student_input")
        if student_id:
            history = AccountChangeLogOperations.get_student_related_changes(student_id.strip())
            df = _format_log_dataframe(history, {
                '变更时间': '变更时间',
                '账号': '账号',
                '变更类型': '变更类型',
                '变更字段': '变更字段',
                '旧值': '旧值',
                '新值': '新值',
                '操作来源': '操作来源',
                '操作批次ID': '批次ID',
                '备注': '备注'
            })
            if df.empty:
                render_empty_state("未找到相关账号变更", ["确认该学号是否存在绑定历史"])
            else:
                st.dataframe(df, use_container_width=True)
        else:
            render_empty_state("请输入学号以查询关联账号变更")

    with tab_range:
        render_section_divider("🗓️ 按时间范围筛选变更记录")
        today = datetime.now().date()
        default_start = today - timedelta(days=7)
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=default_start, key="audit_start_date")
        with col2:
            end_date = st.date_input("结束日期", value=today, key="audit_end_date")

        if start_date > end_date:
            show_error_message("开始日期不能晚于结束日期")
        else:
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            history = AccountChangeLogOperations.get_changes_by_time_range(start_dt, end_dt)
            df = _format_log_dataframe(history, {
                '变更时间': '变更时间',
                '账号': '账号',
                '变更类型': '变更类型',
                '变更字段': '变更字段',
                '旧值': '旧值',
                '新值': '新值',
                '关联学号': '关联学号',
                '操作来源': '操作来源',
                '操作批次ID': '批次ID'
            })
            if df.empty:
                render_empty_state("该时间范围内没有变更记录")
            else:
                st.dataframe(df, use_container_width=True)

    with tab_operations:
        render_section_divider("📦 操作批次执行记录")
        limit = st.slider("选择展示条数", min_value=20, max_value=500, value=100, step=20)
        operation_logs = OperationLogOperations.get_recent_logs(limit=limit)
        df_ops = _format_log_dataframe(operation_logs, {
            'id': '批次ID',
            '操作时间': '操作时间',
            '操作类型': '操作类型',
            '操作人': '操作人',
            '操作详情': '操作详情',
            '影响记录数': '影响记录数',
            '执行状态': '执行状态',
            '备注': '备注'
        })

        if df_ops.empty:
            render_empty_state("暂无操作批次记录", ["执行导入、绑定或维护任务后可查看详细日志"])
        else:
            st.dataframe(df_ops, use_container_width=True)

        render_section_divider("🔗 查看批次关联的账号变更")
        selected_id = st.text_input("输入操作批次ID查看关联账号变更", key="audit_operation_id")
        if selected_id:
            try:
                batch_id = int(selected_id.strip())
                filtered_history = AccountChangeLogOperations.get_changes_by_operation(batch_id)

                df_related = _format_log_dataframe(filtered_history, {
                    '变更时间': '变更时间',
                    '账号': '账号',
                    '变更类型': '变更类型',
                    '变更字段': '变更字段',
                    '旧值': '旧值',
                    '新值': '新值',
                    '关联学号': '关联学号',
                    '操作来源': '操作来源',
                    '备注': '备注'
                })

                if df_related.empty:
                    render_empty_state("该批次未关联账号变更记录")
                else:
                    st.dataframe(df_related, use_container_width=True)
            except ValueError:
                show_error_message("请输入有效的数字ID")


if __name__ == "__main__":
    render()
