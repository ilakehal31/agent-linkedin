"""Mémoire persistante SQLite — posts, feedback, cache recherche."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "history.sqlite"

_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_tables(_conn)
    return _conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            context TEXT NOT NULL,
            topic TEXT NOT NULL,
            format TEXT NOT NULL,
            pillar TEXT,
            funnel_stage TEXT,
            hook TEXT NOT NULL,
            body TEXT NOT NULL,
            cta TEXT,
            hashtags TEXT,
            score_total REAL,
            score_details TEXT,
            char_count INTEGER,
            status TEXT DEFAULT 'draft',
            user_score INTEGER,
            user_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS research_cache (
            id INTEGER PRIMARY KEY,
            context TEXT NOT NULL,
            query TEXT NOT NULL,
            results TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS prompt_versions (
            id INTEGER PRIMARY KEY,
            prompt_file TEXT NOT NULL,
            hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()


def save_post(
    context: str,
    topic: str,
    format_name: str,
    pillar: str | None,
    funnel_stage: str | None,
    hook: str,
    body: str,
    cta: str | None,
    hashtags: list[str] | None,
    score_total: float | None,
    score_details: dict | None,
    char_count: int,
    status: str = "draft",
) -> int:
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO posts
        (context, topic, format, pillar, funnel_stage, hook, body, cta, hashtags,
         score_total, score_details, char_count, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            context, topic, format_name, pillar, funnel_stage, hook, body, cta,
            json.dumps(hashtags) if hashtags else None,
            score_total,
            json.dumps(score_details) if score_details else None,
            char_count, status,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_recent_posts(context: str, limit: int = 10) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM posts WHERE context = ? ORDER BY created_at DESC LIMIT ?",
        (context, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_best_posts(context: str, limit: int = 5) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM posts WHERE context = ? AND user_score IS NOT NULL
        ORDER BY user_score DESC LIMIT ?""",
        (context, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_post_by_id(post_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    return dict(row) if row else None


def update_feedback(post_id: int, user_score: int, user_note: str | None = None):
    conn = get_connection()
    conn.execute(
        "UPDATE posts SET user_score = ?, user_note = ? WHERE id = ?",
        (user_score, user_note, post_id),
    )
    conn.commit()


def update_status(post_id: int, status: str):
    conn = get_connection()
    conn.execute("UPDATE posts SET status = ? WHERE id = ?", (status, post_id))
    conn.commit()


def get_funnel_distribution(context: str, days: int = 7) -> dict[str, int]:
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT funnel_stage, COUNT(*) as count FROM posts
        WHERE context = ? AND created_at > ? AND funnel_stage IS NOT NULL
        GROUP BY funnel_stage""",
        (context, cutoff),
    ).fetchall()
    result = {"tofu": 0, "mofu": 0, "bofu": 0}
    for r in rows:
        if r["funnel_stage"] in result:
            result[r["funnel_stage"]] = r["count"]
    return result


def get_cached_research(context: str, query: str, ttl_hours: int = 24) -> str | None:
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=ttl_hours)).isoformat()
    row = conn.execute(
        """SELECT results FROM research_cache
        WHERE context = ? AND query = ? AND created_at > ?
        ORDER BY created_at DESC LIMIT 1""",
        (context, query, cutoff),
    ).fetchone()
    return row["results"] if row else None


def save_research_cache(context: str, query: str, results: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO research_cache (context, query, results) VALUES (?, ?, ?)",
        (context, query, results),
    )
    conn.commit()


def get_history(context: str, last: int = 20) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, topic, format, pillar, funnel_stage, hook, score_total, user_score, status, created_at FROM posts WHERE context = ? ORDER BY created_at DESC LIMIT ?",
        (context, last),
    ).fetchall()
    return [dict(r) for r in rows]
