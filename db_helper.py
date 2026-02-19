# -*- coding: utf-8 -*-
"""共用数据库：个人资质默认值 + 机场风险与提示"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flight_prep.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    """初始化数据库表"""
    conn = get_conn()
    cur = conn.cursor()
    # 个人资质（单行，id=1）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT,
            tech_level TEXT,
            radio_qual TEXT,
            total_landings INTEGER,
            total_hours REAL,
            type_landings INTEGER,
            type_hours REAL,
            previous_aircraft TEXT,
            app_alert TEXT,
            efb_status TEXT,
            last_pf_time TEXT,
            landing_quality TEXT,
            pickup_location TEXT,
            updated_at TEXT
        )
    """)
    # 机场风险与提示
    cur.execute("""
        CREATE TABLE IF NOT EXISTS airport (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            airport_name TEXT UNIQUE NOT NULL,
            risks_tips TEXT,
            notams_tips TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    # 航班数据（航班号、航线、起飞时间、签到时间）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flight (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_number TEXT NOT NULL,
            route TEXT,
            dep_time TEXT,
            sign_in_time TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()


# ---------- 个人资质 ----------
def get_profile():
    """获取个人资质（用于表单默认值），无则返回 None"""
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM profile WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    cols = ["id", "name", "tech_level", "radio_qual", "total_landings", "total_hours",
            "type_landings", "type_hours", "previous_aircraft", "app_alert", "efb_status",
            "last_pf_time", "landing_quality", "pickup_location", "updated_at"]
    return dict(zip(cols, row))


def save_profile(data: dict):
    """保存个人资质（覆盖 id=1 的一行）"""
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("""
        INSERT INTO profile (id, name, tech_level, radio_qual, total_landings, total_hours,
            type_landings, type_hours, previous_aircraft, app_alert, efb_status,
            last_pf_time, landing_quality, pickup_location, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, tech_level=excluded.tech_level, radio_qual=excluded.radio_qual,
            total_landings=excluded.total_landings, total_hours=excluded.total_hours,
            type_landings=excluded.type_landings, type_hours=excluded.type_hours,
            previous_aircraft=excluded.previous_aircraft, app_alert=excluded.app_alert,
            efb_status=excluded.efb_status, last_pf_time=excluded.last_pf_time,
            landing_quality=excluded.landing_quality, pickup_location=excluded.pickup_location,
            updated_at=excluded.updated_at
    """, (
        data.get("name"), data.get("tech_level"), data.get("radio_qual"),
        data.get("total_landings"), data.get("total_hours"),
        data.get("type_landings"), data.get("type_hours"),
        data.get("previous_aircraft"), data.get("app_alert"), data.get("efb_status"),
        data.get("last_pf_time"), data.get("landing_quality"), data.get("pickup_location"),
        now
    ))
    conn.commit()
    conn.close()


def update_last_pf_time(last_pf_time: str):
    """仅更新“上次主飞起落时间及机型”，用于生成文档后保存"""
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("SELECT id FROM profile WHERE id = 1")
    if cur.fetchone():
        cur.execute("UPDATE profile SET last_pf_time = ?, updated_at = ? WHERE id = 1", (last_pf_time, now))
    else:
        cur.execute("""
            INSERT INTO profile (id, last_pf_time, updated_at)
            VALUES (1, ?, ?)
        """, (last_pf_time, now))
    conn.commit()
    conn.close()


# ---------- 机场 ----------
def list_airports():
    """所有机场列表"""
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, airport_name, risks_tips, notams_tips FROM airport ORDER BY airport_name")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "airport_name": r[1], "risks_tips": r[2] or "", "notams_tips": r[3] or ""} for r in rows]


def get_airport_by_name(airport_name: str):
    """按名称精确匹配机场（用于航线解析后查找）"""
    if not airport_name or not airport_name.strip():
        return None
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    name = airport_name.strip()
    cur.execute("SELECT airport_name, risks_tips, notams_tips FROM airport WHERE airport_name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"airport_name": row[0], "risks_tips": row[1] or "", "notams_tips": row[2] or ""}


def get_risks_for_route(route: str):
    """根据航线字符串（如 三亚-浦东-三亚）从数据库拼接各机场的风险与提示"""
    if not route or not route.strip():
        return ""
    parts = [p.strip() for p in route.replace("—", "-").split("-") if p.strip()]
    if not parts:
        return ""
    seen = set()
    lines = []
    for ap in parts:
        if ap in seen:
            continue
        seen.add(ap)
        info = get_airport_by_name(ap)
        if info and info.get("risks_tips"):
            lines.append(f"【{info['airport_name']}\n{info['risks_tips']}")
    return "\n\n".join(lines) if lines else ""


def get_notams_for_route(route: str):
    """根据航线从数据库拼接各机场的通告提示"""
    if not route or not route.strip():
        return ""
    parts = [p.strip() for p in route.replace("—", "-").split("-") if p.strip()]
    if not parts:
        return ""
    seen = set()
    lines = []
    for ap in parts:
        if ap in seen:
            continue
        seen.add(ap)
        info = get_airport_by_name(ap)
        if info and info.get("notams_tips"):
            lines.append(f"【{info['airport_name']}\n{info['notams_tips']}")
    return "\n\n".join(lines) if lines else ""


def add_or_update_airport(airport_name: str, risks_tips: str = "", notams_tips: str = ""):
    """新增或按名称更新机场"""
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute(
        """INSERT INTO airport (airport_name, risks_tips, notams_tips, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(airport_name) DO UPDATE SET
           risks_tips=excluded.risks_tips, notams_tips=excluded.notams_tips, updated_at=excluded.updated_at
        """,
        (airport_name.strip(), risks_tips or "", notams_tips or "", now, now)
    )
    conn.commit()
    conn.close()


def delete_airport(airport_id: int):
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM airport WHERE id = ?", (airport_id,))
    conn.commit()
    conn.close()


# ---------- 航班数据 ----------
def _normalize_flight_number(num: str):
    """提取航班号中的数字部分用于匹配，如 CZ3835/6 -> 3835/6"""
    if not num or not isinstance(num, str):
        return ""
    s = num.strip().upper().replace(" ", "")
    for prefix in ("CZ", "MU", "CA", "3U", "MF", "HU"):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
            break
    return s

def get_flight_by_number(flight_number: str):
    """按航班号匹配航班（支持 CZ3835、3835、CZ3835/6 等），返回 route, dep_time, sign_in_time"""
    if not flight_number or not str(flight_number).strip():
        return None
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT flight_number, route, dep_time, sign_in_time FROM flight")
    rows = cur.fetchall()
    conn.close()
    key = _normalize_flight_number(flight_number)
    if not key:
        return None
    for r in rows:
        fn, route, dep, sign = r[0] or "", r[1] or "", r[2] or "", r[3] or ""
        if _normalize_flight_number(fn) == key or (fn and key in fn) or (fn and fn in flight_number.strip().upper()):
            return {"flight_number": fn, "route": route, "dep_time": dep, "sign_in_time": sign}
    return None

def list_flights():
    """所有航班列表"""
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, flight_number, route, dep_time, sign_in_time FROM flight ORDER BY flight_number")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "flight_number": r[1], "route": r[2] or "", "dep_time": r[3] or "", "sign_in_time": r[4] or ""} for r in rows]

def add_or_update_flight(flight_number: str, route: str = "", dep_time: str = "", sign_in_time: str = ""):
    """新增或按航班号更新航班"""
    if not flight_number or not flight_number.strip():
        return
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    fn = flight_number.strip().upper()
    cur.execute("SELECT id FROM flight WHERE flight_number = ?", (fn,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE flight SET route=?, dep_time=?, sign_in_time=?, updated_at=? WHERE id=?",
                    (route or "", dep_time or "", sign_in_time or "", now, row[0]))
    else:
        cur.execute("""INSERT INTO flight (flight_number, route, dep_time, sign_in_time, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""", (fn, route or "", dep_time or "", sign_in_time or "", now, now))
    conn.commit()
    conn.close()

def delete_flight(flight_id: int):
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM flight WHERE id = ?", (flight_id,))
    conn.commit()
    conn.close()
