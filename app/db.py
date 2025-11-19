# app/db.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from pathlib import Path
import sqlite3
import time

router = APIRouter()

DB_PATH = Path(__file__).parent / "board.db"

# Pydantic models used for request/response validation
class BoardItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    contact: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    details: str = Field("", max_length=200)
    type: str = Field("req")  # default 'req' or 'offer'

class BoardItemOut(BoardItemCreate):
    id: int
    ts: int

# Initialize DB (creates file and table if needed)
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS board (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                location TEXT NOT NULL,
                details TEXT,
                ts INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

init_db()

# Helper to open connection
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# List items (most recent first)
@router.get("/board", response_model=List[BoardItemOut])
def get_board(limit: int = 200):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute("SELECT id, type, name, contact, location, details, ts FROM board ORDER BY ts DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        return [BoardItemOut(id=row["id"], type=row["type"], name=row["name"], contact=row["contact"], location=row["location"], details=row["details"] or "", ts=row["ts"]) for row in rows]
    finally:
        conn.close()

# POST request -> /board/request
@router.post("/board/request", response_model=BoardItemOut, status_code=201)
def post_request(item: BoardItemCreate):
    # ensure type is request
    item_data = item.dict()
    item_data["type"] = "req"
    return _insert_board_item(item_data)

# POST offer -> /board/offer
@router.post("/board/offer", response_model=BoardItemOut, status_code=201)
def post_offer(item: BoardItemCreate):
    item_data = item.dict()
    item_data["type"] = "offer"
    return _insert_board_item(item_data)

def _insert_board_item(payload: dict) -> BoardItemOut:
    # payload must contain type, name, contact, location, details
    if payload.get("type") not in ("req", "offer"):
        raise HTTPException(status_code=400, detail="type must be 'req' or 'offer'")
    ts = int(time.time() * 1000)
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO board (type, name, contact, location, details, ts) VALUES (?, ?, ?, ?, ?, ?)",
            (payload["type"], payload["name"], payload["contact"], payload["location"], payload.get("details", ""), ts),
        )
        conn.commit()
        id_ = c.lastrowid
        return BoardItemOut(id=id_, type=payload["type"], name=payload["name"], contact=payload["contact"], location=payload["location"], details=payload.get("details", ""), ts=ts)
    finally:
        conn.close()
