"""提单册与过磅票对账证明。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from auth import AuthHeader, require_user
from validators import validate_bl_match

router = APIRouter(tags=["reconcile"])


@router.get("/api/reconcile")
def reconcile_all(authorization: AuthHeader = None):
    require_user(authorization)
    from db import connect

    with connect() as conn:
        rows = conn.execute(
            """SELECT bl_code, declared_gross_t FROM bl_manifests ORDER BY bl_code"""
        ).fetchall()
        items = []
        for bl in rows:
            items.append(_reconcile_bl(conn, bl["bl_code"]))
        return {"items": items}


@router.get("/api/reconcile/{bl_code}")
def reconcile_one(bl_code: str, authorization: AuthHeader = None):
    require_user(authorization)
    from db import connect

    with connect() as conn:
        bl = conn.execute(
            "SELECT * FROM bl_manifests WHERE bl_code=?", (bl_code,)
        ).fetchone()
        if not bl:
            raise HTTPException(404, "提单不存在")
        return _reconcile_bl(conn, bl_code)


def _reconcile_bl(conn, bl_code: str) -> dict:
    bl = conn.execute(
        "SELECT * FROM bl_manifests WHERE bl_code=?", (bl_code,)
    ).fetchone()
    tickets = conn.execute(
        """SELECT ticket_code, gross_t, status, generation FROM weigh_tickets
           WHERE bl_ref=? AND status NOT IN ('作废')""",
        (bl_code,),
    ).fetchall()
    if not tickets:
        return {
            "bl_code": bl_code,
            "declared_gross_t": bl["declared_gross_t"],
            "ticket_sum_t": 0,
            "balanced": False,
            "reason": "无过磅票",
            "tickets": [],
        }
    ticket_sum = round(sum(float(t["gross_t"]) for t in tickets), 3)
    declared = float(bl["declared_gross_t"])
    matched = validate_bl_match(declared, ticket_sum, tolerance=0.1)
    seal_rows = conn.execute(
        """SELECT s.seal_ref, s.ticket_generation, t.ticket_code
           FROM gate_seals s JOIN weigh_tickets t ON t.id=s.ticket_id
           WHERE t.bl_ref=?""",
        (bl_code,),
    ).fetchall()
    # 齐套口径就闸口：正式放行行必须配上与票最新闸代一致的已封闸快照。
    released_rows = conn.execute(
        """SELECT t.id, t.ticket_code, t.generation
           FROM gate_releases g JOIN weigh_tickets t ON t.id=g.ticket_id
           WHERE t.bl_ref=? AND g.status='已放行'""",
        (bl_code,),
    ).fetchall()
    releases_missing_snapshot = 0
    snapshot_complete_releases = 0
    for r in released_rows:
        latest = conn.execute(
            """SELECT 1 FROM gate_seals
               WHERE ticket_id=? AND ticket_generation=? AND status='已封闸'
               LIMIT 1""",
            (r["id"], r["generation"]),
        ).fetchone()
        if latest:
            snapshot_complete_releases += 1
        else:
            releases_missing_snapshot += 1
    proof_ok = (
        matched
        and releases_missing_snapshot == 0
        and snapshot_complete_releases >= 1
    )
    return {
        "bl_code": bl_code,
        "declared_gross_t": declared,
        "ticket_sum_t": ticket_sum,
        "balanced": matched,
        "proof_ready": proof_ok,
        "seal_count": len(seal_rows),
        "released_count": len(released_rows),
        "snapshot_complete_releases": snapshot_complete_releases,
        "releases_missing_snapshot": releases_missing_snapshot,
        "tickets": [dict(t) for t in tickets],
        "seals": [dict(s) for s in seal_rows],
    }


@router.get("/api/proof/ticket/{ticket_code}")
def proof_ticket(ticket_code: str, authorization: AuthHeader = None):
    require_user(authorization)
    from db import connect

    with connect() as conn:
        ticket = conn.execute(
            "SELECT * FROM weigh_tickets WHERE ticket_code=?", (ticket_code,)
        ).fetchone()
        if not ticket:
            raise HTTPException(404, "票不存在")
        bl = conn.execute(
            "SELECT * FROM bl_manifests WHERE bl_code=?", (ticket["bl_ref"],)
        ).fetchone()
        seal = conn.execute(
            """SELECT * FROM gate_seals WHERE ticket_id=? ORDER BY id DESC LIMIT 1""",
            (ticket["id"],),
        ).fetchone()
        release = conn.execute(
            """SELECT * FROM gate_releases WHERE ticket_id=? AND status='已放行'""",
            (ticket["id"],),
        ).fetchone()
        overload_closed = not conn.execute(
            """SELECT id FROM overload_holds WHERE ticket_id=? AND status='开放'""",
            (ticket["id"],),
        ).fetchone()
        manifest_match = False
        if seal and bl:
            manifest_match = validate_bl_match(
                float(bl["declared_gross_t"]), float(ticket["gross_t"])
            )
        latest_snapshot = conn.execute(
            """SELECT id FROM gate_seals
               WHERE ticket_id=? AND ticket_generation=? AND status='已封闸'
               LIMIT 1""",
            (ticket["id"], ticket["generation"]),
        ).fetchone()
        has_latest_snapshot = latest_snapshot is not None
        return {
            "ticket_code": ticket_code,
            "bl_ref": ticket["bl_ref"],
            "gross_t": ticket["gross_t"],
            "manifest_matches_bl": manifest_match,
            "has_seal": seal is not None,
            "has_latest_snapshot": has_latest_snapshot,
            "seal_generation": seal["ticket_generation"] if seal else None,
            "released": release is not None,
            "overload_closed": overload_closed,
            # 齐套就闸口：须最新闸代快照在，且无开放超重，放行与快照口径一致。
            "coherent": bool(
                manifest_match
                and overload_closed
                and has_latest_snapshot
                and release is not None
            ),
        }