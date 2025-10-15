#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI 组件库 - 共享的界面组件和样式
UI Components Library - Shared interface components and styles
"""

import streamlit as st
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

# ==================== 样式定义 ====================

# 现代化配色方案
COLORS = {
    'primary': '#1E88E5',      # 主色调 - 蓝色
    'secondary': '#26A69A',    # 辅助色 - 青色
    'success': '#4CAF50',      # 成功 - 绿色
    'warning': '#FF9800',      # 警告 - 橙色
    'danger': '#F44336',       # 危险 - 红色
    'info': '#2196F3',         # 信息 - 浅蓝色
    'light': '#F5F7FA',        # 浅色背景
    'dark': '#263238',         # 深色文字
    'border': '#E0E0E0',       # 边框色
    'gradient_start': '#667eea', # 渐变起始色
    'gradient_end': '#764ba2',   # 渐变结束色
}

# 全局样式
GLOBAL_STYLE = f"""
<style>
    /* 隐藏Streamlit默认元素 */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* 全局字体和背景 */
    .main {{
        background-color: {COLORS['light']};
        font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }}

    /* 标题样式 */
    h1, h2, h3 {{
        color: {COLORS['dark']};
        font-weight: 600;
    }}

    h1 {{
        background: linear-gradient(135deg, {COLORS['gradient_start']}, {COLORS['gradient_end']});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 10px;
        border-bottom: 3px solid {COLORS['primary']};
        margin-bottom: 25px;
    }}

    /* 卡片容器 */
    .card {{
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border-left: 4px solid {COLORS['primary']};
    }}

    /* Metric卡片美化 */
    [data-testid="stMetricValue"] {{
        font-size: 32px;
        font-weight: 700;
        color: {COLORS['primary']};
    }}

    [data-testid="stMetricDelta"] {{
        font-size: 14px;
        font-weight: 500;
    }}

    /* 按钮样式 */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 500;
        padding: 8px 24px;
        transition: all 0.3s ease;
        border: none;
    }}

    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}

    /* 主要按钮 */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['info']});
        color: white;
    }}

    /* 文件上传器美化 */
    [data-testid="stFileUploader"] {{
        background: white;
        border: 2px dashed {COLORS['border']};
        border-radius: 12px;
        padding: 20px;
    }}

    /* 数据表格美化 */
    .dataframe {{
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid {COLORS['border']};
    }}

    /* 侧边栏美化 */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {COLORS['gradient_start']}, {COLORS['gradient_end']});
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
        color: white;
    }}

    /* 分割线 */
    hr {{
        margin: 30px 0;
        border: none;
        border-top: 2px solid {COLORS['border']};
    }}

    /* 信息框美化 */
    .stAlert {{
        border-radius: 8px;
        border-left-width: 4px;
    }}

    /* Tab美化 */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 500;
    }}

    /* 进度条美化 */
    .stProgress > div > div > div {{
        background: linear-gradient(90deg, {COLORS['gradient_start']}, {COLORS['gradient_end']});
    }}
</style>
"""

# ==================== 组件函数 ====================

def apply_global_style():
    """应用全局样式"""
    st.markdown(GLOBAL_STYLE, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str, icon: str = ""):
    """
    渲染页面标题

    Args:
        title: 页面标题
        subtitle: 页面副标题
        icon: emoji图标
    """
    st.markdown(f"""
        <div style="margin-bottom: 20px;">
            <h1>{icon} {title}</h1>
            <p style="color: #666; font-size: 16px; margin-top: -10px;">{subtitle}</p>
        </div>
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value: str, delta: Optional[str] = None,
                       delta_color: str = "normal", icon: str = "📊"):
    """
    渲染指标卡片

    Args:
        label: 指标名称
        value: 指标值
        delta: 变化量
        delta_color: 变化颜色 ("normal", "inverse", "off")
        icon: 图标
    """
    st.markdown(f"""
        <div class="card" style="text-align: center;">
            <div style="font-size: 32px; margin-bottom: 10px;">{icon}</div>
            <div style="color: #666; font-size: 14px; margin-bottom: 5px;">{label}</div>
            <div style="font-size: 32px; font-weight: 700; color: {COLORS['primary']};">{value}</div>
            {f'<div style="color: {COLORS["success"] if delta_color == "normal" else COLORS["danger"]}; font-size: 14px; margin-top: 5px;">{delta}</div>' if delta else ''}
        </div>
    """, unsafe_allow_html=True)


def render_info_card(title: str, content: str, icon: str = "ℹ️", color: str = "info"):
    """
    渲染信息卡片

    Args:
        title: 卡片标题
        content: 卡片内容
        icon: 图标
        color: 颜色主题 ("info", "success", "warning", "danger")
    """
    card_color = COLORS.get(color, COLORS['info'])

    st.markdown(f"""
        <div class="card" style="border-left-color: {card_color};">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 24px; margin-right: 10px;">{icon}</span>
                <h3 style="margin: 0; font-size: 18px; color: {card_color};">{title}</h3>
            </div>
            <p style="margin: 0; color: #555; line-height: 1.6;">{content}</p>
        </div>
    """, unsafe_allow_html=True)


def render_status_badge(status: str) -> str:
    """
    渲染状态徽章HTML

    Args:
        status: 状态文本

    Returns:
        HTML字符串
    """
    status_colors = {
        '未使用': COLORS['success'],
        '已使用': COLORS['warning'],
        '已过期': COLORS['danger'],
        '已过期但被绑定': '#FF6F00',  # 深橙色 - 需要注意的状态
        '待处理': COLORS['info'],
        '已处理': COLORS['success'],
        '处理失败': COLORS['danger'],
        '已停机': '#9E9E9E',
    }

    color = status_colors.get(status, COLORS['info'])

    return f"""
        <span style="
            background-color: {color}15;
            color: {color};
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid {color}40;
        ">{status}</span>
    """


def render_dataframe_with_style(df: pd.DataFrame, status_column: Optional[str] = None, height: int = 400):
    """
    使用 AgGrid 渲染高性能数据表格（支持大数据量，带分页筛选排序）

    Args:
        df: DataFrame对象
        status_column: 状态列名，将为其添加颜色标记
        height: 表格高度（像素）
    """
    if df.empty:
        st.info("暂无数据")
        return

    # 复制一份数据，避免修改原始 DataFrame
    df = df.copy()

    # 配置 AgGrid
    gb = GridOptionsBuilder.from_dataframe(df)

    # 启用分页（每页50条）
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=50)

    # 启用筛选和排序
    gb.configure_default_column(
        filterable=True,
        sortable=True,
        resizable=True,
        editable=False,
        wrapText=False,
        autoHeight=False,
        enableCellTextSelection=True,  # 启用单元格文本选择
        ensureDomOrder=True
    )

    # 禁用行选择，但保留单元格选择功能
    gb.configure_selection(selection_mode='single', use_checkbox=False, suppressRowClickSelection=False)

    # 配置侧边栏（高级筛选）
    gb.configure_side_bar()

    # 配置网格选项 - 启用范围选择和复制功能
    gb.configure_grid_options(
        domLayout='normal',
        enableRangeSelection=True,  # 启用范围选择
        enableRangeHandle=True,     # 启用范围拖动
        enableCellTextSelection=True,  # 启用单元格文本选择
        suppressRowClickSelection=True,  # 禁止点击行时选择整行
        suppressCellSelection=False   # 允许单元格选择
    )

    gridOptions = gb.build()

    # 渲染 AgGrid（启用复制功能）
    AgGrid(
        df,
        gridOptions=gridOptions,
        height=height,
        width='100%',
        theme='streamlit',
        enable_enterprise_modules=False,
        update_mode=GridUpdateMode.NO_UPDATE,
        allow_unsafe_jscode=False,
        fit_columns_on_grid_load=True,
        reload_data=False
    )


def render_progress_card(title: str, current: int, total: int, icon: str = "📊"):
    """
    渲染进度卡片

    Args:
        title: 标题
        current: 当前值
        total: 总值
        icon: 图标
    """
    percentage = (current / total * 100) if total > 0 else 0

    # 根据百分比选择颜色
    if percentage < 30:
        color = COLORS['danger']
    elif percentage < 70:
        color = COLORS['warning']
    else:
        color = COLORS['success']

    st.markdown(f"""
        <div class="card">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 24px; margin-right: 10px;">{icon}</span>
                    <h3 style="margin: 0; font-size: 16px;">{title}</h3>
                </div>
                <div style="font-size: 24px; font-weight: 700; color: {color};">
                    {percentage:.1f}%
                </div>
            </div>
            <div style="background: #E0E0E0; height: 8px; border-radius: 4px; overflow: hidden;">
                <div style="background: linear-gradient(90deg, {COLORS['gradient_start']}, {COLORS['gradient_end']});
                            height: 100%; width: {percentage}%; transition: width 0.3s ease;">
                </div>
            </div>
            <div style="margin-top: 8px; color: #666; font-size: 14px;">
                {current} / {total}
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_action_card(title: str, description: str, button_text: str,
                       button_key: str, icon: str = "⚡", on_click=None) -> bool:
    """
    渲染操作卡片

    Args:
        title: 标题
        description: 描述
        button_text: 按钮文本
        button_key: 按钮的唯一key
        icon: 图标
        on_click: 点击回调函数

    Returns:
        按钮是否被点击
    """
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"**{icon} {title}**")
        st.markdown(f"<span style='color: #666; font-size: 14px;'>{description}</span>",
                   unsafe_allow_html=True)

    with col2:
        clicked = st.button(
            button_text,
            key=button_key,
            type="primary",
            width='stretch',
            on_click=on_click
        )

    return clicked


def render_stats_row(stats: List[Dict[str, Any]], icons: Optional[List[str]] = None):
    """
    渲染统计信息行

    Args:
        stats: 统计信息列表，每个字典包含 label, value, delta(可选)
        icons: 图标列表
    """
    if not icons:
        icons = ["📊"] * len(stats)

    cols = st.columns(len(stats))

    for col, stat, icon in zip(cols, stats, icons):
        with col:
            delta = stat.get('delta')
            delta_color = stat.get('delta_color', 'normal')

            st.metric(
                label=f"{icon} {stat['label']}",
                value=stat['value'],
                delta=delta,
                delta_color=delta_color
            )


def render_search_filters(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    渲染搜索和筛选器

    Args:
        config: 配置字典，包含各个筛选项的定义

    Returns:
        用户选择的筛选值字典
    """
    st.markdown("### 🔍 搜索与筛选")

    filters = {}
    cols = st.columns(len(config))

    for col, (key, filter_config) in zip(cols, config.items()):
        with col:
            filter_type = filter_config['type']

            if filter_type == 'text':
                filters[key] = st.text_input(
                    filter_config['label'],
                    placeholder=filter_config.get('placeholder', ''),
                    key=f"filter_{key}"
                )
            elif filter_type == 'select':
                filters[key] = st.selectbox(
                    filter_config['label'],
                    options=filter_config['options'],
                    key=f"filter_{key}"
                )
            elif filter_type == 'date':
                filters[key] = st.date_input(
                    filter_config['label'],
                    key=f"filter_{key}"
                )

    return filters


def render_file_upload_section(title: str, help_text: str,
                               file_types: List[str] = ['xlsx', 'xls'],
                               template_data: Optional[bytes] = None,
                               template_name: str = "template.xlsx") -> Tuple[Any, st.container]:
    """
    渲染文件上传区域

    Args:
        title: 标题
        help_text: 帮助文本
        file_types: 支持的文件类型
        template_data: 模板文件数据
        template_name: 模板文件名

    Returns:
        (上传的文件, 操作列容器)
    """
    st.markdown(f"### 📤 {title}")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            f"选择{title}文件",
            type=file_types,
            help=help_text
        )

    with col2:
        if template_data:
            st.download_button(
                label="📋 下载模板",
                data=template_data,
                file_name=template_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    return uploaded_file, col1


def render_section_divider(title: Optional[str] = None):
    """
    渲染章节分隔符

    Args:
        title: 可选的章节标题
    """
    if title:
        st.markdown(f"""
            <div style="margin: 30px 0;">
                <div style="height: 2px; background: linear-gradient(90deg, {COLORS['primary']}, transparent);"></div>
                <h3 style="margin-top: 15px; color: {COLORS['primary']};">{title}</h3>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style="margin: 30px 0; height: 2px;
                        background: linear-gradient(90deg, {COLORS['primary']}, transparent);">
            </div>
        """, unsafe_allow_html=True)


def show_success_message(message: str, icon: str = "✅"):
    """显示成功消息"""
    st.success(f"{icon} {message}")


def show_error_message(message: str, icon: str = "❌"):
    """显示错误消息"""
    st.error(f"{icon} {message}")


def show_warning_message(message: str, icon: str = "⚠️"):
    """显示警告消息"""
    st.warning(f"{icon} {message}")


def show_info_message(message: str, icon: str = "ℹ️"):
    """显示信息消息"""
    st.info(f"{icon} {message}")


def render_empty_state(message: str, suggestions: Optional[List[str]] = None, icon: str = "📭"):
    """
    渲染空状态

    Args:
        message: 主要消息
        suggestions: 建议列表
        icon: 图标
    """
    st.markdown(f"""
        <div style="text-align: center; padding: 60px 20px; color: #999;">
            <div style="font-size: 64px; margin-bottom: 20px;">{icon}</div>
            <h3 style="color: #666;">{message}</h3>
        </div>
    """, unsafe_allow_html=True)

    if suggestions:
        st.markdown("**💡 建议：**")
        for suggestion in suggestions:
            st.markdown(f"- {suggestion}")
