#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统设置页面 - 配置管理与系统维护
System Settings Page - Configuration & System Maintenance
"""

import streamlit as st
from datetime import datetime, date
import sys
import os
import pandas as pd

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import SystemSettingsOperations, MaintenanceOperations, AccountTypeRuleOperations
from utils.business_logic import system_maintenance, AccountManager
from ui_components import (
    apply_global_style,
    render_page_header,
    render_section_divider,
    render_info_card,
    render_stats_row,
    show_success_message,
    show_error_message,
    show_warning_message,
    show_info_message,
    render_progress_card
)

st.set_page_config(
    page_title="系统设置 - 校园网账号管理系统",
    page_icon="⚙️",
    layout="wide"
)

# 应用全局样式
apply_global_style()

# 页面标题
render_page_header(
    title="系统设置",
    subtitle="管理系统全局配置和执行维护任务",
    icon="⚙️"
)

# ==================== 0元账号配置 ====================
render_section_divider("💰 0元账号配置")

col1, col2 = st.columns(2)

with col1:
    # 获取当前设置
    current_status = SystemSettingsOperations.get_setting('0元账号启用状态') or '启用'
    current_expiry = SystemSettingsOperations.get_setting('0元账号有效期') or '2025-12-31'

    # 启用状态开关
    enable_zero_cost = st.toggle(
        "启用0元账号特殊有效期",
        value=(current_status == '启用'),
        help="开启后，0元账号将使用统一的到期日期，而不是根据账号类型计算"
    )

    # 到期日期设置
    try:
        default_date = datetime.strptime(current_expiry, '%Y-%m-%d').date()
    except:
        default_date = date(2025, 12, 31)

    expiry_date = st.date_input(
        "0元账号统一到期日",
        value=default_date,
        help="所有0元账号的统一到期日期"
    )

    if st.button("💾 保存0元账号设置", type="primary"):
        try:
            # 保存设置
            SystemSettingsOperations.set_setting(
                '0元账号启用状态',
                '启用' if enable_zero_cost else '禁用'
            )

            SystemSettingsOperations.set_setting(
                '0元账号有效期',
                expiry_date.strftime('%Y-%m-%d')
            )

            show_success_message("0元账号设置已保存")
            st.rerun()

        except Exception as e:
            show_error_message(f"保存失败: {e}")

with col2:
    render_info_card(
        title="当前配置",
        content=f"启用状态: {current_status}\n统一到期日: {current_expiry}",
        icon="📋",
        color="info"
    )

    render_info_card(
        title="配置说明",
        content="• 启用后，所有标记为'0元账号'的账号将使用统一到期日\n• 禁用后，0元账号将按照账号类型规则计算到期日\n• 修改设置后，新导入的账号将采用新配置",
        icon="💡",
        color="success"
    )

# ==================== 账号类型策略 ====================
render_section_divider("🧩 账号类型策略")

rules = AccountTypeRuleOperations.list_rules()
col_rules, col_editor = st.columns([1.1, 1.4])

with col_rules:
    if rules:
        display_rows = []
        for rule in rules:
            display_rows.append({
                '账号类型': rule['账号类型'],
                '允许绑定': '是' if rule['允许绑定'] else '否',
                '生命周期（月）': rule.get('生命周期月份') if rule.get('生命周期月份') is not None else '',
                '固定开始日期': rule.get('自定义开始日期') or '',
                '固定结束日期': rule.get('自定义结束日期') or '',
                '最近更新': rule.get('更新时间') or ''
            })
        st.dataframe(
            pd.DataFrame(display_rows),
            hide_index=True,
            use_container_width=True
        )
    else:
        render_info_card(
            title="规则说明",
            content="当前未设置自定义规则，系统将默认允许所有账号类型绑定，生命周期依账号类型推导。",
            icon="ℹ️",
            color="info"
        )

with col_editor:
    st.markdown("#### ✏️ 新增或更新规则")
    rule_options = ["新建规则"] + [rule['账号类型'] for rule in rules]

    with st.form("account_type_rule_form"):
        selected_option = st.selectbox(
            "选择账号类型",
            rule_options,
            help="选择已有类型进行编辑，或选择“新建规则”输入新的账号类型标识"
        )

        if selected_option == "新建规则":
            account_type_value = st.text_input(
                "账号类型标识",
                placeholder="例如：202409 或 未知",
                help="与导入表格中的账号类型字段保持一致"
            ).strip()
            existing_rule = None
        else:
            account_type_value = selected_option
            existing_rule = AccountTypeRuleOperations.get_rule(account_type_value)

        allow_binding = st.toggle(
            "允许绑定",
            value=(existing_rule['允许绑定'] if existing_rule else True),
            help="关闭后，该类型账号不会参与自动绑定、换绑等需要可用账号的流程"
        )

        lifecycle_default = existing_rule.get('生命周期月份') if existing_rule else None
        use_custom_lifecycle = st.toggle(
            "自定义生命周期（月）",
            value=(lifecycle_default is not None),
            help="开启后按指定月数计算结束日期；关闭则使用账号类型默认逻辑"
        )
        lifecycle_months = st.number_input(
            "生命周期（月）",
            min_value=0,
            max_value=120,
            value=int(lifecycle_default if lifecycle_default is not None else 12),
            step=1,
            disabled=not use_custom_lifecycle,
            help="设为0表示开始日当天到期"
        )

        start_default_str = existing_rule.get('自定义开始日期') if existing_rule else None
        use_custom_start = st.toggle(
            "指定固定开始日期",
            value=bool(start_default_str),
            help="适用于无法从账号类型推导开始日期的账号"
        )
        if use_custom_start:
            try:
                start_default = datetime.strptime(start_default_str, '%Y-%m-%d').date() if start_default_str else date.today()
            except Exception:
                start_default = date.today()
            custom_start_date = st.date_input("固定开始日期", value=start_default)
        else:
            custom_start_date = None

        end_default_str = existing_rule.get('自定义结束日期') if existing_rule else None
        use_custom_end = st.toggle(
            "指定固定结束日期",
            value=bool(end_default_str),
            help="开启后将覆盖生命周期（月）的计算结果"
        )
        if use_custom_end:
            try:
                end_default = datetime.strptime(end_default_str, '%Y-%m-%d').date() if end_default_str else date.today()
            except Exception:
                end_default = date.today()
            custom_end_date = st.date_input("固定结束日期", value=end_default)
        else:
            custom_end_date = None

        apply_now = st.checkbox("保存后立即同步现有账号的生命周期", value=True)
        save_rule = st.form_submit_button("💾 保存规则", type="primary", use_container_width=True)

    if save_rule:
        if not account_type_value:
            show_error_message("账号类型标识不能为空")
        elif use_custom_start and use_custom_end and custom_start_date and custom_end_date and custom_start_date > custom_end_date:
            show_error_message("固定开始日期不能晚于固定结束日期")
        else:
            lifecycle_value = int(lifecycle_months) if use_custom_lifecycle else None
            success = AccountTypeRuleOperations.upsert_rule(
                account_type_value,
                allow_binding,
                lifecycle_value,
                custom_start_date,
                custom_end_date
            )
            if success:
                sync_message = ""
                if apply_now:
                    sync_result = AccountManager.recalculate_lifecycle_for_type(account_type_value)
                    if sync_result['success']:
                        sync_message = sync_result['message']
                    else:
                        show_warning_message(sync_result['message'])
                show_success_message("规则已保存" + (f"：{sync_message}" if sync_message else ""))
                st.rerun()
            else:
                show_error_message("保存失败，请检查日志")

with st.expander("🗑️ 删除账号类型规则"):
    if rules:
        with st.form("delete_account_type_rule"):
            delete_target = st.selectbox(
                "选择要删除的账号类型",
                [rule['账号类型'] for rule in rules],
                help="删除后该账号类型将恢复为默认规则"
            )
            confirm_delete = st.form_submit_button("删除规则", use_container_width=True)
            if confirm_delete:
                if AccountTypeRuleOperations.delete_rule(delete_target):
                    show_success_message(f"已删除账号类型 {delete_target} 的自定义规则")
                    st.rerun()
                else:
                    show_error_message("删除失败，请检查日志")
    else:
        st.caption("暂无可删除的账号类型规则。设置规则后可在此处删除。")

# ==================== 数据维护 ====================
render_section_divider("🔧 数据维护")

col1, col2 = st.columns(2)

with col1:
    render_info_card(
        title="自动维护任务",
        content="系统将自动执行账号释放和过期标记等维护任务，保持数据准确性",
        icon="🤖",
        color="info"
    )

    # 获取上次维护时间
    last_maintenance = SystemSettingsOperations.get_setting('上次自动维护执行时间')

    if last_maintenance and last_maintenance != '1970-01-01 00:00:00':
        show_info_message(f"上次执行时间: {last_maintenance}", "⏰")
    else:
        show_warning_message("尚未执行过自动维护", "⚠️")

    if st.button("🔧 立即执行维护任务", type="primary", use_container_width=True):
        with st.spinner("正在执行系统维护..."):
            result = system_maintenance.run_daily_maintenance()

            if result['success']:
                show_success_message("维护完成")
                st.write(f"**维护结果:** {result['message']}")

                stats_data = []
                icons_list = []

                if result['released_count'] > 0:
                    stats_data.append({
                        'label': '释放绑定',
                        'value': f"{result['released_count']} 个"
                    })
                    icons_list.append('🔓')

                if result['expired_count'] > 0:
                    stats_data.append({
                        'label': '过期账号',
                        'value': f"{result['expired_count']} 个"
                    })
                    icons_list.append('❌')

                if result.get('subscription_expired_count', 0) > 0:
                    stats_data.append({
                        'label': '到期套餐',
                        'value': f"{result['subscription_expired_count']} 个"
                    })
                    icons_list.append('📅')

                if stats_data:
                    render_stats_row(stats_data, icons_list)

                st.rerun()
            else:
                show_error_message(f"维护失败: {result['message']}")

    render_info_card(
        title="维护任务包括",
        content="1. 🔓 释放套餐已过期但账号未过期的绑定\n2. ❌ 将生命周期结束的账号标记为过期\n3. 📅 标记用户列表中套餐到期的记录\n4. ⏰ 更新系统维护时间戳",
        icon="📖",
        color="success"
    )

with col2:
    render_info_card(
        title="手动维护操作",
        content="可单独执行特定的维护操作，不影响自动维护时间戳",
        icon="🛠️",
        color="warning"
    )

    # 手动释放过期绑定
    if st.button("🔓 仅释放过期绑定", use_container_width=True):
        with st.spinner("正在释放过期绑定..."):
            try:
                released_count = MaintenanceOperations.auto_release_expired_bindings()
                show_success_message(f"释放了 {released_count} 个过期绑定")
            except Exception as e:
                show_error_message(f"操作失败: {e}")

    # 手动标记过期账号
    if st.button("❌ 仅标记过期账号", use_container_width=True):
        with st.spinner("正在标记过期账号..."):
            try:
                expired_count = MaintenanceOperations.auto_expire_lifecycle_ended()
                show_success_message(f"标记了 {expired_count} 个过期账号")
            except Exception as e:
                show_error_message(f"操作失败: {e}")

    show_warning_message("手动操作不会更新系统维护时间戳")

# ==================== 系统状态 ====================
render_section_divider("ℹ️ 系统状态")

try:
    status = system_maintenance.get_system_status()

    if 'error' not in status:
        settings = status['settings']
        stats = status['stats']

        col1, col2 = st.columns(2)

        with col1:
            render_info_card(
                title="时间状态",
                content=f"上次缴费导入: {settings.get('上次缴费导入时间', '未导入')}\n上次用户列表导入: {settings.get('上次用户列表导入时间', '未导入')}\n上次自动维护: {settings.get('上次自动维护执行时间', '未执行')}",
                icon="⏰",
                color="info"
            )

        with col2:
            render_info_card(
                title="账号统计",
                content=f"总账号数: {stats.get('总账号数', 0)}\n可用账号: {stats.get('账号_未使用', 0)}\n已使用账号: {stats.get('账号_已使用', 0)}\n已过期账号: {stats.get('账号_已过期', 0)}\n待处理缴费: {stats.get('待处理缴费', 0)}",
                icon="📊",
                color="success"
            )

        # 可视化账号使用情况
        col1, col2, col3 = st.columns(3)

        total_accounts = stats.get('总账号数', 0)
        available_accounts = stats.get('账号_未使用', 0)
        used_accounts = stats.get('账号_已使用', 0)
        expired_accounts = stats.get('账号_已过期', 0)

        with col1:
            if total_accounts > 0:
                render_progress_card("可用账号", available_accounts, total_accounts, "🟢")

        with col2:
            if total_accounts > 0:
                render_progress_card("已使用账号", used_accounts, total_accounts, "🟡")

        with col3:
            if total_accounts > 0:
                render_progress_card("已过期账号", expired_accounts, total_accounts, "🔴")

    else:
        show_error_message(f"获取系统状态失败: {status['error']}")

except Exception as e:
    show_error_message(f"系统状态加载错误: {e}")

# ==================== 高级设置 ====================
render_section_divider("🔬 高级设置")

with st.expander("⚠️ 数据库操作 - 请谨慎使用", expanded=False):
    show_warning_message("以下操作可能影响系统数据，请谨慎使用")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ 清除所有缴费记录", type="secondary", use_container_width=True):
            if st.session_state.get('confirm_clear_payments', False):
                try:
                    from database.models import db_manager
                    db_manager.execute_update("DELETE FROM payment_logs")
                    show_success_message("缴费记录已清除")
                    st.session_state['confirm_clear_payments'] = False
                    st.rerun()
                except Exception as e:
                    show_error_message(f"清除失败: {e}")
            else:
                st.session_state['confirm_clear_payments'] = True
                show_warning_message("再次点击确认清除所有缴费记录")

    with col2:
        if st.button("🔄 重置系统时间戳", type="secondary", use_container_width=True):
            try:
                SystemSettingsOperations.set_setting('上次缴费导入时间', '1970-01-01 00:00:00')
                SystemSettingsOperations.set_setting('上次用户列表导入时间', '1970-01-01 00:00:00')
                SystemSettingsOperations.set_setting('上次自动维护执行时间', '1970-01-01 00:00:00')

                show_success_message("系统时间戳已重置")
                st.rerun()
            except Exception as e:
                show_error_message(f"重置失败: {e}")

    # 清除用户列表
    if st.button("🗑️ 清除用户列表数据", type="secondary", use_container_width=True):
        if st.session_state.get('confirm_clear_users', False):
            try:
                from database.models import db_manager
                db_manager.execute_update("DELETE FROM user_list")
                show_success_message("用户列表已清除")
                st.session_state['confirm_clear_users'] = False
                st.rerun()
            except Exception as e:
                show_error_message(f"清除失败: {e}")
        else:
            st.session_state['confirm_clear_users'] = True
            show_warning_message("再次点击确认清除用户列表数据")

# ==================== 系统信息 ====================
with st.expander("📋 系统信息", expanded=False):
    render_info_card(
        title="系统版本",
        content="校园网账号管理系统 v2.0\n基于 Streamlit + SQLite\n多页面架构 + 用户列表数据校准",
        icon="🏷️",
        color="info"
    )

    st.write("**数据库位置:**")
    st.code("data/account_manager.db")

    st.write("**支持的文件格式:**")
    st.code("Excel文件: .xlsx, .xls")

    # 显示数据目录内容
    st.write("**数据目录内容:**")
    data_dir = "data"
    if os.path.exists(data_dir):
        files = os.listdir(data_dir)
        if files:
            for file in files:
                file_path = os.path.join(data_dir, file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    size_mb = size / 1024 / 1024
                    st.text(f"📄 {file} ({size_mb:.2f} MB)")
        else:
            st.text("目录为空")
    else:
        st.text("数据目录不存在")

    # 数据库表统计
    try:
        from database.models import db_manager

        st.write("**数据库表统计:**")

        stats_list = []

        # 账号表统计
        account_count = db_manager.execute_query("SELECT COUNT(*) as count FROM isp_accounts")[0]['count']
        stats_list.append({'label': 'ISP账号', 'value': f"{account_count} 条"})

        # 用户列表统计
        user_count = db_manager.execute_query("SELECT COUNT(*) as count FROM user_list")[0]['count']
        stats_list.append({'label': '用户列表', 'value': f"{user_count} 条"})

        # 缴费记录统计
        payment_count = db_manager.execute_query("SELECT COUNT(*) as count FROM payment_logs")[0]['count']
        stats_list.append({'label': '缴费记录', 'value': f"{payment_count} 条"})

        # 系统设置统计
        settings_count = db_manager.execute_query("SELECT COUNT(*) as count FROM system_settings")[0]['count']
        stats_list.append({'label': '系统设置', 'value': f"{settings_count} 条"})

        render_stats_row(stats_list, ['📱', '👥', '💰', '⚙️'])

    except Exception as e:
        show_error_message(f"获取数据库统计失败: {e}")
