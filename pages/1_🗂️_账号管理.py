#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号管理页面 - ISP账号池管理
Account Management Page - ISP Account Pool Management
"""

import os

# 使用轮询监视器避免 inotify 限制带来的崩溃
os.environ.setdefault("STREAMLIT_WATCHDOG_TYPE", "polling")

import streamlit as st
import pandas as pd
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.business_logic import account_manager
from database.operations import ISPAccountOperations, MaintenanceOperations
from database.models import get_db_stats
from utils.excel_handler import export_processor
from ui_components import (
    apply_global_style, render_page_header, render_stats_row,
    render_search_filters, render_dataframe_with_style,
    show_success_message, show_error_message, render_section_divider,
    render_empty_state, render_info_card
)

st.set_page_config(
    page_title="账号管理 - 校园网账号管理系统",
    page_icon="🗂️",
    layout="wide"
)

# 应用全局样式
apply_global_style()

# 页面标题
render_page_header(
    "ISP账号池管理",
    "管理移动/联通/电信账号资源池（不包含绑定关系）",
    "🗂️"
)

# 导入新账号模块
render_section_divider("📤 导入上网账号")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("#### 📁 上传账号文件")
    uploaded_file = st.file_uploader(
        "选择账号Excel文件",
        type=['xlsx', 'xls'],
        help="Excel文件应包含：移动账户、账号类型、使用状态（可选）",
        key="account_upload"
    )

    if uploaded_file is not None:
        if st.button("📤 导入账号", type="primary", width='stretch'):
            with st.spinner("正在处理账号数据..."):
                result = account_manager.import_accounts_from_excel(uploaded_file)

                if result['success']:
                    show_success_message(result['message'])

                    if result['errors']:
                        with st.expander("⚠️ 查看导入错误详情"):
                            for error in result['errors']:
                                show_error_message(error)
                    st.rerun()
                else:
                    show_error_message(result['message'])
                    if result['errors']:
                        for error in result['errors'][:5]:  # 只显示前5个错误
                            show_error_message(error)

with col2:
    render_info_card(
        "导入模板",
        "下载标准模板文件，按照模板格式填写账号信息后上传",
        "📋",
        "info"
    )

    try:
        template_path = export_processor.create_template_file('account_import')
        if os.path.exists(template_path):
            with open(template_path, 'rb') as file:
                st.download_button(
                    label="📋 下载导入模板",
                    data=file.read(),
                    file_name="账号导入模板.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width='stretch'
                )
    except Exception as e:
        show_error_message(f"模板生成失败: {e}")

# 搜索与筛选
render_section_divider("🔍 搜索与筛选")

col1, col2, col3, col4 = st.columns(4)

with col1:
    search_account = st.text_input("搜索账号", placeholder="输入移动账号", key="search_acc")

with col2:
    search_student = st.text_input("搜索学号", placeholder="输入绑定的学号", key="search_stu")

with col3:
    filter_status = st.selectbox(
        "账号状态",
        ["全部", "未使用", "已使用", "已过期", "已过期但被绑定", "已停机"],
        key="filter_status"
    )

with col4:
    filter_type = st.selectbox(
        "账号类型",
        ["全部", "202409", "202410", "0元账号", "其他"],
        key="filter_type"
    )

# 执行搜索
try:
    # 构建搜索条件
    search_conditions = {}

    if filter_status != "全部":
        search_conditions['状态'] = filter_status

    if filter_type != "全部":
        if filter_type != "其他":
            search_conditions['账号类型'] = filter_type

    if search_student:
        search_conditions['绑定的学号'] = search_student

    # 获取账号列表
    if search_account:
        # 精确搜索单个账号
        account = ISPAccountOperations.get_account(search_account)
        accounts = [account] if account else []
    else:
        # 按条件搜索
        accounts = ISPAccountOperations.search_accounts(**search_conditions)

    # 显示结果
    if accounts:
        render_section_divider(f"📋 账号列表 ({len(accounts)} 条记录)")

        # 转换为DataFrame显示
        df_data = []
        for account in accounts:
            df_data.append({
                '账号': account['账号'],
                '状态': account['状态'],
                '账号类型': account['账号类型'],
                '绑定学号': account['绑定的学号'] or '',
                '用户姓名': account.get('用户姓名') or '',
                '生命周期结束日期': account['生命周期结束日期'] or '',
                '套餐到期日': account['绑定的套餐到期日'] or '',
                '更新时间': account['更新时间']
            })

        df = pd.DataFrame(df_data)

        # 使用样式渲染数据表格
        render_dataframe_with_style(df, status_column='状态')

        # 批量操作
        render_section_divider("⚙️ 批量操作")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 释放过期绑定", width='stretch'):
                with st.spinner("正在释放过期绑定..."):
                    released_count = MaintenanceOperations.auto_release_expired_bindings()
                    show_success_message(f"释放了 {released_count} 个过期绑定")
                    st.rerun()

        with col2:
            if st.button("❌ 标记过期账号", width='stretch'):
                with st.spinner("正在标记过期账号..."):
                    expired_count = MaintenanceOperations.auto_expire_lifecycle_ended()
                    show_success_message(f"标记了 {expired_count} 个过期账号")
                    st.rerun()

        with col3:
            # 导出当前搜索结果
            if st.button("📤 导出搜索结果", width='stretch'):
                try:
                    export_path = export_processor.save_to_excel(
                        df_data,
                        f"账号搜索结果_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        "账号列表"
                    )

                    if os.path.exists(export_path):
                        with open(export_path, 'rb') as file:
                            st.download_button(
                                label="📥 下载导出文件",
                                data=file.read(),
                                file_name=os.path.basename(export_path),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="download_search_result"
                            )
                except Exception as e:
                    show_error_message(f"导出失败: {e}")

    else:
        render_empty_state(
            "没有找到匹配的账号记录",
            suggestions=[
                "检查搜索条件是否正确",
                "尝试清除部分筛选条件",
                "如果是新系统，请先导入账号数据"
            ]
        )

except Exception as e:
    show_error_message(f"搜索过程中发生错误: {e}")

# 账号统计信息
try:
    stats = get_db_stats()

    render_section_divider("📈 账号统计")

    stats_data = [
        {'label': '总账号数', 'value': stats.get('总账号数', 0)},
        {'label': '可用账号', 'value': stats.get('账号_未使用', 0)},
        {'label': '已使用账号', 'value': stats.get('账号_已使用', 0)},
        {'label': '已过期账号', 'value': stats.get('账号_已过期', 0)}
    ]

    render_stats_row(stats_data, icons=['📊', '🔋', '📱', '❌'])

except Exception as e:
    show_error_message(f"获取统计信息失败: {e}")
