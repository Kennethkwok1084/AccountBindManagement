# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Campus Network Account Management System v2.0** (校园网上网账号管理系统) designed to manage internet service provider (ISP) accounts for a campus network. The system handles the complete lifecycle of network accounts from inventory to binding to expiration with independent user list data calibration.

## Architecture

The system is built around a core data model with four main tables using a multi-page Streamlit application:

### Core Data Tables
1. **`isp_accounts` (上网账号表)** - ISP account resource pool (no initial binding info)
   - `账号` (account): Primary key, unique ISP account number
   - `账号类型` (account_type): Type like "202409", "0元账号"
   - `状态` (status): "未使用", "已使用", "已过期"
   - `生命周期开始日期/结束日期`: Lifecycle dates calculated from account type
   - `绑定的学号/套餐到期日`: Binding information (synced from user_list)

2. **`user_list` (用户列表表)** - Source of truth for actual binding relationships
   - `用户账号` (student ID): Student account number
   - `绑定套餐` (subscription): Subscription plan
   - `用户姓名` (name): User name
   - `用户类别` (category): User category (本科生/研究生/教职工)
   - `移动账号` (ISP account): Bound ISP account
   - `到期日期` (expiry): Subscription expiry date
   - Monthly import for data calibration

3. **`payment_logs` (缴费记录表)** - Payment processing queue
   - Tracks incremental payment imports with processing status
   - States: "待处理", "已处理", "处理失败"

4. **`system_settings` (系统设置表)** - Global configuration
   - Stores settings like last import time, zero-cost account policies

## Technology Stack

- **Language**: Python 3.8+
- **Data Processing**: Pandas + openpyxl (for Excel file handling)
- **Database**: SQLite (lightweight, single-file database)
- **UI Framework**: Streamlit multi-page application
- **Backend**: SQLite with Python business logic

## Core Workflows

### 1. ISP Account Pool Import
- Upload Excel files containing ISP account pools (resource pool only)
- Fields: 移动账户, 账号类型, 使用状态
- Calculates lifecycle dates based on account types
- No binding information initially - pure resource pool

### 2. User List Import & Data Calibration (Monthly)
- Independent module for actual binding relationships
- Excel fields: 用户账号, 绑定套餐, 用户姓名, 用户类别, 移动账号, 到期日期
- Monthly import for data calibration
- Synchronizes binding state from user_list to isp_accounts
- Source of truth for actual bindings

### 3. Payment Processing & Export Generation
Two-step process:
- **Step A**: Import payment records (用户账号, 收费时间, 收费金额)
- **Step B**: Auto-bind available accounts and generate Excel for batch modification

### 4. System Maintenance
- **Auto-release**: Free accounts when subscription expires but account lifecycle continues
- **Auto-expire**: Mark accounts as expired when lifecycle ends
- **Configuration management**: Zero-cost account policies
- **Data integrity**: Regular calibration from user list

## User Interface Structure (Multi-page Streamlit)

The system uses Streamlit's multi-page architecture with 5 separate pages:

1. **📊 首页** (app.py): Dashboard with metrics and system overview
2. **🗂️ 账号管理** (pages/1_🗂️_账号管理.py): ISP account pool management
3. **👥 用户列表** (pages/2_👥_用户列表.py): User list management and data calibration
4. **🚀 绑定导出** (pages/3_🚀_绑定导出.py): Payment processing and export generation
5. **⚙️ 系统设置** (pages/4_⚙️_系统设置.py): Configuration and maintenance

URLs: http://localhost:8506/[page_name]

## Development Commands

Start the multi-page application:
```bash
streamlit run app.py --server.port 8506
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Always respond in Chinese/中文, 遵循"如无必要不增加实体原则"。

## Key Business Logic

- **Separation of Concerns**: ISP account pool (pure resources) vs user list (actual bindings)
- **Data Calibration**: Monthly user list import as source of truth for bindings
- **Account Lifecycle**: Accounts have definite start/end dates based on type
- **Incremental Processing**: Only process new payments since last import
- **Resource Allocation**: Bind available accounts to paying students
- **Data Integrity**: Regular calibration from user list to account pool
- **Automated Maintenance**: Daily cleanup of expired bindings and accounts

## File Structure

```
Account_manager/
├── app.py                     # Main dashboard (首页)
├── start.bat                  # Windows startup script
├── requirements.txt           # Python dependencies
├── pages/                     # Multi-page structure
│   ├── 1_🗂️_账号管理.py      # ISP account pool management
│   ├── 2_👥_用户列表.py       # User list & data calibration
│   ├── 3_🚀_绑定导出.py       # Payment processing & export
│   └── 4_⚙️_系统设置.py       # System settings
├── database/                  # Database layer
│   ├── models.py             # Data models & schema
│   └── operations.py         # Database operations
├── utils/                     # Business logic
│   ├── business_logic.py     # Core business processes
│   ├── excel_handler.py      # Excel processing
│   └── date_utils.py         # Date calculations
├── data/                      # Data directory
│   └── account_manager.db    # SQLite database
└── templates/                 # Excel templates
```

## Key Design Principles

1. **如无必要不增加实体**: Don't add entities unless necessary
2. **Separation of Resource Pool and Bindings**: ISP accounts are pure resources, user list contains actual binding relationships
3. **Monthly Data Calibration**: User list serves as authoritative source for binding synchronization
4. **Multi-page Architecture**: Each major function has its own page with dedicated URL