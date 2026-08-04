from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date
from typing import Optional
import os

app = FastAPI(title="BRVM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "brvm-postgres"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "brvm"),
    "user": os.getenv("DB_USER", "brvm_bot"),
    "password": os.getenv("DB_PASS", "BrvmSecure2026!")
}


def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


@app.get("/")
def root():
    return {"message": "BRVM API", "version": "1.0.0", "status": "running"}


@app.get("/health")
def health():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


@app.get("/tickers")
def get_tickers():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT DISTINCT ticker FROM daily ORDER BY ticker")
    tickers = [row["ticker"] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return {"tickers": tickers, "count": len(tickers)}


@app.get("/daily")
def get_daily(
    ticker: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = "SELECT * FROM daily WHERE 1=1"
    params = []

    if ticker:
        query += " AND ticker = %s"
        params.append(ticker.upper())
    if start_date:
        query += " AND date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND date <= %s"
        params.append(end_date)

    query += " ORDER BY date DESC, ticker LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = cur.fetchall()

    for row in rows:
        if row.get("created_at"):
            row["created_at"] = row["created_at"].isoformat()

    cur.close()
    conn.close()

    return {"data": rows, "count": len(rows), "limit": limit, "offset": offset}


@app.get("/market_data")
def get_market_data(
    ticker: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = "SELECT * FROM market_data WHERE 1=1"
    params = []

    if ticker:
        query += " AND ticker = %s"
        params.append(ticker.upper())
    if start_date:
        query += " AND date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND date <= %s"
        params.append(end_date)

    query += " ORDER BY timestamp DESC, ticker LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = cur.fetchall()

    for row in rows:
        for key in ["timestamp", "created_at"]:
            if row.get(key):
                row[key] = row[key].isoformat()
        if row.get("date"):
            row["date"] = row["date"].isoformat()

    cur.close()
    conn.close()

    return {"data": rows, "count": len(rows), "limit": limit, "offset": offset}


@app.get("/stats")
def get_stats():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT COUNT(*) as total, COUNT(DISTINCT ticker) as tickers, "
        "MIN(date) as first_date, MAX(date) as last_date FROM daily"
    )
    daily_stats = cur.fetchone()

    cur.execute(
        "SELECT COUNT(*) as total, COUNT(DISTINCT ticker) as tickers, "
        "MIN(date) as first_date, MAX(date) as last_date FROM market_data"
    )
    market_stats = cur.fetchone()

    cur.close()
    conn.close()

    return {
        "daily": {
            "total_rows": daily_stats["total"],
            "tickers": daily_stats["tickers"],
            "first_date": daily_stats["first_date"].isoformat() if daily_stats["first_date"] else None,
            "last_date": daily_stats["last_date"].isoformat() if daily_stats["last_date"] else None,
        },
        "market_data": {
            "total_rows": market_stats["total"],
            "tickers": market_stats["tickers"],
            "first_date": market_stats["first_date"].isoformat() if market_stats["first_date"] else None,
            "last_date": market_stats["last_date"].isoformat() if market_stats["last_date"] else None,
        },
    }


@app.get("/ticker/{ticker}")
def get_ticker_info(ticker: str):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT MIN(date) as first_date, MAX(date) as last_date, COUNT(*) as total_days "
        "FROM daily WHERE ticker = %s",
        (ticker.upper(),),
    )
    daily_info = cur.fetchone()

    if not daily_info or not daily_info["total_days"]:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ticker {ticker.upper()} not found")

    cur.execute(
        "SELECT * FROM daily WHERE ticker = %s ORDER BY date DESC LIMIT 1",
        (ticker.upper(),),
    )
    latest = cur.fetchone()
    if latest and latest.get("created_at"):
        latest["created_at"] = latest["created_at"].isoformat()
    if latest and latest.get("date"):
        latest["date"] = latest["date"].isoformat()

    cur.close()
    conn.close()

    return {
        "ticker": ticker.upper(),
        "first_date": daily_info["first_date"].isoformat(),
        "last_date": daily_info["last_date"].isoformat(),
        "total_days": daily_info["total_days"],
        "latest": latest,
    }
