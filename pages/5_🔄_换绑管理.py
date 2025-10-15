#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
换绑管理页面 - 管理已过期但被绑定的账号
Rebinding Management Page
"""

import os

# 使用轮询监视器避免 inotify 限制带来的崩溃
os.environ.setdefault("STREAMLIT_WATCHDOG_TYPE", "polling")

import streamlit as st
import pandas as pd
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import ISPAccountOperations
from database.models import db_manager
from utils.excel_handler import export_processor
from ui_components import (
    apply_global_style, render_page_header, render_stats_row,
    render_dataframe_with_style, show_success_message, show_error_message,
    render_section_divider, render_empty_state, render_info_card
)

st.set_page_config(
    page_title="换绑管理 - 校园网账号管理系统",
    page_icon="🔄",
    layout="wide"
)

# 应用全局样式
apply_global_style()

# 页面标题
render_page_header(
    "换绑管理",
    "查看和导出已过期但仍被绑定的账号列表",
    "🔄"
)

# 说明卡片
render_section_divider("📋 功能说明")

col1, col2 = st.columns(2)

with col1:
    render_info_card(
        "什么是「已过期但被绑定」？",
        """
        <strong>账号状态说明：</strong><br>
        • 账号生命周期已结束（已过期）<br>
        • 但仍然绑定着学号（被绑定）<br>
        • 需要手动换绑到新的可用账号
        """,
        "❓",
        "info"
    )

with col2:
    render_info_card(
        "操作流程",
        """
        <strong>换绑操作步骤：</strong><br>
        1️⃣ 查看下方列表，了解需要换绑的账号<br>
        2️⃣ 点击导出按钮，下载Excel文件<br>
        3️⃣ 在后台系统中导入Excel进行批量换绑
        """,
        "📝",
        "warning"
    )

# 查询已过期但被绑定的账号
render_section_divider("🔍 已过期但被绑定账号列表")

try:
    # 查询所有「已过期但被绑定」的账号
    expired_but_bound_accounts = ISPAccountOperations.search_accounts(状态='已过期但被绑定')

    if expired_but_bound_accounts:
        # 准备表格数据
        df_data = []
        for account in expired_but_bound_accounts:
            df_data.append({
                '账号': account['账号'],
                '账号类型': account['账号类型'],
                '状态': account['状态'],
                '绑定的学号': account['绑定的学号'] or '',
                '套餐到期日': account['绑定的套餐到期日'] or '',
                '生命周期开始日期': account['生命周期开始日期'],
                '生命周期结束日期': account['生命周期结束日期']
            })

        df = pd.DataFrame(df_data)

        # 显示统计信息
        stats_data = [
            {'label': '需要换绑的账号数', 'value': len(df_data)},
            {'label': '涉及用户数', 'value': df[df['绑定的学号'] != '']['绑定的学号'].nunique()},
        ]
        render_stats_row(stats_data, icons=['📊', '👥'])

        st.markdown("---")

        # 显示数据表格
        st.markdown(f"#### 📋 账号详情 ({len(df_data)} 条记录)")
        render_dataframe_with_style(df)

        # 导出功能
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])

        with col2:
            if st.button("📥 导出换绑列表Excel", type="primary", width='stretch'):
                try:
                    export_path = export_processor.save_to_excel(
                        df_data,
                        f"换绑列表_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        "换绑列表"
                    )

                    if os.path.exists(export_path):
                        with open(export_path, 'rb') as file:
                            st.download_button(
                                label="💾 下载导出文件",
                                data=file.read(),
                                file_name=os.path.basename(export_path),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                width='stretch',
                                key="download_rebind_list"
                            )
                            show_success_message("导出成功！点击上方按钮下载文件")
                except Exception as e:
                    show_error_message(f"导出失败: {e}")

    else:
        render_empty_state(
            "没有需要换绑的账号",
            suggestions=[
                "所有已过期的账号都已释放绑定",
                "可以在「账号管理」页面查看其他状态的账号",
                "如需刷新账号状态，请在「账号管理」中执行批量操作"
            ]
        )

except Exception as e:
    show_error_message(f"查询过程中发生错误: {e}")

# 操作提示
st.markdown("---")
st.info("""
💡 **温馨提示**：
- 导出的Excel文件包含所有需要换绑的账号信息
- 包括：账号、绑定学号、套餐到期日、生命周期日期等
- 可直接用于后台系统的批量换绑操作
- 如需手动处理，可在「账号管理」页面中逐个操作
""")
