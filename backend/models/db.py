"""
db.py — SQLite database interface for ClaimCopilot.
"""

import sqlite3
import json
from pathlib import Path
from config import RECORDS_DB

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(str(RECORDS_DB))
    # Return rows as dictionaries
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and performs auto-migrations."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Primary schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claim_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE,
                patient_name TEXT,
                policy_id TEXT,
                original_filename TEXT,
                decision TEXT,
                reason TEXT,
                result_json TEXT,
                file_bytes BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check for missing columns (Auto-migration)
        cursor.execute("PRAGMA table_info(claim_records)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        
        if 'decision' not in existing_cols:
            cursor.execute("ALTER TABLE claim_records ADD COLUMN decision TEXT")
        if 'reason' not in existing_cols:
            cursor.execute("ALTER TABLE claim_records ADD COLUMN reason TEXT")
            
        conn.commit()
    finally:
        conn.close()

def save_record(record_id: str, patient_name: str, policy_id: str, original_filename: str, result: dict, file_bytes: bytes):
    """Saves a claim record to the database with dedicated columns for fast indexing."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        decision = result.get("decision", "Unknown")
        reason = result.get("reason", "No reason provided")
        
        cursor.execute("""
            INSERT INTO claim_records (record_id, patient_name, policy_id, original_filename, decision, reason, result_json, file_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record_id,
            patient_name,
            policy_id,
            original_filename,
            decision,
            reason,
            json.dumps(result, default=str),
            file_bytes
        ))
        conn.commit()
    finally:
        conn.close()
