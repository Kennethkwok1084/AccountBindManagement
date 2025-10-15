import io
from datetime import date

import pandas as pd
import pytest

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database.models as models  # noqa: E402
import database.operations as operations  # noqa: E402
from database.models import DatabaseManager  # noqa: E402
from database.operations import AccountTypeRuleOperations, ISPAccountOperations  # noqa: E402
from utils.business_logic import AccountManager


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Create an isolated SQLite database for each test."""
    db_path = tmp_path / "account_manager.db"
    manager = DatabaseManager(str(db_path))

    # Patch the shared db_manager references so all layers use the temp database.
    monkeypatch.setattr(models, "db_manager", manager, raising=False)
    monkeypatch.setattr(operations, "db_manager", manager, raising=False)

    return manager


def test_release_account_updates_account_and_user_list(temp_db):
    ISPAccountOperations.create_account(
        "ACC-REL",
        "202409",
        "已使用",
        生命周期开始日期=date(2024, 9, 1),
        生命周期结束日期=date(2025, 9, 1),
    )
    ISPAccountOperations.update_account(
        "ACC-REL",
        绑定的学号="STU-REL",
        绑定的套餐到期日="2025-05-01",
    )

    with temp_db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_list (用户账号, 绑定套餐, 用户姓名, 用户类别, 移动账号, 到期日期, 导入时间, 更新时间)
            VALUES ('STU-REL', '测试套餐', '学生甲', '本科生', 'ACC-REL', '2025-05-01', datetime('now'), datetime('now'))
            """
        )
        conn.commit()

    assert ISPAccountOperations.release_account("ACC-REL")

    account = ISPAccountOperations.get_account("ACC-REL")
    assert account["状态"] == "未使用"
    assert account["绑定的学号"] is None
    assert account["绑定的套餐到期日"] is None

    with temp_db.get_connection() as conn:
        row = conn.execute(
            "SELECT 移动账号 FROM user_list WHERE 用户账号 = 'STU-REL'"
        ).fetchone()

    assert row is not None
    assert row["移动账号"] is None


def test_recalculate_lifecycle_updates_status(temp_db):
    # Initial data: one unbound account and two bound accounts with different套餐到期日.
    past_start = date(2023, 1, 1)
    past_end = date(2023, 7, 1)

    ISPAccountOperations.create_account("ACC-A", "RULETYPE", "未使用", 生命周期开始日期=past_start, 生命周期结束日期=past_end)
    ISPAccountOperations.create_account("ACC-B", "RULETYPE", "已使用", 生命周期开始日期=past_start, 生命周期结束日期=past_end)
    ISPAccountOperations.create_account("ACC-C", "RULETYPE", "已使用", 生命周期开始日期=past_start, 生命周期结束日期=past_end)

    ISPAccountOperations.update_account(
        "ACC-B",
        绑定的学号="STU-B",
        绑定的套餐到期日="2030-01-01",
    )
    ISPAccountOperations.update_account(
        "ACC-C",
        绑定的学号="STU-C",
        绑定的套餐到期日="2020-01-01",
    )

    with temp_db.get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO user_list (用户账号, 绑定套餐, 用户姓名, 用户类别, 移动账号, 到期日期, 导入时间, 更新时间)
            VALUES (?, '套餐', '测试', '本科生', ?, ?, datetime('now'), datetime('now'))
            """,
            [
                ("STU-B", "ACC-B", "2030-01-01"),
                ("STU-C", "ACC-C", "2020-01-01"),
            ],
        )
        conn.commit()

    # Rule drives lifecycle into the past.
    AccountTypeRuleOperations.upsert_rule(
        "RULETYPE",
        允许绑定=True,
        生命周期月份=1,
        自定义开始日期=None,
        自定义结束日期=None,
    )

    result = AccountManager.recalculate_lifecycle_for_type("RULETYPE")
    assert result["success"]
    assert result["updated_count"] == 3

    acc_a = ISPAccountOperations.get_account("ACC-A")
    acc_b = ISPAccountOperations.get_account("ACC-B")
    acc_c = ISPAccountOperations.get_account("ACC-C")

    assert acc_a["状态"] == "已过期"
    assert acc_b["状态"] == "已过期但被绑定"
    assert acc_c["状态"] == "已过期"

    # Extend lifecycle to future; bound accounts should return to 已使用, unbound to 未使用.
    future_start = date.today()
    future_end = date(future_start.year + 1, future_start.month, future_start.day)
    AccountTypeRuleOperations.upsert_rule(
        "RULETYPE",
        允许绑定=False,
        生命周期月份=None,
        自定义开始日期=future_start,
        自定义结束日期=future_end,
    )

    result2 = AccountManager.recalculate_lifecycle_for_type("RULETYPE")
    assert result2["success"]
    assert result2["updated_count"] == 3

    acc_a = ISPAccountOperations.get_account("ACC-A")
    acc_b = ISPAccountOperations.get_account("ACC-B")
    acc_c = ISPAccountOperations.get_account("ACC-C")

    assert acc_a["状态"] == "未使用"
    assert acc_b["状态"] == "已使用"
    assert acc_c["状态"] == "已使用"
    assert acc_a["生命周期开始日期"] == future_start.isoformat()
    assert acc_a["生命周期结束日期"] == future_end.isoformat()


def test_binding_import_releases_expired_package(temp_db):
    ISPAccountOperations.create_account(
        "ACC-BIND",
        "202409",
        "已使用",
        生命周期开始日期=date(2024, 9, 1),
        生命周期结束日期=date(2025, 9, 1),
    )
    ISPAccountOperations.update_account(
        "ACC-BIND",
        绑定的学号="STU-BIND",
        绑定的套餐到期日="2025-06-30",
    )

    with temp_db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_list (用户账号, 绑定套餐, 用户姓名, 用户类别, 移动账号, 到期日期, 导入时间, 更新时间)
            VALUES ('STU-BIND', '本科2022', '学生乙', '本科生', 'ACC-BIND', '2025-06-30', datetime('now'), datetime('now'))
            """
        )
        conn.commit()

    df = pd.DataFrame(
        [
            {
                "用户账号": "STU-BIND",
                "移动账号": "ACC-BIND",
                "到期日期": "2025-06-30",
                "绑定资费组": "本科2022",
            }
        ]
    )

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    result = AccountManager.sync_binding_details_from_excel(buffer)

    assert result["success"]
    assert result["released_count"] == 1
    assert result["updated_count"] == 0

    account = ISPAccountOperations.get_account("ACC-BIND")
    assert account["状态"] == "未使用"
    assert account["绑定的学号"] is None

    with temp_db.get_connection() as conn:
        row = conn.execute(
            "SELECT 移动账号 FROM user_list WHERE 用户账号 = 'STU-BIND'"
        ).fetchone()

    assert row is not None
    assert row["移动账号"] is None
