#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绑定导出页面 - 缴费处理与账号绑定
Binding Export Page - Payment Processing & Account Binding
"""

import os

# 使用轮询监视器避免 inotify 限制带来的崩溃
os.environ.setdefault("STREAMLIT_WATCHDOG_TYPE", "polling")

import streamlit as st
import pandas as pd
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.business_logic import payment_processor_logic
from database.operations import PaymentOperations
from utils.excel_handler import export_processor
from ui_components import (
    apply_global_style,
    render_page_header,
    render_section_divider,
    render_info_card,
    render_stats_row,
    render_dataframe_with_style,
    show_success_message,
    show_error_message,
    show_info_message,
    show_warning_message,
    render_empty_state,
    render_progress_card,
    ProgressTracker
)

st.set_page_config(
    page_title="绑定导出 - 校园网账号管理系统",
    page_icon="🚀",
    layout="wide"
)

# 应用全局样式
apply_global_style()

# 页面标题
render_page_header(
    title="绑定与导出",
    subtitle="完成从缴费记录导入到账号绑定再到生成批量修改文件的完整流程",
    icon="🚀"
)

# ==================== 第一步：导入最新缴费信息 ====================
render_section_divider("📤 第一步：导入最新缴费信息")

render_info_card(
    title="操作说明",
    content="上传包含用户账号、收费时间、收费金额的Excel文件，系统将自动解析并存储待处理的缴费记录",
    icon="💡",
    color="info"
)

col1, col2 = st.columns([2, 1])

with col1:
    payment_file = st.file_uploader(
        "上传收费Excel文件",
        type=['xlsx', 'xls'],
        help="Excel文件应包含：用户账号、收费时间、收费金额",
        key="payment_upload"
    )

    if payment_file is not None:
        if st.button("📥 导入缴费记录", type="primary"):
            with st.spinner("正在处理缴费记录..."):
                result = payment_processor_logic.import_payments_from_excel(payment_file)

                if result['success']:
                    show_success_message(result['message'])

                    if result['errors']:
                        with st.expander("查看导入错误详情"):
                            for error in result['errors']:
                                show_error_message(error)
                    st.rerun()
                else:
                    show_error_message(result['message'])
                    if result['errors']:
                        for error in result['errors'][:3]:
                            show_error_message(error)

with col2:
    try:
        template_path = export_processor.create_template_file('payment_import')
        if os.path.exists(template_path):
            with open(template_path, 'rb') as file:
                st.download_button(
                    label="📋 下载缴费模板",
                    data=file.read(),
                    file_name="缴费导入模板.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    except Exception as e:
        show_error_message(f"模板生成失败: {e}")

# 显示当前待处理缴费统计
try:
    pending_payments = PaymentOperations.get_pending_payments()
    pending_count = len(pending_payments)

    if pending_count > 0:
        show_info_message(f"当前有 {pending_count} 条缴费记录待处理", "📋")

        # 显示最近的几条记录
        if st.checkbox("显示待处理记录详情"):
            recent_payments = pending_payments[:10]  # 只显示前10条
            df_data = []

            for payment in recent_payments:
                df_data.append({
                    '学号': payment['学号'],
                    '缴费时间': payment['缴费时间'],
                    '缴费金额': payment['缴费金额'],
                    '状态': payment['处理状态']
                })

            if df_data:
                df = pd.DataFrame(df_data)
                render_dataframe_with_style(df, status_column='状态')

    else:
        show_success_message("当前没有待处理的缴费记录")

except Exception as e:
    show_error_message(f"获取待处理缴费记录失败: {e}")

# ==================== 第二步：执行绑定任务 ====================
render_section_divider("⚡ 第二步：执行绑定任务")

col1, col2 = st.columns([1, 1])

with col1:
    render_info_card(
        title="绑定流程说明",
        content="""
        1. 🔍 查找可用的上网账号\n
        2. 🔗 将账号绑定到付费学生\n
        3. 📝 更新缴费记录状态\n
        4. 📊 生成绑定统计报告
        """,
        icon="📖",
        color="info"
    )

with col2:
    # 确保 pending_count 在作用域内可用
    if 'pending_count' in locals() and pending_count > 0:
        if st.button("⚡ 开始处理所有待绑定任务", type="primary", width='stretch'):
            try:
                # 创建进度追踪器容器
                progress_container = st.container()
                
                with progress_container:
                    tracker = ProgressTracker(
                        total=pending_count,
                        title="绑定任务处理",
                        show_eta=True
                    )
                    
                    # 定义进度回调函数
                    def update_progress(info):
                        tracker.update(
                            current=info.get('current', 0),
                            message=info.get('message', ''),
                            success_count=info.get('success', 0),
                            failed_count=info.get('failed', 0),
                            step=info.get('step', '')
                        )
                    
                    # 执行绑定任务并传递进度回调
                    result = payment_processor_logic.process_pending_payments_and_generate_export(
                        progress_callback=update_progress
                    )
                    
                    # 标记完成
                    if result['success']:
                        tracker.complete(
                            success_count=result['processed_count'],
                            failed_count=result['failed_count'],
                            message=result['message']
                        )
                    else:
                        tracker.error(result['message'])
                
                # 显示处理结果
                if result['success']:
                    # 显示成功消息
                    show_success_message(result['message'], "🎉")
                    
                    # 显示绑定详情
                    if result['binding_data']:
                        st.write(f"📊 成功绑定了 {len(result['binding_data'])} 个账号:")
                        
                        # 显示绑定结果表格（显示更多信息）
                        binding_df_data = []
                        for item in result['binding_data']:
                            binding_df_data.append({
                                '学号': item.get('学号', ''),
                                '移动账号': item.get('移动账号', ''),
                                '套餐类型': item.get('套餐类型', ''),
                                '到期日期': item.get('到期日期', '')
                            })
                        
                        binding_df = pd.DataFrame(binding_df_data)
                        st.dataframe(binding_df, use_container_width=True)
                        
                        # 显示导出文件信息
                        if result.get('export_file'):
                            st.success(f"📁 导出文件已生成: {os.path.basename(result['export_file'])}")
                    
                    # 等待用户确认后再刷新页面
                    st.info("💡 所有操作已完成并保存到数据库")
                    if st.button("🔄 刷新页面查看最新数据", type="primary"):
                        st.rerun()
                else:
                    show_error_message(result['message'])
                    
                    # 显示详细的失败信息
                    if result.get('failed_count', 0) > 0:
                        st.warning(f"⚠️ 有 {result['failed_count']} 条记录处理失败")
                        
            except Exception as e:
                # 捕获并显示所有异常
                show_error_message(f"执行绑定任务时发生错误: {str(e)}")
                st.error("详细错误信息：")
                st.code(str(e))
                
                # 显示完整的堆栈跟踪
                import traceback
                with st.expander("查看完整错误堆栈"):
                    st.code(traceback.format_exc())
                    
    else:
        show_info_message("没有待处理的缴费记录，请先导入缴费数据", "📭")

# ==================== 第三步：下载批量修改文件 ====================
render_section_divider("📥 第三步：下载批量修改文件")

# 检查是否有最近生成的导出文件
data_dir = "data"
export_files = []

if os.path.exists(data_dir):
    for file in os.listdir(data_dir):
        if file.startswith("绑定导出_") and file.endswith(".xlsx"):
            file_path = os.path.join(data_dir, file)
            file_stat = os.stat(file_path)
            export_files.append({
                'filename': file,
                'path': file_path,
                'size': file_stat.st_size,
                'mtime': file_stat.st_mtime
            })

# 按修改时间排序，最新的在前
export_files.sort(key=lambda x: x['mtime'], reverse=True)

if export_files:
    st.write("**可用的导出文件:**")

    for i, file_info in enumerate(export_files[:5]):  # 只显示最近5个文件
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.write(f"📄 {file_info['filename']}")

        with col2:
            size_mb = file_info['size'] / 1024 / 1024
            st.write(f"📊 {size_mb:.1f} MB")

        with col3:
            try:
                with open(file_info['path'], 'rb') as file:
                    st.download_button(
                        label="📥 下载",
                        data=file.read(),
                        file_name=file_info['filename'],
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_{i}"
                    )
            except Exception as e:
                show_error_message(f"文件读取失败: {e}")

else:
    render_empty_state(
        message="暂无可下载的导出文件",
        suggestions=["请先导入缴费记录", "执行绑定任务后将自动生成导出文件"],
        icon="📭"
    )

# ==================== 绑定失败记录 ====================
render_section_divider("⚠️ 绑定失败记录")

try:
    failed_payments = PaymentOperations.get_failed_payments()

    if failed_payments:
        show_warning_message(f"有 {len(failed_payments)} 条缴费记录处理失败")

        # 显示失败记录
        failed_df_data = []
        for payment in failed_payments:
            failed_df_data.append({
                '学号': payment['学号'],
                '缴费时间': payment['缴费时间'],
                '缴费金额': payment['缴费金额'],
                '处理时间': payment['处理时间'] or '未处理'
            })

        if failed_df_data:
            df = pd.DataFrame(failed_df_data)
            st.dataframe(df, width='stretch')

        render_info_card(
            title="可能的失败原因",
            content="🔋 可用账号池已耗尽\n📊 数据格式错误\n🔧 系统处理异常",
            icon="💡",
            color="warning"
        )

        if st.button("🔄 重新处理失败记录"):
            # 将失败记录状态重置为待处理
            with st.spinner("正在重置失败记录..."):
                try:
                    for payment in failed_payments:
                        PaymentOperations.update_payment_status(payment['记录ID'], '待处理')

                    show_success_message(f"已重置 {len(failed_payments)} 条失败记录，可以重新处理")
                    st.rerun()
                except Exception as e:
                    show_error_message(f"重置失败: {e}")

    else:
        show_success_message("没有处理失败的记录")

except Exception as e:
    show_error_message(f"获取失败记录时出错: {e}")

# ==================== 处理历史统计 ====================
render_section_divider("📊 处理历史")

try:
    from database.models import db_manager

    # 获取处理统计
    stats_query = '''
        SELECT
            处理状态,
            COUNT(*) as count,
            SUM(缴费金额) as total_amount
        FROM payment_logs
        GROUP BY 处理状态
    '''

    stats = db_manager.execute_query(stats_query)

    if stats:
        stats_data = []
        icons_list = []

        for stat in stats:
            if stat['处理状态'] == '待处理':
                stats_data.append({
                    'label': '待处理',
                    'value': f"{stat['count']} 条",
                    'delta': f"¥{stat['total_amount']:.2f}"
                })
                icons_list.append('⏳')
            elif stat['处理状态'] == '已处理':
                stats_data.append({
                    'label': '已处理',
                    'value': f"{stat['count']} 条",
                    'delta': f"¥{stat['total_amount']:.2f}"
                })
                icons_list.append('✅')
            elif stat['处理状态'] == '处理失败':
                stats_data.append({
                    'label': '处理失败',
                    'value': f"{stat['count']} 条",
                    'delta': f"¥{stat['total_amount']:.2f}",
                    'delta_color': 'inverse'
                })
                icons_list.append('❌')

        if stats_data:
            render_stats_row(stats_data, icons_list)

    # 最近处理记录
    recent_query = '''
        SELECT * FROM payment_logs
        WHERE 处理状态 IN ('已处理', '处理失败')
        ORDER BY 处理时间 DESC
        LIMIT 10
    '''

    recent_records = db_manager.execute_query(recent_query)

    if recent_records:
        st.write("**最近处理记录:**")
        recent_df_data = []

        for record in recent_records:
            recent_df_data.append({
                '学号': record['学号'],
                '缴费金额': record['缴费金额'],
                '处理状态': record['处理状态'],
                '处理时间': record['处理时间']
            })

        df = pd.DataFrame(recent_df_data)
        render_dataframe_with_style(df, status_column='处理状态')

except Exception as e:
    show_error_message(f"获取处理历史失败: {e}")
