from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.control_plane.services.auth_service import AuthService
from opportunity_crawler.control_plane.services.customer_service import CustomerService
from opportunity_crawler.shared.db.base import apply_migrations, connect_sqlite


def test_customer_history_aggregates_candidates_and_activities(tmp_path: Path) -> None:
    database_path = tmp_path / "opportunity.db"
    connection = connect_sqlite(database_path)
    apply_migrations(connection)
    _seed_user(connection)
    source_id = connection.execute("SELECT id FROM sources LIMIT 1").fetchone()[0]
    connection.execute(
        """
        INSERT INTO raw_evidence_items (source_id, source_item_key, title, raw_text)
        VALUES (?, 'item-1', '昆山项目', '正文')
        """,
        (source_id,),
    )
    evidence_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
    connection.execute(
        """
        INSERT INTO opportunity_candidates (
            source_id, evidence_id, dedupe_key, title, organization_name, score, review_status, follow_up_status
        )
        VALUES (?, ?, 'key-1', '昆山项目', '昆山某单位', 91, 'accepted', 'visited')
        """,
        (source_id, evidence_id),
    )
    candidate_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
    customer_id = connection.execute(
        "INSERT INTO customers (name, region) VALUES ('昆山某单位', '昆山') RETURNING id"
    ).fetchone()[0]
    user_id = connection.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]
    connection.execute(
        """
        INSERT INTO customer_activities (customer_id, candidate_id, activity_type, content, occurred_at, created_by)
        VALUES (?, ?, 'visited', '已拜访', '2026-04-24', ?)
        """,
        (customer_id, candidate_id, user_id),
    )
    connection.commit()
    connection.close()

    history = CustomerService(database_path).history_for_customer("昆山某单位")

    assert history["customer"]["name"] == "昆山某单位"
    assert history["opportunity_count"] == 1
    assert history["activities"][0]["activity_type"] == "visited"


def _seed_user(connection) -> None:
    password_hash = AuthService.hash_password("admin-pass")
    connection.execute(
        "INSERT INTO users (username, password_hash, display_name) VALUES ('admin', ?, 'admin')",
        (password_hash,),
    )
    role_id = connection.execute("SELECT id FROM roles WHERE name = 'administrator'").fetchone()[0]
    user_id = connection.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]
    connection.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, role_id))
    connection.commit()

