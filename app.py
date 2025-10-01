#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校园网上网账号管理系统 - 首页仪表盘
Campus Network Account Management System - Dashboard
"""

import streamlit as st
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.business_logic import system_maintenance, payment_processor_logic
from database.models import get_db_stats
from ui_components import (
    apply_global_style, render_page_header, render_stats_row,
    render_progress_card, render_action_card, render_info_card,
    show_success_message, show_error_message, render_section_divider,
    COLORS
)

st.set_page_config(
    page_title="校园网账号管理系统",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 应用全局样式
apply_global_style()

# 启动定时任务调度器（仅在主线程启动一次）
if 'scheduler_started' not in st.session_state:
    try:
        from utils.scheduler import start_scheduler, get_scheduler
        start_scheduler()
        scheduler = get_scheduler()
        st.session_state.scheduler_started = True
        st.session_state.scheduler_next_run = scheduler.get_next_run_time()
    except Exception as e:
        st.session_state.scheduler_started = False
        st.session_state.scheduler_error = str(e)

# 页面标题
render_page_header(
    "校园网上网账号管理系统",
    "Campus Network Account Management System v2.0",
    "🌐"
)

# 获取系统状态
try:
    status = system_maintenance.get_system_status()

    if 'error' in status:
        show_error_message(f"获取系统状态失败: {status['error']}")
    else:
        stats = status['stats']
        settings = status['settings']

        # 核心数据看板
        render_section_divider("💎 核心指标")

        available_count = stats.get('账号_未使用', 0)
        pending_count = stats.get('待处理缴费', 0)
        used_count = stats.get('账号_已使用', 0)
        expired_count = stats.get('账号_已过期', 0)
        total_accounts = stats.get('总账号数', 0)

        # 使用新的统计行组件
        stats_data = [
            {
                'label': '可用账号',
                'value': available_count,
                'delta': '库存预警' if available_count < 10 else None,
                'delta_color': 'inverse' if available_count < 10 else 'normal'
            },
            {
                'label': '待处理缴费',
                'value': pending_count,
                'delta': '需要处理' if pending_count > 0 else None
            },
            {
                'label': '已使用账号',
                'value': used_count
            },
            {
                'label': '已过期账号',
                'value': expired_count
            }
        ]

        render_stats_row(stats_data, icons=['🔋', '⏳', '📱', '❌'])

        # 账号池健康度
        render_section_divider("🏥 账号池健康度")

        if total_accounts > 0:
            col1, col2, col3 = st.columns([1, 1, 1])

            with col1:
                render_progress_card(
                    "可用账号占比",
                    available_count,
                    total_accounts,
                    "🔋"
                )

            with col2:
                render_progress_card(
                    "已使用账号占比",
                    used_count,
                    total_accounts,
                    "📱"
                )

            with col3:
                render_progress_card(
                    "过期账号占比",
                    expired_count,
                    total_accounts,
                    "❌"
                )

            # 详细统计
            st.markdown("---")
            col1, col2 = st.columns([2, 1])

            with col1:
                # 创建图表数据
                import pandas as pd
                chart_data = pd.DataFrame({
                    '状态': ['可用', '已使用', '已过期'],
                    '数量': [available_count, used_count, expired_count]
                })
                st.bar_chart(chart_data, x='状态', y='数量', color='#1E88E5')

            with col2:
                render_info_card(
                    "账号池统计",
                    f"""
                    总账号数: **{total_accounts}**<br>
                    可用率: **{available_count/total_accounts*100:.1f}%**<br>
                    使用率: **{used_count/total_accounts*100:.1f}%**<br>
                    过期率: **{expired_count/total_accounts*100:.1f}%**
                    """,
                    "📊",
                    "info"
                )
        else:
            render_info_card(
                "暂无数据",
                "暂无账号数据，请先导入账号池",
                "📭",
                "warning"
            )

        # 快捷操作区
        render_section_divider("⚡ 快捷操作")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📤 缴费处理")
            st.markdown("---")

            # 上传缴费文件
            uploaded_file = st.file_uploader(
                "选择收费Excel文件",
                type=['xlsx', 'xls'],
                key="payment_upload_home"
            )

            if uploaded_file is not None:
                if st.button("📤 导入缴费记录", type="primary", key="import_payment_home"):
                    with st.spinner("正在处理缴费记录..."):
                        result = payment_processor_logic.import_payments_from_excel(uploaded_file)

                        if result['success']:
                            show_success_message(result['message'])
                            if result['errors']:
                                with st.expander("查看导入错误"):
                                    for error in result['errors']:
                                        show_error_message(error)
                            st.rerun()
                        else:
                            show_error_message(result['message'])
            else:
                render_info_card(
                    "缴费导入",
                    "上传收费Excel文件以导入最新缴费记录",
                    "📋",
                    "info"
                )

        with col2:
            st.markdown("### ⚡ 绑定操作")
            st.markdown("---")

            if pending_count > 0:
                render_info_card(
                    f"待处理缴费: {pending_count} 条",
                    "点击下方按钮执行自动绑定并生成批量修改文件",
                    "⏳",
                    "warning"
                )

                if st.button("⚡ 执行绑定并生成文件", type="primary", key="process_binding_home"):
                    with st.spinner("正在处理绑定任务..."):
                        result = payment_processor_logic.process_pending_payments_and_generate_export()

                        if result['success']:
                            show_success_message(result['message'])

                            if result['export_file']:
                                # 提供文件下载
                                if os.path.exists(result['export_file']):
                                    with open(result['export_file'], 'rb') as file:
                                        st.download_button(
                                            label="📥 下载绑定文件",
                                            data=file.read(),
                                            file_name=os.path.basename(result['export_file']),
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                        )
                            st.rerun()
                        else:
                            show_error_message(result['message'])
            else:
                render_info_card(
                    "暂无待处理",
                    "目前没有待处理的缴费记录，请先导入缴费数据",
                    "✅",
                    "success"
                )

        # 系统状态信息
        render_section_divider("ℹ️ 系统状态")

        col1, col2 = st.columns(2)

        with col1:
            render_info_card(
                "最近操作时间",
                f"""
                上次缴费导入: **{settings.get('上次缴费导入时间', '未导入')}**<br>
                上次用户列表导入: **{settings.get('上次用户列表导入时间', '未导入')}**
                """,
                "⏰",
                "info"
            )

        with col2:
            # 获取下次自动维护时间
            next_run_info = ""
            if st.session_state.get('scheduler_started', False):
                from utils.scheduler import get_scheduler
                scheduler = get_scheduler()
                next_run = scheduler.get_next_run_time()
                if next_run:
                    next_run_info = f"<br>下次自动维护: **{next_run.strftime('%Y-%m-%d %H:%M:%S')}**"

            render_info_card(
                "系统设置",
                f"""
                上次自动维护: **{settings.get('上次自动维护执行时间', '未执行')}**{next_run_info}<br>
                0元账号状态: **{settings.get('0元账号启用状态', '未知')}**
                """,
                "⚙️",
                "info"
            )

        # 系统维护
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])

        with col2:
            if st.button("🔧 执行系统维护", type="primary", use_container_width=True):
                with st.spinner("正在执行系统维护..."):
                    maintenance_result = system_maintenance.run_daily_maintenance()

                    if maintenance_result['success']:
                        show_success_message(f"维护完成: {maintenance_result['message']}")

                        # 显示详细统计
                        if (maintenance_result.get('released_count', 0) > 0 or
                            maintenance_result.get('expired_count', 0) > 0 or
                            maintenance_result.get('subscription_expired_count', 0) > 0):
                            st.write("**维护详情:**")
                            if maintenance_result.get('released_count', 0) > 0:
                                st.write(f"- 🔓 释放了 {maintenance_result['released_count']} 个过期绑定")
                            if maintenance_result.get('expired_count', 0) > 0:
                                st.write(f"- ❌ 标记了 {maintenance_result['expired_count']} 个过期账号")
                            if maintenance_result.get('subscription_expired_count', 0) > 0:
                                st.write(f"- 📅 标记了 {maintenance_result['subscription_expired_count']} 个到期套餐")

                        st.rerun()
                    else:
                        show_error_message(f"维护失败: {maintenance_result['message']}")

except Exception as e:
    show_error_message(f"页面加载错误: {e}")
    st.info("请检查数据库连接和系统配置")