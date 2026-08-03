# Casino Demo (fichas virtuales)

Demo legal de casino con fichas virtuales — **sin dinero real**. Mismo stack que AutoClip: FastAPI + PostgreSQL + Render + Docker.

## Stack
- Backend: FastAPI, SQLAlchemy 2.x, bcrypt, PyJWT
- Base de datos: SQLite en disco persistente de Render (`/data`) — Postgres disponible si se quieren concursos multi-usuario
- Frontend: HTML/CSS/JS vanilla (SPA sin frameworks)
- Deploy: Render via `render.yaml` (web service docker + disk 5GB), puerto 10000

## Estructura
```
backend/app/
  main.py           # entrypoint, mounts frontend estático
  config.py         # env vars (DATABASE_URL, SECRET_KEY, BONUS_CHIPS)
  db.py             # SQLAlchemy models (User, GameHistory)
  auth.py           # bcrypt + JWT
  games/
    slots.py        # RNG criptográfico server-side (secrets)
    blackjack.py    # dealer 17, payout estándar
    roulette.py     # europea 37 números
  routers/
    auth.py         # register / login / me
    games.py        # slots/roulette/blackjack play + leaderboard
frontend/
  index.html        # lobby + registro/login
  slots.html blackjack.html roulette.html
  css/ js/
tests/              # pytest para cada juego + API
render.yaml Dockerfile
```

## API
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/auth/register` | Crea cuenta (100 fichas bonus) |
| POST | `/api/auth/login` | Token JWT |
| GET | `/api/auth/me` | Saldo |
| POST | `/api/games/slots/play` | `{"bet": n}` |
| POST | `/api/games/roulette/play?bet_type=red` | también black/even/odd/low/high/straight |
| POST | `/api/games/blackjack/play` | `{"bet", "player", "dealer"}` |
| GET | `/api/games/leaderboard` | Top 20 |

## Seguridad
- RNG con `secrets` (nunca `random`)
- Resultados y payouts calculados server-side, el cliente jamás envía resultado
- Passwords hasheados con bcrypt, sesiones JWT firmadas con HS256
- Validación de saldo y apuesta en el servidor (anti-cheat)
- Sin payouts, sin monedas reales, sin cripto — solo fichas de demo

## Correr local
```bash
cd backend && pip install -r requirements.txt
uvicorn backend.app.main:app --port 10000
```

## Deploy en Render
1. Push a GitHub
2. Dashboard → New → Blueprint → seleccionar repo → `render.yaml` configura web service docker + disco `data`
3. Variables: `SECRET_KEY` (auto-generada), `DATABASE_URL=sqlite:////data/casino.db`, `BONUS_CHIPS=100`

## Roadmap (phas 2): skill games con dinero real
- Modelo estilo Skillz: competencias de trivia/typing donde el usuario paga entrada y compite
- Legal en MX como "concurso" sin licencia de casino
- Pagos: Mercado Pago (MXN) → Stripe (USD) → USDC