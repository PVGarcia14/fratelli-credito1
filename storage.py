from __future__ import annotations
import json, sqlite3
from datetime import datetime
from pathlib import Path

class Store:
    def __init__(self,path:Path):
        self.path=path
        self.init()
    def conn(self): return sqlite3.connect(self.path)
    def init(self):
        with self.conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS analyses(id INTEGER PRIMARY KEY, created_at TEXT, cnpj TEXT, company TEXT, score REAL, confidence REAL, limit_value REAL, requested REAL, decision TEXT, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, created_at TEXT, action TEXT, cnpj TEXT, details TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS customer_history(cnpj TEXT PRIMARY KEY, purchases REAL DEFAULT 0, orders INTEGER DEFAULT 0, paid_on_time INTEGER DEFAULT 0, overdue REAL DEFAULT 0, used_limit REAL DEFAULT 0, updated_at TEXT)")
    def save_analysis(self, payload):
        with self.conn() as c:
            c.execute("INSERT INTO analyses(created_at,cnpj,company,score,confidence,limit_value,requested,decision,payload) VALUES(?,?,?,?,?,?,?,?,?)",(datetime.now().isoformat(timespec='seconds'),payload.get('cnpj'),payload.get('company',''),payload.get('score',0),payload.get('confidence',0),payload.get('limit',0),payload.get('requested',0),payload.get('decision',''),json.dumps(payload,ensure_ascii=False)))
    def audit(self,action,cnpj,details):
        with self.conn() as c: c.execute("INSERT INTO audit(created_at,action,cnpj,details) VALUES(?,?,?,?)",(datetime.now().isoformat(timespec='seconds'),action,cnpj,json.dumps(details,ensure_ascii=False)))
    def history(self,limit=100):
        with self.conn() as c: return c.execute("SELECT created_at,cnpj,company,score,confidence,limit_value,requested,decision FROM analyses ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    def portfolio(self):
        with self.conn() as c: return c.execute("SELECT COUNT(*),COALESCE(SUM(limit_value),0),COALESCE(SUM(requested),0),COALESCE(SUM(CASE WHEN decision='RECUSAR' THEN 1 ELSE 0 END),0) FROM analyses").fetchone()
