from __future__ import annotations

import json
import sqlite3


MIGRATION_ID = "20260424_001_initial_schema"


def upgrade(connection: sqlite3.Connection) -> None:
    _create_tables(connection)
    _seed_roles(connection)
    _seed_sources(connection)


def _create_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, role_id)
        );

        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            home_url TEXT NOT NULL,
            priority TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            adapter_mode TEXT NOT NULL,
            login_mode TEXT NOT NULL,
            login_status TEXT NOT NULL DEFAULT 'not_required',
            health_status TEXT NOT NULL DEFAULT 'unknown',
            active_rule_version_id INTEGER,
            maintenance_owner TEXT,
            last_success_at TEXT,
            last_failure_at TEXT,
            last_failure_reason TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (name, home_url)
        );

        CREATE TABLE IF NOT EXISTS source_basic_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL UNIQUE REFERENCES sources(id) ON DELETE CASCADE,
            regions_json TEXT NOT NULL DEFAULT '[]',
            industry_keywords_json TEXT NOT NULL DEFAULT '[]',
            demand_keywords_json TEXT NOT NULL DEFAULT '[]',
            exclude_keywords_json TEXT NOT NULL DEFAULT '[]',
            frequency TEXT NOT NULL DEFAULT 'manual',
            digest_enabled INTEGER NOT NULL DEFAULT 0,
            digest_score_threshold INTEGER NOT NULL DEFAULT 70,
            updated_by TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS source_advanced_rule_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            version INTEGER NOT NULL,
            status TEXT NOT NULL,
            adapter_mode TEXT NOT NULL,
            entry_url TEXT NOT NULL,
            login_mode TEXT NOT NULL,
            selectors_json TEXT NOT NULL DEFAULT '{}',
            pagination_policy_json TEXT NOT NULL DEFAULT '{}',
            normalization_mapping_json TEXT NOT NULL DEFAULT '{}',
            attachment_policy_json TEXT NOT NULL DEFAULT '{}',
            risk_patterns_json TEXT NOT NULL DEFAULT '{}',
            rate_limit_policy_json TEXT NOT NULL DEFAULT '{}',
            retry_policy_json TEXT NOT NULL DEFAULT '{}',
            trial_run_snapshot_json TEXT,
            created_by TEXT NOT NULL,
            activated_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (source_id, version)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_source_one_active_rule
        ON source_advanced_rule_versions(source_id)
        WHERE status = 'active';

        CREATE TABLE IF NOT EXISTS source_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            credential_profile_id TEXT,
            owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            login_status TEXT NOT NULL DEFAULT 'pending_login',
            last_login_at TEXT,
            session_profile_path TEXT,
            masked_account_name TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS agent_hosts (
            host_id TEXT PRIMARY KEY,
            hostname TEXT NOT NULL,
            platform TEXT,
            app_version TEXT,
            last_seen_at TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_instances (
            agent_id TEXT PRIMARY KEY,
            host_id TEXT NOT NULL REFERENCES agent_hosts(host_id) ON DELETE CASCADE,
            status TEXT NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 1,
            active_sessions INTEGER NOT NULL DEFAULT 0,
            last_heartbeat_at TEXT
        );

        CREATE TABLE IF NOT EXISTS collection_runs (
            run_id TEXT PRIMARY KEY,
            source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            agent_id TEXT REFERENCES agent_instances(agent_id) ON DELETE SET NULL,
            rule_version INTEGER NOT NULL,
            status TEXT NOT NULL,
            scheduled_at TEXT,
            started_at TEXT,
            finished_at TEXT,
            page_count INTEGER NOT NULL DEFAULT 0,
            item_count INTEGER NOT NULL DEFAULT 0,
            failure_kind TEXT,
            diagnostic_snapshot_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS raw_evidence_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT REFERENCES collection_runs(run_id) ON DELETE SET NULL,
            source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            source_item_key TEXT,
            url TEXT,
            title TEXT NOT NULL,
            published_at TEXT,
            raw_text TEXT,
            raw_html_path TEXT,
            attachments_json TEXT NOT NULL DEFAULT '[]',
            content_fingerprint TEXT,
            collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_evidence_source_item_key
        ON raw_evidence_items(source_id, source_item_key)
        WHERE source_item_key IS NOT NULL;

        CREATE TABLE IF NOT EXISTS opportunity_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            evidence_id INTEGER NOT NULL REFERENCES raw_evidence_items(id) ON DELETE CASCADE,
            dedupe_key TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            organization_name TEXT,
            region TEXT,
            industry TEXT,
            project_stage TEXT,
            budget_amount REAL,
            score INTEGER NOT NULL DEFAULT 0,
            priority_label TEXT NOT NULL DEFAULT 'P3',
            review_status TEXT NOT NULL DEFAULT 'pending',
            follow_up_status TEXT NOT NULL DEFAULT 'none',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS candidate_analysis (
            candidate_id INTEGER PRIMARY KEY REFERENCES opportunity_candidates(id) ON DELETE CASCADE,
            extracted_facts_json TEXT NOT NULL DEFAULT '{}',
            inferred_analysis_json TEXT NOT NULL DEFAULT '{}',
            scoring_reasons_json TEXT NOT NULL DEFAULT '{}',
            outreach_json TEXT NOT NULL DEFAULT '{}',
            provider_metadata_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            region TEXT,
            industry TEXT,
            crm_external_id TEXT,
            source TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS customer_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            candidate_id INTEGER REFERENCES opportunity_candidates(id) ON DELETE SET NULL,
            activity_type TEXT NOT NULL,
            content TEXT,
            occurred_at TEXT NOT NULL,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS weekly_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            week_start TEXT NOT NULL,
            visit_target INTEGER NOT NULL DEFAULT 0,
            quote_target INTEGER NOT NULL DEFAULT 0,
            opportunity_target INTEGER NOT NULL DEFAULT 0,
            UNIQUE(owner_user_id, week_start)
        );

        CREATE TABLE IF NOT EXISTS notification_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            template TEXT NOT NULL,
            candidate_ids_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL,
            sent_at TEXT,
            failure_reason TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            before_json TEXT,
            after_json TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    )


def _seed_roles(connection: sqlite3.Connection) -> None:
    roles = [
        ("operator", "操作员"),
        ("business_manager", "业务经理"),
        ("manager", "管理者"),
        ("administrator", "管理员"),
    ]
    connection.executemany(
        "INSERT OR IGNORE INTO roles (name, display_name) VALUES (?, ?)",
        roles,
    )


def _seed_sources(connection: sqlite3.Connection) -> None:
    sources = [
        (
            "中国政府采购网",
            "政府采购与招标",
            "https://www.ccgp.gov.cn",
            "P0",
            "public_search_list_detail",
            "not_required",
            "daily",
            70,
        ),
        (
            "全国公共资源交易平台",
            "政府采购与招标",
            "https://www.ggzy.gov.cn",
            "P0",
            "public_search_list_detail",
            "not_required",
            "daily",
            70,
        ),
        (
            "中国招标投标公共服务平台",
            "政府采购与招标",
            "https://www.cebpubservice.com",
            "P0",
            "public_search_list_detail",
            "not_required",
            "daily",
            70,
        ),
        (
            "江苏省政府采购网",
            "政府采购与招标",
            "https://www.ccgp-jiangsu.gov.cn",
            "P0",
            "public_search_list_detail",
            "not_required",
            "daily",
            70,
        ),
        (
            "江苏省公共资源交易平台",
            "政府采购与招标",
            "https://jsggzy.jszwfw.gov.cn",
            "P0",
            "public_search_list_detail",
            "not_required",
            "daily",
            70,
        ),
        (
            "苏州市公共资源交易平台",
            "政府采购与招标",
            "https://www.szzyjy.com.cn",
            "P0",
            "public_search_list_detail",
            "not_required",
            "daily",
            70,
        ),
        (
            "昆山市政府网",
            "政府部门",
            "https://www.ks.gov.cn",
            "P0",
            "public_channel_news",
            "not_required",
            "daily",
            70,
        ),
        (
            "建设网",
            "账号型行业平台",
            "https://www.jszhaobiao.com",
            "P1",
            "login_search_list_detail",
            "login_required",
            "weekly",
            75,
        ),
        (
            "微信公众号手动导入",
            "微信公众号",
            "manual://wechat",
            "P1",
            "manual_import",
            "not_required",
            "manual",
            70,
        ),
    ]
    for source in sources:
        _seed_source(connection, *source)


def _seed_source(
    connection: sqlite3.Connection,
    name: str,
    category: str,
    home_url: str,
    priority: str,
    adapter_mode: str,
    login_mode: str,
    frequency: str,
    digest_score_threshold: int,
) -> None:
    login_status = "not_required" if login_mode == "not_required" else "pending_login"
    connection.execute(
        """
        INSERT OR IGNORE INTO sources (
            name, category, home_url, priority, adapter_mode, login_mode, login_status, health_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'unknown')
        """,
        (name, category, home_url, priority, adapter_mode, login_mode, login_status),
    )
    source_id = connection.execute(
        "SELECT id FROM sources WHERE name = ? AND home_url = ?",
        (name, home_url),
    ).fetchone()[0]

    connection.execute(
        """
        INSERT OR IGNORE INTO source_basic_rules (
            source_id, regions_json, industry_keywords_json, demand_keywords_json,
            exclude_keywords_json, frequency, digest_enabled, digest_score_threshold, updated_by
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, 'system')
        """,
        (
            source_id,
            _json(["昆山", "太仓", "常熟", "张家港", "苏州"]),
            _json(["四新", "政府", "医疗", "教育", "金融", "制造"]),
            _json(["智能化", "弱电", "数字化", "AI", "云平台", "数据中台"]),
            _json([]),
            frequency,
            digest_score_threshold,
        ),
    )

    connection.execute(
        """
        INSERT OR IGNORE INTO source_advanced_rule_versions (
            source_id, version, status, adapter_mode, entry_url, login_mode,
            selectors_json, pagination_policy_json, normalization_mapping_json,
            attachment_policy_json, risk_patterns_json, rate_limit_policy_json,
            retry_policy_json, created_by, activated_at
        )
        VALUES (?, 1, 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'system', CURRENT_TIMESTAMP)
        """,
        (
            source_id,
            adapter_mode,
            home_url,
            login_mode,
            _json(_default_selectors(adapter_mode)),
            _json({"max_pages": 3, "max_items": 50}),
            _json({"title": "title", "url": "url", "published_at": "published_at"}),
            _json({"enabled": adapter_mode == "attachment_document"}),
            _json({"captcha": ["验证码", "安全验证"], "login": ["登录", "请登录"]}),
            _json({"min_interval_seconds": 3}),
            _json({"max_retries": 2}),
        ),
    )
    rule_id = connection.execute(
        """
        SELECT id FROM source_advanced_rule_versions
        WHERE source_id = ? AND version = 1
        """,
        (source_id,),
    ).fetchone()[0]
    connection.execute(
        "UPDATE sources SET active_rule_version_id = ? WHERE id = ?",
        (rule_id, source_id),
    )


def _default_selectors(adapter_mode: str) -> dict[str, str]:
    if adapter_mode in {"public_search_list_detail", "login_search_list_detail", "public_channel_news"}:
        return {
            "list_selector": ".result",
            "detail_link_selector": "a",
            "content_selector": ".content",
        }
    return {}


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
