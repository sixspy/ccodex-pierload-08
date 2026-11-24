"""无快照禁放（快照案辛 · 第 8 号）三红失败测。

红测链：
  失败测甲：无最新闸代快照却放行 -> 须整笔回滚、正式册零增。
  失败测乙：对账/单票证明不得把无快照票记为已放行齐套。
  争用失败测：双会话同票抢闸口写（封闸/放行），后到只记争用痕、不写业务。

裁决见 docs/无快照禁放说明.md（采用甲路径，当日锁死）。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from db import connect, init_db


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr("db.DB_PATH", tmp_path / "t.db")
    init_db()
    yield


def _auth(c: TestClient, user: str = "admin", password: str = "admin123") -> dict:
    tok = c.post(
        "/api/login", json={"username": user, "password": password}
    ).json()["token"]
    return {"Authorization": "Bearer " + tok}


def _ticket_id(code: str) -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM weigh_tickets WHERE ticket_code=?", (code,)
        ).fetchone()
        return int(row["id"])


def _make_adjudicated_ticket(c: TestClient, h: dict, code: str) -> int:
    """造一张已裁定、无任何闸代快照的新票（非超重，可直接走放行流程）。"""
    lanes = c.get("/api/lanes", headers=h).json()["items"]
    lane = next(x for x in lanes if x["lane_code"] == "LN-S-01-OUT")
    r = c.post(
        "/api/tickets",
        headers=h,
        json={
            "lane_id": lane["id"],
            "bl_ref": "BL-2026-0102",
            "vehicle_plate": "测H08·红01",
            "axle_weights": [
                {"axle": 1, "w": 6.0},
                {"axle": 2, "w": 5.5},
            ],
            "ticket_code": code,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "已裁定"
    return r.json()["id"]


def _formal_release_count(ticket_id: int) -> int:
    with connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) c FROM gate_releases "
            "WHERE ticket_id=? AND status='已放行'",
            (ticket_id,),
        ).fetchone()["c"]


def _ticket_status(ticket_id: int) -> str:
    with connect() as conn:
        return conn.execute(
            "SELECT status FROM weigh_tickets WHERE id=?", (ticket_id,)
        ).fetchone()["status"]


# ---------------------------------------------------------------------------
# 失败测甲：无最新闸代快照 -> 放行整笔回滚，正式册零增
# ---------------------------------------------------------------------------
def test_甲_无最新闸代快照放行整笔回滚正式册零增():
    c = TestClient(app)
    h = _auth(c)
    ticket_id = _make_adjudicated_ticket(c, h, "WT-H08-RED-A")

    # 前置：无任何快照
    with connect() as conn:
        seal_n = conn.execute(
            "SELECT COUNT(*) c FROM gate_seals WHERE ticket_id=?", (ticket_id,)
        ).fetchone()["c"]
    assert seal_n == 0
    before = _formal_release_count(ticket_id)

    resp = c.post(
        "/api/gate/release",
        headers=h,
        json={"ticket_id": ticket_id, "officer": "红测甲"},
    )

    # 甲路径：闸口拒绝（409），整笔回滚
    assert resp.status_code == 409, resp.text
    assert _formal_release_count(ticket_id) == before  # 正式册零增
    assert _ticket_status(ticket_id) == "已裁定"  # 票态零改

    # 补上最新闸代快照后，同一票必须能够原子放行成功（证明禁放只认快照、不误伤）
    seal = c.post("/api/seals", headers=h, json={"ticket_id": ticket_id})
    assert seal.status_code == 200, seal.text
    ok = c.post(
        "/api/gate/release",
        headers=h,
        json={"ticket_id": ticket_id, "officer": "红测甲"},
    )
    assert ok.status_code == 200, ok.text
    assert _formal_release_count(ticket_id) == before + 1


def test_甲_快照闸代落后于票最新代同样禁放():
    """快照存在但不是最新闸代（票已升代）仍属无最新快照，禁放。"""
    c = TestClient(app)
    h = _auth(c)
    ticket_id = _make_adjudicated_ticket(c, h, "WT-H08-RED-A2")
    # 封闸升代到 G2，再人工把票推进到 G3 而不补快照（模拟快照缺失最新代）
    seal = c.post("/api/seals", headers=h, json={"ticket_id": ticket_id})
    assert seal.status_code == 200
    with connect() as conn:
        conn.execute(
            "UPDATE weigh_tickets SET generation=generation+1 WHERE id=?",
            (ticket_id,),
        )
        conn.commit()

    resp = c.post(
        "/api/gate/release", headers=h, json={"ticket_id": ticket_id}
    )
    assert resp.status_code == 409, resp.text
    assert "快照" in resp.json()["detail"]  # 必须因无最新快照禁放，而非泛化票锁
    assert _formal_release_count(ticket_id) == 0
    # 补出 G3 最新快照后放行
    with connect() as conn:
        gen = conn.execute(
            "SELECT generation FROM weigh_tickets WHERE id=?", (ticket_id,)
        ).fetchone()["generation"]
        conn.execute(
            """INSERT INTO gate_seals(ticket_id,ticket_generation,manifest,seal_ref,status,sealed_at)
               VALUES (?,?,?,?,'已封闸',?)""",
            (ticket_id, gen, "补最新代清单", f"GS-WT-H08-RED-A2-G{gen}", "2026-11-24T09:00:00"),
        )
        conn.commit()
    ok = c.post(
        "/api/gate/release", headers=h, json={"ticket_id": ticket_id}
    )
    assert ok.status_code == 200, ok.text


# ---------------------------------------------------------------------------
# 失败测乙：对账/证明不得把无快照票记为「已放行齐套」
# ---------------------------------------------------------------------------
def test_乙_对账不把无快照票记为已放行齐套():
    c = TestClient(app)
    h = _auth(c)

    # 种子里 BL-2026-0105 的票 WT-NOSNAP-H08-001 有正式放行行 PL-H08 但零快照
    recon = c.get("/api/reconcile/BL-2026-0105", headers=h)
    assert recon.status_code == 200, recon.text
    data = recon.json()
    ticket_codes = {t["ticket_code"] for t in data["tickets"]}
    assert "WT-NOSNAP-H08-001" in ticket_codes

    # 齐套口径必须就闸口：无最新闸代快照 -> 不得标记齐套/可出证明
    assert data["proof_ready"] is False
    assert data["snapshot_complete_releases"] == 0
    assert data["releases_missing_snapshot"] >= 1

    # 单票证明同样不得自算「已放行齐套」
    proof = c.get("/api/proof/ticket/WT-NOSNAP-H08-001", headers=h).json()
    assert proof["released"] is True  # 放行事实如实暴露
    assert proof["has_latest_snapshot"] is False
    assert proof["coherent"] is False  # 无快照不得判齐套


def test_乙_快照齐套后对账才认可():
    """对照：补齐最新闸代快照后，对账口径方可认可（同源闸口）。"""
    c = TestClient(app)
    h = _auth(c)
    ticket_id = _ticket_id("WT-NOSNAP-H08-001")
    with connect() as conn:
        gen = conn.execute(
            "SELECT generation FROM weigh_tickets WHERE id=?", (ticket_id,)
        ).fetchone()["generation"]
        conn.execute(
            """INSERT INTO gate_seals(ticket_id,ticket_generation,manifest,seal_ref,status,sealed_at)
               VALUES (?,?,?,?,'已封闸',?)""",
            (
                ticket_id,
                gen,
                "票号=WT-NOSNAP-H08-001;闸代=1;补快照",
                f"GS-WT-NOSNAP-H08-001-G{gen}",
                "2026-11-24T09:10:00",
            ),
        )
        conn.commit()

    recon = c.get("/api/reconcile/BL-2026-0105", headers=h).json()
    assert recon["snapshot_complete_releases"] >= 1
    assert recon["releases_missing_snapshot"] == 0
    proof = c.get("/api/proof/ticket/WT-NOSNAP-H08-001", headers=h).json()
    assert proof["has_latest_snapshot"] is True
    assert proof["coherent"] is True


# ---------------------------------------------------------------------------
# 争用失败测：双会话同票抢闸口写，后到只记争用痕、不写业务
# ---------------------------------------------------------------------------
def test_丙_双会话同票抢闸口后到只记争用痕不写放行():
    c = TestClient(app)
    h1 = _auth(c, "admin", "admin123")
    h2 = _auth(c, "writer", "writer123")
    ticket_id = _make_adjudicated_ticket(c, h1, "WT-H08-RED-C")
    # 先封闸造出最新快照，使争用发生在锁层而非快照校验层
    assert c.post("/api/seals", headers=h1, json={"ticket_id": ticket_id}).status_code == 200

    # 会话一占住该票闸口锁不释放
    with connect() as conn:
        from locks import try_acquire

        assert try_acquire(conn, f"gate:{ticket_id}", "admin") is True
        conn.commit()

    try:
        # 会话二抢同票放行：须 409 争用，正式册零增
        resp = c.post(
            "/api/gate/release",
            headers=h2,
            json={"ticket_id": ticket_id, "officer": "会话二"},
        )
        assert resp.status_code == 409, resp.text
        assert "争用" in resp.json()["detail"]
        assert _formal_release_count(ticket_id) == 0

        # 会话二改抢同票封闸：同一闸口锁同样挡住，快照零增
        seals_before = None
        with connect() as conn:
            seals_before = conn.execute(
                "SELECT COUNT(*) c FROM gate_seals WHERE ticket_id=?", (ticket_id,)
            ).fetchone()["c"]
        seal_resp = c.post(
            "/api/seals", headers=h2, json={"ticket_id": ticket_id}
        )
        assert seal_resp.status_code == 409, seal_resp.text
        with connect() as conn:
            seals_after = conn.execute(
                "SELECT COUNT(*) c FROM gate_seals WHERE ticket_id=?", (ticket_id,)
            ).fetchone()["c"]
            assert seals_after == seals_before

        # 争用痕只登记、不产生业务写
        contention = c.get("/api/contention", headers=h1).json()["items"]
        hits = [x for x in contention if x["lock_key"] == f"gate:{ticket_id}"]
        assert len(hits) >= 2
        assert any(x["actor"] == "writer" for x in hits)
    finally:
        with connect() as conn:
            from locks import release as _release

            _release(conn, f"gate:{ticket_id}", "admin")
            conn.commit()

    # 锁释放后，会话一可正常放行（恰好一条正式行）
    ok = c.post(
        "/api/gate/release",
        headers=h1,
        json={"ticket_id": ticket_id, "officer": "会话一"},
    )
    assert ok.status_code == 200, ok.text
    assert _formal_release_count(ticket_id) == 1
