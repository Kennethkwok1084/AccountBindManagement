#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复绑定处理页面 - 定位并修复移动账号重复绑定
Duplicate Binding Resolution Page
"""

import streamlit as st
import pandas as pd
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import MaintenanceOperations, ISPAccountOperations
from ui_components import (
    apply_global_style, render_page_header, render_section_divider,
    render_info_card, render_stats_row, render_dataframe_with_style,
    show_success_message, show_error_message
)

st.set_page_config(
    page_title="重复绑定处理 - 校园网账号管理系统",
    page_icon="♻️",
    layout="wide"
)

# 应用全局样式
apply_global_style()

# 页面标题
render_page_header(
    "重复绑定处理",
    "定位并修复移动账号同时绑定多个学号的异常情况",
    "♻️"
)

# 获取数据
duplicate_groups = MaintenanceOperations.get_duplicate_mobile_bindings()
available_accounts = ISPAccountOperations.get_available_accounts()
available_count = len(available_accounts)

# 统计信息
render_section_divider("📊 当前状态")

stats_data = [
    {'label': '重复账号组数', 'value': len(duplicate_groups)},
    {'label': '可用账号库存', 'value': available_count},
]
render_stats_row(stats_data, icons=['♻️', '🔋'])

if available_count == 0:
    st.warning("当前没有可用的未使用账号，无法执行换绑操作。")

# 功能说明
render_section_divider("ℹ️ 操作说明")

col1, col2 = st.columns(2)
with col1:
    render_info_card(
        "处理步骤",
        """
        1. 找到下方重复绑定的移动账号<br>
        2. 确认需要保留的学号<br>
        3. 对其他学号执行“换绑”操作<br>
        4. 系统会自动分配新的未使用账号
        """,
        "🛠️",
        "info"
    )

with col2:
    render_info_card(
        "换绑规则",
        """
        • 优先保留当前在账号池中绑定的学号<br>
        • 换绑会占用一张未使用账号<br>
        • 若库存不足，需先补充账号<br>
        • 换绑成功后列表会自动刷新
        """,
        "📐",
        "warning"
    )

# 重复绑定列表
render_section_divider("🔍 重复绑定详情")

if not duplicate_groups:
    st.success("当前没有重复绑定的移动账号，一切正常。")
else:
    for group in duplicate_groups:
        mobile_account = group['移动账号']
        students = group['学生列表']
        current_binding = group.get('账号绑定学号')

        with st.expander(f"账号 {mobile_account}（当前绑定学号：{current_binding or '无'}）", expanded=True):
            df = pd.DataFrame([
                {
                    '移动账号': mobile_account,
                    '用户账号': student['用户账号'],
                    '用户姓名': student['用户姓名'] or '',
                    '用户类别': student['用户类别'] or '',
                    '到期日期': student['到期日期'] or '',
                    '更新时间': student['更新时间'],
                    '是否账号当前绑定': "是" if student['是否账号当前绑定'] else "否"
                }
                for student in students
            ])

            render_dataframe_with_style(df)

            st.markdown("#### 🎯 换绑操作")

            for student in students:
                user_account = student['用户账号']
                is_keeper = student['是否账号当前绑定']

                button_disabled = available_count == 0 or (is_keeper and len(students) == 1)
                button_label = f"为学号 {user_account} 分配新账号"

                if is_keeper and len(students) > 1:
                    helper_text = "（当前账号池绑定的学号，通常无需换绑）"
                elif is_keeper:
                    helper_text = "（当前账号池绑定的学号）"
                else:
                    helper_text = ""

                col_btn, col_msg = st.columns([1, 3])
                with col_btn:
                    if st.button(button_label, key=f"rebind_{mobile_account}_{user_account}", disabled=button_disabled):
                        success, message, new_account = MaintenanceOperations.manual_rebind_duplicate_student(
                            mobile_account, user_account
                        )
                        if success:
                            show_success_message(message)
                            st.experimental_rerun()
                        else:
                            show_error_message(message)

                with col_msg:
                    if helper_text:
                        st.write(helper_text)

            if available_count == 0:
                st.info("提示：补充账号库存后，可重新执行换绑操作。")

