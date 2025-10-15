#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户列表页面 - 实际绑定关系管理与数据校准
User List Page - Actual Binding Relationship Management & Data Calibration
"""

import os

# 使用轮询监视器避免 inotify 限制带来的崩溃
os.environ.setdefault("STREAMLIT_WATCHDOG_TYPE", "polling")

import streamlit as st
import pandas as pd
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import ISPAccountOperations, SystemSettingsOperations
from database.models import db_manager
from utils.excel_handler import export_processor
from ui_components import (
    apply_global_style, render_page_header, render_stats_row,
    render_dataframe_with_style, show_success_message, show_error_message,
    render_section_divider, render_empty_state, render_info_card,
    render_action_card
)

st.set_page_config(
    page_title="用户列表 - 校园网账号管理系统",
    page_icon="👥",
    layout="wide"
)

# 应用全局样式
apply_global_style()

# 页面标题
render_page_header(
    "用户列表管理",
    "管理实际用户绑定关系，每月导入一次进行数据校准",
    "👥"
)

# 用户列表操作函数
def process_user_list_import(file_buffer):
    """处理用户列表导入"""
    result = {
        'success': False,
        'message': '',
        'processed_count': 0,
        'error_count': 0,
        'errors': []
    }

    try:
        # 读取Excel文件
        df = pd.read_excel(file_buffer)
        df.columns = df.columns.str.strip()

        # 字段名映射（兼容不同的列名）
        column_mapping = {
            '绑定套餐组': '绑定套餐',
            '用户名称': '用户姓名',
        }

        # 应用列名映射
        df.rename(columns=column_mapping, inplace=True)

        # 验证必需列（运营商账号至少需要一个）
        required_columns = ['用户账号', '绑定套餐', '用户姓名', '用户类别', '到期日期']
        optional_isp_columns = ['移动账号', '联通账号', '电信账号']

        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            result['message'] = f"缺少必需列: {', '.join(missing_columns)}"
            result['errors'].append(f"当前列名: {list(df.columns)}")
            return result

        # 处理数据
        for index, row in df.iterrows():
            try:
                # 数据清理和验证
                用户账号 = str(row['用户账号']).strip()
                绑定套餐 = str(row['绑定套餐']).strip() if pd.notna(row['绑定套餐']) else ''
                用户姓名 = str(row['用户姓名']).strip() if pd.notna(row['用户姓名']) else ''
                用户类别 = str(row['用户类别']).strip() if pd.notna(row['用户类别']) else ''

                # 读取三大运营商账号（可能不存在某些列）
                移动账号 = str(row['移动账号']).strip() if '移动账号' in df.columns and pd.notna(row.get('移动账号')) else ''
                联通账号 = str(row['联通账号']).strip() if '联通账号' in df.columns and pd.notna(row.get('联通账号')) else ''
                电信账号 = str(row['电信账号']).strip() if '电信账号' in df.columns and pd.notna(row.get('电信账号')) else ''

                # 处理到期日期
                try:
                    if pd.notna(row['到期日期']):
                        if isinstance(row['到期日期'], pd.Timestamp):
                            到期日期 = row['到期日期'].date()
                        else:
                            到期日期 = pd.to_datetime(row['到期日期']).date()
                    else:
                        到期日期 = None
                except:
                    到期日期 = None

                if not 用户账号:
                    result['errors'].append(f"第{index+2}行: 用户账号不能为空")
                    result['error_count'] += 1
                    continue

                # 插入或更新用户列表（包含三大运营商账号）
                query = '''
                    INSERT OR REPLACE INTO user_list
                    (用户账号, 绑定套餐, 用户姓名, 用户类别, 移动账号, 联通账号, 电信账号, 到期日期, 导入时间, 更新时间)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                '''

                db_manager.execute_update(query, (
                    用户账号, 绑定套餐, 用户姓名, 用户类别, 移动账号, 联通账号, 电信账号, 到期日期
                ))

                result['processed_count'] += 1

            except Exception as e:
                result['errors'].append(f"第{index+2}行处理错误: {e}")
                result['error_count'] += 1

        result['success'] = result['processed_count'] > 0
        result['message'] = f"成功处理 {result['processed_count']} 条用户记录"

        if result['error_count'] > 0:
            result['message'] += f"，{result['error_count']} 条失败"

        # 更新导入时间
        if result['success']:
            from datetime import datetime
            SystemSettingsOperations.set_setting(
                '上次用户列表导入时间',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )

    except Exception as e:
        result['message'] = f"文件处理失败: {e}"

    return result

def sync_bindings_from_user_list():
    """从用户列表同步绑定关系到账号池（批量优化版本）"""
    result = {
        'success': False,
        'message': '',
        'updated_count': 0,
        'created_count': 0,
        'error_count': 0
    }

    try:
        # 使用批量 SQL 操作，避免逐条查询
        with db_manager.get_connection(enable_performance_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")

            try:
                # 1. 批量更新已存在的账号（使用 JOIN）
                update_query = '''
                    UPDATE isp_accounts
                    SET 状态 = '已使用',
                        绑定的学号 = (SELECT 用户账号 FROM user_list WHERE user_list.移动账号 = isp_accounts.账号),
                        绑定的套餐到期日 = (SELECT 到期日期 FROM user_list WHERE user_list.移动账号 = isp_accounts.账号),
                        更新时间 = datetime('now', 'localtime')
                    WHERE 账号 IN (SELECT 移动账号 FROM user_list WHERE 移动账号 IS NOT NULL AND 移动账号 != '')
                '''
                cursor.execute(update_query)
                result['updated_count'] = cursor.rowcount

                # 2. 批量创建不存在的账号（找出 user_list 中有但 isp_accounts 中没有的账号）
                create_query = '''
                    INSERT OR IGNORE INTO isp_accounts (账号, 账号类型, 状态, 绑定的学号, 绑定的套餐到期日, 创建时间, 更新时间)
                    SELECT
                        ul.移动账号,
                        '未知' as 账号类型,
                        '已停机' as 状态,
                        ul.用户账号 as 绑定的学号,
                        ul.到期日期 as 绑定的套餐到期日,
                        datetime('now', 'localtime'),
                        datetime('now', 'localtime')
                    FROM user_list ul
                    WHERE ul.移动账号 IS NOT NULL
                        AND ul.移动账号 != ''
                        AND ul.移动账号 NOT IN (SELECT 账号 FROM isp_accounts)
                '''
                cursor.execute(create_query)
                result['created_count'] = cursor.rowcount

                cursor.execute("COMMIT")
                result['success'] = True

            except Exception as e:
                cursor.execute("ROLLBACK")
                raise e

        message_parts = []
        if result['updated_count'] > 0:
            message_parts.append(f"更新了 {result['updated_count']} 个现有账号")
        if result['created_count'] > 0:
            message_parts.append(f"新建了 {result['created_count']} 个缺失账号")

        result['message'] = f"同步完成：{', '.join(message_parts) if message_parts else '无需更新'}"

    except Exception as e:
        result['message'] = f"同步失败: {e}"
        result['success'] = False

    return result

# 导入用户列表模块
render_section_divider("📤 导入用户列表")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("#### 📁 上传用户列表文件")
    uploaded_file = st.file_uploader(
        "选择用户列表Excel文件",
        type=['xlsx', 'xls'],
        help="Excel文件应包含：用户账号、绑定套餐、用户姓名、用户类别、移动账号/联通账号/电信账号（至少一个）、到期日期",
        key="user_list_upload"
    )

    if uploaded_file is not None:
        if st.button("📤 导入用户列表", type="primary", width='stretch'):
            with st.spinner("正在处理用户列表数据..."):
                result = process_user_list_import(uploaded_file)

                if result['success']:
                    show_success_message(result['message'])

                    if result['errors']:
                        with st.expander("⚠️ 查看导入错误详情"):
                            for error in result['errors']:
                                show_error_message(error)
                    st.rerun()
                else:
                    show_error_message(result['message'])

with col2:
    render_info_card(
        "导入模板",
        "下载用户列表标准模板，按照模板格式填写用户信息后上传",
        "📋",
        "info"
    )

    # 创建用户列表模板（包含三大运营商，兼容不同列名）
    template_data = [{
        '用户账号': '示例学号',
        '绑定套餐组': '30元套餐',  # 也可用"绑定套餐"
        '用户名称': '张三',         # 也可用"用户姓名"
        '用户类别': '本科生',
        '移动账号': '示例移动账号',
        '联通账号': '示例联通账号',
        '电信账号': '示例电信账号',
        '到期日期': '2024-12-31'
    }]

    try:
        template_path = export_processor.save_to_excel(
            template_data,
            "用户列表导入模板.xlsx",
            "用户列表"
        )

        if os.path.exists(template_path):
            with open(template_path, 'rb') as file:
                st.download_button(
                    label="📋 下载导入模板",
                    data=file.read(),
                    file_name="用户列表导入模板.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width='stretch'
                )
    except Exception as e:
        show_error_message(f"模板生成失败: {e}")

# 数据校准
render_section_divider("🔄 数据校准")

col1, col2 = st.columns([1, 1])

with col1:
    render_info_card(
        "校准说明",
        """
        <strong>数据校准流程：</strong><br>
        • 将用户列表的绑定关系同步到账号池<br>
        • 更新账号状态和绑定信息<br>
        • 确保数据一致性<br>
        • 建议每月导入后执行一次
        """,
        "📚",
        "info"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 执行数据校准", type="primary", width='stretch', key="sync_btn"):
        with st.spinner("正在同步绑定关系..."):
            result = sync_bindings_from_user_list()

            if result['success']:
                show_success_message(result['message'])
                st.rerun()
            else:
                show_error_message(result['message'])

# 用户列表查询
render_section_divider("🔍 用户列表查询")

col1, col2, col3 = st.columns(3)

with col1:
    search_user = st.text_input("用户账号", placeholder="输入用户账号", key="search_user_acc")

with col2:
    search_name = st.text_input("用户姓名", placeholder="输入用户姓名", key="search_user_name")

with col3:
    filter_category = st.selectbox(
        "用户类别",
        ["全部", "本科生", "研究生", "教职工", "其他"],
        key="filter_user_category"
    )

# 执行查询
try:
    conditions = []
    params = []

    if search_user:
        conditions.append("用户账号 LIKE ?")
        params.append(f"%{search_user}%")

    if search_name:
        conditions.append("用户姓名 LIKE ?")
        params.append(f"%{search_name}%")

    if filter_category != "全部":
        conditions.append("用户类别 = ?")
        params.append(filter_category)

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    query = f"SELECT * FROM user_list WHERE {where_clause} ORDER BY 更新时间 DESC"

    users = db_manager.execute_query(query, tuple(params))

    if users:
        render_section_divider(f"📋 用户列表 ({len(users)} 条记录)")

        df_data = []
        for user in users:
            df_data.append({
                '用户账号': user['用户账号'],
                '用户姓名': user['用户姓名'],
                '用户类别': user['用户类别'],
                '绑定套餐': user['绑定套餐'],
                '移动账号': user['移动账号'] or '',
                '联通账号': user['联通账号'] or '',
                '电信账号': user['电信账号'] or '',
                '到期日期': user['到期日期'],
                '更新时间': user['更新时间']
            })

        df = pd.DataFrame(df_data)
        render_dataframe_with_style(df)

        # 导出功能
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("📤 导出用户列表", width='stretch'):
                try:
                    export_path = export_processor.save_to_excel(
                        df_data,
                        f"用户列表_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        "用户列表"
                    )

                    if os.path.exists(export_path):
                        with open(export_path, 'rb') as file:
                            st.download_button(
                                label="📥 下载导出文件",
                                data=file.read(),
                                file_name=os.path.basename(export_path),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="download_user_list"
                            )
                except Exception as e:
                    show_error_message(f"导出失败: {e}")

    else:
        render_empty_state(
            "没有找到匹配的用户记录",
            suggestions=[
                "检查搜索条件是否正确",
                "尝试清除部分筛选条件",
                "如果是新系统，请先导入用户列表"
            ]
        )

except Exception as e:
    show_error_message(f"查询过程中发生错误: {e}")

# 统计信息
try:
    stats_query = '''
        SELECT
            COUNT(*) as total_users,
            COUNT(CASE WHEN 移动账号 IS NOT NULL AND 移动账号 != '' THEN 1 END) as mobile_users,
            COUNT(CASE WHEN 联通账号 IS NOT NULL AND 联通账号 != '' THEN 1 END) as unicom_users,
            COUNT(CASE WHEN 电信账号 IS NOT NULL AND 电信账号 != '' THEN 1 END) as telecom_users,
            COUNT(CASE WHEN (移动账号 IS NOT NULL AND 移动账号 != '')
                         OR (联通账号 IS NOT NULL AND 联通账号 != '')
                         OR (电信账号 IS NOT NULL AND 电信账号 != '') THEN 1 END) as bound_users
        FROM user_list
    '''

    stats_result = db_manager.execute_query(stats_query)

    if stats_result:
        stats = stats_result[0]

        render_section_divider("📈 用户统计")

        stats_data = [
            {'label': '总用户数', 'value': stats['total_users']},
            {'label': '已绑定用户', 'value': stats['bound_users']},
            {'label': '移动用户', 'value': stats['mobile_users']},
            {'label': '联通用户', 'value': stats['unicom_users']},
            {'label': '电信用户', 'value': stats['telecom_users']}
        ]

        render_stats_row(stats_data, icons=['👥', '🔗', '📱', '📞', '☎️'])

except Exception as e:
    show_error_message(f"获取统计信息失败: {e}")

# 显示最后导入时间
try:
    last_import = SystemSettingsOperations.get_setting('上次用户列表导入时间')
    if last_import and last_import != '1970-01-01 00:00:00':
        st.markdown("---")
        st.info(f"📅 上次用户列表导入时间: **{last_import}**")
    else:
        st.markdown("---")
        st.warning("📅 还未导入过用户列表")
except:
    pass
