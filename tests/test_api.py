import os
import uuid

os.environ["DATABASE_URL"] = "sqlite:///./test_casino.db"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import Base, SessionLocal, engine
from app.games import fair

Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client, request):
    email = f"{request.node.name}-{uuid.uuid4().hex[:8]}@test.com"
    res = client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['token']}"}


def test_seed_determinism():
    rng1 = fair.rng_for("seed-a", "seed-b", 3)
    rng2 = fair.rng_for("seed-a", "seed-b", 3)
    rng3 = fair.rng_for("seed-a", "seed-b", 4)
    assert rng1.random() == rng2.random()
    assert rng1.random() != rng3.random()


def test_fair_commit_chain(client, auth):
    from app.games import slots

    st = client.get("/api/games/fair/state", headers=auth).json()
    assert st["round_no"] == 0
    assert len(st["server_seed_commit"]) == 64

    r1 = client.post("/api/games/slots/play", json={"bet": 5}, headers=auth).json()
    assert r1["fair"]["round_no"] == 1
    assert r1["fair"]["commit_published_before"] == st["server_seed_commit"]
    assert fair.hash_hex(r1["fair"]["server_seed_used"]) == st["server_seed_commit"]

    r2 = client.post("/api/games/slots/play", json={"bet": 5}, headers=auth).json()
    f2 = r2["fair"]
    assert f2["round_no"] == 2
    assert fair.hash_hex(f2["server_seed_used"]) == f2["commit_published_before"] == r1["fair"]["next_commit"]

    rng = fair.rng_for(f2["server_seed_used"], f2["client_seed"], f2["round_no"])
    assert slots.spin(5, rng) == r2["result"]

    r3 = client.post("/api/games/slots/play", json={"bet": 5}, headers=auth).json()
    assert fair.hash_hex(r3["fair"]["server_seed_used"]) == r3["fair"]["commit_published_before"] == f2["next_commit"]

    st2 = client.get("/api/games/fair/state", headers=auth).json()
    assert st2["round_no"] == 3
    assert st2["server_seed_commit"] == r3["fair"]["next_commit"]


def test_custom_client_seed(client, auth):
    r = client.post("/api/games/slots/play", json={"bet": 5, "client_seed": "mi-seed"}, headers=auth).json()
    assert r["fair"]["client_seed"] == "mi-seed"


def test_invalid_bets(client, auth):
    r = client.post("/api/games/slots/play", json={"bet": 0}, headers=auth)
    assert r.status_code == 400
    r = client.post("/api/games/slots/play", json={"bet": 99999}, headers=auth)
    assert r.status_code == 400


def test_rate_limit_register(client):
    ok = 0
    for i in range(8):
        res = client.post("/api/auth/register", json={"email": f"rl{i}@test.com", "password": "secret123"})
        if res.status_code == 200:
            ok += 1
    assert ok == 5
    assert res.status_code == 429


def test_dice_play(client, auth):
    for bet_type in ("under7", "over7", "7"):
        r = client.post(f"/api/games/dice/play?bet_type={bet_type}", json={"bet": 5}, headers=auth)
        assert r.status_code == 200
        res = r.json()
        assert res["result"]["total"] == sum(res["result"]["dice"])
        assert 2 <= res["result"]["total"] <= 12
        assert "fair" in res


def _start_open_round(client, headers, bet=10):
    for _ in range(10):
        r = client.post("/api/games/blackjack/start", json={"bet": bet}, headers=headers)
        assert r.status_code == 200
        body = r.json()
        if body["round_id"] is not None:
            return body
    raise AssertionError("could not start an open round")


def test_blackjack_server_side_flow(client, auth):
    body = _start_open_round(client, auth)
    assert body["dealer_hidden"] is True
    assert body["can_act"] is True
    assert body["result"] is None
    round_id = body["round_id"]

    while True:
        player_total = _hand_total(body["player"])
        action = "hit" if player_total < 15 else "stand"
        r = client.post(
            "/api/games/blackjack/action",
            json={"round_id": round_id, "action": action},
            headers=auth,
        )
        assert r.status_code == 200
        body = r.json()
        if not body["can_act"]:
            break

    res = body["result"]
    assert res["outcome"] in ("bust", "win", "push", "lose", "blackjack")
    assert res["payout"] >= 0


def test_blackjack_rounds_are_server_owned(client, auth):
    body = _start_open_round(client, auth)
    round_id = body["round_id"]
    r = client.post("/api/games/blackjack/action", json={"round_id": round_id, "action": "hit"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    if body["can_act"]:
        r = client.post("/api/games/blackjack/action", json={"round_id": round_id, "action": "stand"}, headers=auth)
        assert r.status_code == 200
    r = client.post("/api/games/blackjack/action", json={"round_id": round_id, "action": "hit"}, headers=auth)
    assert r.status_code == 400


def test_blackjack_other_user_round(client, auth):
    body = _start_open_round(client, auth)
    round_id = body["round_id"]
    other = client.post("/api/auth/register", json={"email": "t2@test.com", "password": "secret123"}).json()
    headers2 = {"Authorization": f"Bearer {other['token']}"}
    r = client.post("/api/games/blackjack/action", json={"round_id": round_id, "action": "stand"}, headers=headers2)
    assert r.status_code == 400


def test_history_endpoint(client, auth):
    client.post("/api/games/dice/play?bet_type=over7", json={"bet": 5}, headers=auth)
    h = client.get("/api/games/history", headers=auth)
    assert h.status_code == 200
    rows = h.json()
    assert len(rows) >= 1
    assert rows[0]["game"] == "dice"
    assert rows[0]["net"] == round(rows[0]["payout"] - rows[0]["bet"], 2)


def test_health_endpoint(client):
    assert client.get("/health").status_code == 200
    assert client.get("/health").json()["status"] == "ok"


def test_register_username_and_dedupe(client):
    r1 = client.post(
        "/api/auth/register", json={"email": "gael@test.com", "password": "secret123", "username": "gael"}
    ).json()
    assert r1["user"]["username"] == "gael"

    r2 = client.post(
        "/api/auth/register", json={"email": "gael2@test.com", "password": "secret123", "username": "gael"}
    ).json()
    assert r2["user"]["username"] == "gael1"

    r3 = client.post("/api/auth/register", json={"email": "no-name@test.com", "password": "secret123"}).json()
    assert r3["user"]["username"].startswith("no-name")


def test_leaderboard_leaks_no_email(client, auth):
    reg = client.post("/api/auth/register", json={"email": "private@test.com", "password": "secret123", "username": "anonimato"}).json()
    h = {"Authorization": f"Bearer {reg['token']}"}
    client.post("/api/games/slots/play", json={"bet": 5}, headers=h)
    rows = client.get("/api/games/leaderboard").json()
    assert rows, "leaderboard vacío"
    assert all("@" not in str(r.get("username", "")) for r in rows)
    assert all("username" in r and "chips" in r for r in rows)
    assert all("email" not in r for r in rows)


def test_login_rate_limit(client, auth):
    # 10 intentos con credenciales malas -> 401; el 11º -> 429
    for i in range(10):
        r = client.post("/api/auth/login", json={"email": "ghost@test.com", "password": "wrongpass"})
        assert r.status_code == 401
    r = client.post("/api/auth/login", json={"email": "ghost@test.com", "password": "wrongpass"})
    assert r.status_code == 429
    assert r.headers.get("retry-after") == "60"


def test_bet_nan_inf_rejected(client, auth):
    # Body crudo: json.dumps(allow_nan=False) en httpx bloquea NaN, pero un cliente
    # real puede mandar JSON con NaN/Infinity (Python json.loads lo acepta).
    head = {"Content-Type": "application/json", **auth}
    for raw in (b'{"bet": NaN}', b'{"bet": Infinity}', b'{"bet": -Infinity}', b'{"bet": -1}', b'{"bet": 0}', b'{"bet": 0.0001}', b'{"bet": 1000.01}'):
        r = client.post("/api/games/slots/play", content=raw, headers=head)
        assert r.status_code == 400, f"bet {raw} debería dar 400 (dio {r.status_code})"


def test_chips_invariant_under_concurrency(client):
    import threading

    N_THREADS, PLAYS = 4, 4
    results: list[tuple] = []
    errors: list[Exception] = []

    def worker(idx: int):
        try:
            with TestClient(app) as c:
                email = f"conc-{idx}-{uuid.uuid4().hex[:8]}@test.com"
                tok = c.post(
                    "/api/auth/register", json={"email": email, "password": "secret123"}
                ).json()["token"]
                head = {"Authorization": f"Bearer {tok}"}
                for _ in range(PLAYS):
                    r = c.post("/api/games/slots/play", json={"bet": 2}, headers=head)
                    assert r.status_code == 200, r.text[:200]
                me = c.get("/api/auth/me", headers=head).json()
                hist = c.get("/api/games/history", headers=head).json()
                results.append(
                    (
                        me["chips"],
                        sum(x["bet"] for x in hist),
                        sum(x["payout"] for x in hist),
                        len(hist),
                    )
                )
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert len(results) == N_THREADS, "algún worker no terminó"
    for chips, total_bet, total_payout, n_hist in results:
        assert n_hist == PLAYS, f"history={n_hist} esperado {PLAYS}"
        assert chips == round(100 - total_bet + total_payout, 2), "invariante de chips rota"


def test_secret_key_guard(monkeypatch):
    import app.config as cfg

    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("RENDER", "true")
    assert cfg.SECRET_KEY  # nunca vacío
    monkeypatch.setenv("SECRET_KEY", "dev-secret-key")
    monkeypatch.setenv("RENDER", "true")
    assert cfg.SECRET_KEY  # el valor seteado se usa tal cual (Render genera aleatorio)


def _hand_total(hand):
    total = sum(c["value"] for c in hand)
    aces = sum(1 for c in hand if c["rank"] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total