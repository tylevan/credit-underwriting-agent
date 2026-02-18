"""
Assessment Repository — Data Access Layer for assessment history.

Dual-mode:
  - Production: PostgreSQL via asyncpg (Supabase)
  - Local dev:  SQLite via aiosqlite (fallback)

Chọn mode tự động dựa trên biến DATABASE_URL.
"""

import json
import logging
import os
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

# ── Detect mode ──
_USE_POSTGRES = bool(os.getenv("DATABASE_URL"))
_DB_PATH = "data/assessments.db"  # SQLite fallback
_PG_POOL = None  # asyncpg connection pool


async def _get_pg_pool():
    """Lazy-init PostgreSQL connection pool."""
    global _PG_POOL
    if _PG_POOL is None:
        import asyncpg
        _PG_POOL = await asyncpg.create_pool(
            os.getenv("DATABASE_URL"),
            min_size=1,
            max_size=5,
            # Supabase dùng connection pooler (Supavisor/pgBouncer)
            # cần tắt statement cache để tránh lỗi prepared statement
            statement_cache_size=0,
            server_settings={"plan_cache_mode": "force_custom_plan"},
        )
    return _PG_POOL


# ════════════════════════════════════════════
# INIT
# ════════════════════════════════════════════

async def init_db(db_path: str = None):
    """Tạo bảng assessments nếu chưa tồn tại."""
    global _DB_PATH, _USE_POSTGRES
    _USE_POSTGRES = bool(os.getenv("DATABASE_URL"))

    if _USE_POSTGRES:
        try:
            pool = await _get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS assessments (
                        id SERIAL PRIMARY KEY,
                        assessment_id TEXT NOT NULL,
                        thread_id TEXT NOT NULL,
                        customer_id TEXT NOT NULL,
                        customer_name TEXT DEFAULT '',
                        loan_amount DOUBLE PRECISION NOT NULL,
                        term_months INTEGER NOT NULL,
                        decision TEXT,
                        cic_score INTEGER,
                        dti DOUBLE PRECISION,
                        approved_limit DOUBLE PRECISION,
                        reasoning_trail TEXT DEFAULT '[]',
                        report TEXT DEFAULT '',
                        needs_human_review INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                await conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_assessments_assessment_id
                    ON assessments(assessment_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_assessments_created_at
                    ON assessments(created_at)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_assessments_decision
                    ON assessments(decision)
                """)
            logger.info("PostgreSQL (Supabase) connected successfully.")
        except Exception as e:
            logger.warning(f"PostgreSQL init failed, will retry on first request: {e}")
    else:
        import aiosqlite
        if db_path:
            _DB_PATH = db_path
        async with aiosqlite.connect(_DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assessment_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    customer_name TEXT DEFAULT '',
                    loan_amount REAL NOT NULL,
                    term_months INTEGER NOT NULL,
                    decision TEXT,
                    cic_score INTEGER,
                    dti REAL,
                    approved_limit REAL,
                    reasoning_trail TEXT DEFAULT '[]',
                    report TEXT DEFAULT '',
                    needs_human_review INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_assessments_assessment_id
                ON assessments(assessment_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_assessments_created_at
                ON assessments(created_at)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_assessments_decision
                ON assessments(decision)
            """)
            await db.commit()


# ════════════════════════════════════════════
# SAVE
# ════════════════════════════════════════════

async def save_assessment(data: dict) -> int:
    """
    Lưu kết quả thẩm định vào DB.

    Returns:
        ID của record mới tạo
    """
    reasoning_json = json.dumps(data.get("reasoning_trail", []), ensure_ascii=False)
    created_at_raw = data.get("created_at", datetime.now().isoformat())

    if _USE_POSTGRES:
        # asyncpg cần datetime object, không nhận string
        if isinstance(created_at_raw, str):
            try:
                created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                created_at = datetime.now()
        elif isinstance(created_at_raw, datetime):
            created_at = created_at_raw
        else:
            created_at = datetime.now()

        try:
            pool = await _get_pg_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO assessments
                        (assessment_id, thread_id, customer_id, customer_name, loan_amount, term_months,
                         decision, cic_score, dti, approved_limit,
                         reasoning_trail, report, needs_human_review, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    RETURNING id, assessment_id
                    """,
                    str(data.get("assessment_id", "")),
                    str(data.get("thread_id", "")),
                    str(data.get("customer_id", "")),
                    str(data.get("customer_name", "")),
                    float(data.get("loan_amount", 0)),
                    int(data.get("term_months", 0)),
                    data.get("decision"),
                    int(data.get("cic_score", 0)) if data.get("cic_score") is not None else None,
                    float(data.get("dti", 0)) if data.get("dti") is not None else None,
                    float(data.get("approved_limit", 0)) if data.get("approved_limit") is not None else None,
                    reasoning_json,
                    str(data.get("report", "")),
                    1 if data.get("needs_human_review") else 0,
                    created_at,
                )
                logger.info(f"Assessment saved to PostgreSQL, id={row['id']}, assessment_id={row['assessment_id']}")
                return row["id"]
        except Exception as e:
            logger.error(f"Failed to save assessment to PostgreSQL: {e}")
            raise
    else:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            cursor = await db.execute(
                """
                INSERT INTO assessments
                    (assessment_id, thread_id, customer_id, customer_name, loan_amount, term_months,
                     decision, cic_score, dti, approved_limit,
                     reasoning_trail, report, needs_human_review, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.get("assessment_id", ""),
                    data.get("thread_id", ""),
                    data.get("customer_id", ""),
                    data.get("customer_name", ""),
                    data.get("loan_amount", 0),
                    data.get("term_months", 0),
                    data.get("decision"),
                    data.get("cic_score"),
                    data.get("dti"),
                    data.get("approved_limit"),
                    reasoning_json,
                    data.get("report", ""),
                    1 if data.get("needs_human_review") else 0,
                    created_at,
                ),
            )
            await db.commit()
            return cursor.lastrowid


# ════════════════════════════════════════════
# STATS
# ════════════════════════════════════════════

async def get_stats(date_from: date = None, date_to: date = None) -> dict:
    """
    Lấy thống kê thẩm định theo khoảng thời gian.

    Returns:
        {total, approved, rejected, review,
         approved_pct, rejected_pct, review_pct}
    """
    if _USE_POSTGRES:
        return await _get_stats_pg(date_from, date_to)
    else:
        return await _get_stats_sqlite(date_from, date_to)


async def _get_stats_pg(date_from, date_to):
    try:
        pool = await _get_pg_pool()
        async with pool.acquire() as conn:
            where = "1=1"
            params = []
            idx = 1

            if date_from:
                where += f" AND created_at::date >= ${idx}"
                params.append(date_from)  # pass date object directly
                idx += 1
            if date_to:
                where += f" AND created_at::date <= ${idx}"
                params.append(date_to)  # pass date object directly
                idx += 1

            row = await conn.fetchrow(
                f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN decision = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN decision = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN decision = 'REVIEW' THEN 1 ELSE 0 END) as review
                FROM assessments
                WHERE {where}
                """,
                *params,
            )

            total = row["total"] or 0
            approved = row["approved"] or 0
            rejected = row["rejected"] or 0
            review = row["review"] or 0

            return {
                "total": total,
                "approved": approved,
                "rejected": rejected,
                "review": review,
                "approved_pct": round(approved / total * 100, 1) if total > 0 else 0,
                "rejected_pct": round(rejected / total * 100, 1) if total > 0 else 0,
                "review_pct": round(review / total * 100, 1) if total > 0 else 0,
            }
    except Exception as e:
        logger.error(f"_get_stats_pg error: {e}")
        raise


async def _get_stats_sqlite(date_from, date_to):
    import aiosqlite
    where = "1=1"
    params = []

    if date_from:
        where += " AND DATE(created_at) >= ?"
        params.append(date_from.isoformat())
    if date_to:
        where += " AND DATE(created_at) <= ?"
        params.append(date_to.isoformat())

    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN decision = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN decision = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN decision = 'REVIEW' THEN 1 ELSE 0 END) as review
            FROM assessments
            WHERE {where}
            """,
            params,
        )
        row = await cursor.fetchone()

        total = row["total"] or 0
        approved = row["approved"] or 0
        rejected = row["rejected"] or 0
        review = row["review"] or 0

        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "review": review,
            "approved_pct": round(approved / total * 100, 1) if total > 0 else 0,
            "rejected_pct": round(rejected / total * 100, 1) if total > 0 else 0,
            "review_pct": round(review / total * 100, 1) if total > 0 else 0,
        }


# ════════════════════════════════════════════
# LIST
# ════════════════════════════════════════════

async def list_assessments(
    date_from: date = None,
    date_to: date = None,
    decision: str = None,
    search: str = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    Lấy danh sách assessments với filter + phân trang.

    Returns:
        {items: [...], total: int, page: int, page_size: int}
    """
    if _USE_POSTGRES:
        return await _list_pg(date_from, date_to, decision, search, page, page_size)
    else:
        return await _list_sqlite(date_from, date_to, decision, search, page, page_size)


async def _list_pg(date_from, date_to, decision, search, page, page_size):
    try:
        pool = await _get_pg_pool()
        async with pool.acquire() as conn:
            where = "1=1"
            params = []
            idx = 1

            if date_from:
                where += f" AND created_at::date >= ${idx}"
                params.append(date_from)  # pass date object directly
                idx += 1
            if date_to:
                where += f" AND created_at::date <= ${idx}"
                params.append(date_to)  # pass date object directly
                idx += 1
            if decision:
                where += f" AND decision = ${idx}"
                params.append(decision)
                idx += 1
            if search:
                where += f" AND (customer_name ILIKE ${idx} OR customer_id ILIKE ${idx+1})"
                params.extend([f"%{search}%", f"%{search}%"])
                idx += 2

            # Count
            row = await conn.fetchrow(
                f"SELECT COUNT(*) as cnt FROM assessments WHERE {where}", *params
            )
            total = row["cnt"]

            # Items
            offset = (page - 1) * page_size
            rows = await conn.fetch(
                f"""
                SELECT id, assessment_id, thread_id, customer_id, customer_name, loan_amount,
                       term_months, decision, cic_score, dti, approved_limit,
                       reasoning_trail, needs_human_review, created_at
                FROM assessments
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT ${idx} OFFSET ${idx+1}
                """,
                *params, page_size, offset,
            )

            items = []
            for r in rows:
                items.append({
                    "id": r["id"],
                    "assessment_id": r["assessment_id"],
                    "thread_id": r["thread_id"],
                    "customer_id": r["customer_id"],
                    "customer_name": r["customer_name"],
                    "loan_amount": r["loan_amount"],
                    "term_months": r["term_months"],
                    "decision": r["decision"],
                    "cic_score": r["cic_score"],
                    "dti": r["dti"],
                    "approved_limit": r["approved_limit"],
                    "reasoning_trail": json.loads(r["reasoning_trail"] or "[]"),
                    "needs_human_review": bool(r["needs_human_review"]),
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                })

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
    except Exception as e:
        logger.error(f"_list_pg error: {e}")
        raise


async def _list_sqlite(date_from, date_to, decision, search, page, page_size):
    import aiosqlite
    where = "1=1"
    params = []

    if date_from:
        where += " AND DATE(created_at) >= ?"
        params.append(date_from.isoformat())
    if date_to:
        where += " AND DATE(created_at) <= ?"
        params.append(date_to.isoformat())
    if decision:
        where += " AND decision = ?"
        params.append(decision)
    if search:
        where += " AND (customer_name LIKE ? OR customer_id LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            f"SELECT COUNT(*) as cnt FROM assessments WHERE {where}", params
        )
        total = (await cursor.fetchone())["cnt"]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"""
            SELECT id, assessment_id, thread_id, customer_id, customer_name, loan_amount,
                   term_months, decision, cic_score, dti, approved_limit,
                   reasoning_trail, needs_human_review, created_at
            FROM assessments
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset],
        )
        rows = await cursor.fetchall()

        items = []
        for r in rows:
            items.append({
                "id": r["id"],
                "assessment_id": r["assessment_id"],
                "thread_id": r["thread_id"],
                "customer_id": r["customer_id"],
                "customer_name": r["customer_name"],
                "loan_amount": r["loan_amount"],
                "term_months": r["term_months"],
                "decision": r["decision"],
                "cic_score": r["cic_score"],
                "dti": r["dti"],
                "approved_limit": r["approved_limit"],
                "reasoning_trail": json.loads(r["reasoning_trail"] or "[]"),
                "needs_human_review": bool(r["needs_human_review"]),
                "created_at": r["created_at"],
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }


# ════════════════════════════════════════════
# GET BY ID
# ════════════════════════════════════════════

async def get_assessment_by_id(assessment_id: int) -> Optional[dict]:
    """Lấy 1 assessment theo ID (bao gồm trail + report)."""
    if _USE_POSTGRES:
        return await _get_by_id_pg(assessment_id)
    else:
        return await _get_by_id_sqlite(assessment_id)


async def _get_by_id_pg(assessment_id: int):
    pool = await _get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM assessments WHERE id = $1", assessment_id
        )
        if not row:
            return None

        return {
            "id": row["id"],
            "assessment_id": row["assessment_id"],
            "thread_id": row["thread_id"],
            "customer_id": row["customer_id"],
            "customer_name": row["customer_name"],
            "loan_amount": row["loan_amount"],
            "term_months": row["term_months"],
            "decision": row["decision"],
            "cic_score": row["cic_score"],
            "dti": row["dti"],
            "approved_limit": row["approved_limit"],
            "reasoning_trail": json.loads(row["reasoning_trail"] or "[]"),
            "report": row["report"],
            "needs_human_review": bool(row["needs_human_review"]),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }


async def _get_by_id_sqlite(assessment_id: int):
    import aiosqlite
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM assessments WHERE id = ?", (assessment_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return {
            "id": row["id"],
            "assessment_id": row["assessment_id"],
            "thread_id": row["thread_id"],
            "customer_id": row["customer_id"],
            "customer_name": row["customer_name"],
            "loan_amount": row["loan_amount"],
            "term_months": row["term_months"],
            "decision": row["decision"],
            "cic_score": row["cic_score"],
            "dti": row["dti"],
            "approved_limit": row["approved_limit"],
            "reasoning_trail": json.loads(row["reasoning_trail"] or "[]"),
            "report": row["report"],
            "needs_human_review": bool(row["needs_human_review"]),
            "created_at": row["created_at"],
        }


# ════════════════════════════════════════════
# GET BY ASSESSMENT ID
# ════════════════════════════════════════════

async def get_assessment_by_assessment_id(assessment_id: str) -> Optional[dict]:
    """Lấy 1 assessment theo assessment_id (business transaction ID)."""
    if _USE_POSTGRES:
        return await _get_by_assessment_id_pg(assessment_id)
    else:
        return await _get_by_assessment_id_sqlite(assessment_id)


async def _get_by_assessment_id_pg(assessment_id: str):
    pool = await _get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM assessments WHERE assessment_id = $1", assessment_id
        )
        if not row:
            return None

        return {
            "id": row["id"],
            "assessment_id": row["assessment_id"],
            "thread_id": row["thread_id"],
            "customer_id": row["customer_id"],
            "customer_name": row["customer_name"],
            "loan_amount": row["loan_amount"],
            "term_months": row["term_months"],
            "decision": row["decision"],
            "cic_score": row["cic_score"],
            "dti": row["dti"],
            "approved_limit": row["approved_limit"],
            "reasoning_trail": json.loads(row["reasoning_trail"] or "[]"),
            "report": row["report"],
            "needs_human_review": bool(row["needs_human_review"]),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }


async def _get_by_assessment_id_sqlite(assessment_id: str):
    import aiosqlite
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM assessments WHERE assessment_id = ?", (assessment_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return {
            "id": row["id"],
            "assessment_id": row["assessment_id"],
            "thread_id": row["thread_id"],
            "customer_id": row["customer_id"],
            "customer_name": row["customer_name"],
            "loan_amount": row["loan_amount"],
            "term_months": row["term_months"],
            "decision": row["decision"],
            "cic_score": row["cic_score"],
            "dti": row["dti"],
            "approved_limit": row["approved_limit"],
            "reasoning_trail": json.loads(row["reasoning_trail"] or "[]"),
            "report": row["report"],
            "needs_human_review": bool(row["needs_human_review"]),
            "created_at": row["created_at"],
        }
