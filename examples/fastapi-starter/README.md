# fastapi-starter — minimal FastAPI service

A tiny FastAPI service that accepts orders, writes them to a Postgres database via SQLAlchemy, and enqueues a receipt email through FastAPI's `BackgroundTasks`. Migrations are applied on startup. Three flows ship with this fixture: one user flow, one internal flow, one build flow.

## Layout

```
app/
├── main.py                # FastAPI app, startup event runs migrations
├── routes/
│   ├── __init__.py
│   └── orders.py          # POST /v1/orders
├── db/
│   ├── __init__.py
│   ├── session.py         # async engine + session factory
│   └── migrations.py      # bootstrap migrations
└── tasks/
    ├── __init__.py
    └── receipts.py        # send_receipt() background worker
```

## Routes

```python
# app/routes/orders.py:24
@app.post("/v1/orders", response_model=OrderOut, status_code=201)
async def create_order(
    payload: OrderIn,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Persist the order row, then queue the receipt task."""
    order_id = await _insert_order(session, payload)
    background_tasks.add_task(send_receipt, order_id)
    return {"id": order_id, "status": "created"}
```

## SQL

```python
# app/routes/orders.py:48
async def _insert_order(session: AsyncSession, payload: OrderIn) -> str:
    order_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO orders (id, customer_id, amount_cents, currency, "
            "status, created_at) VALUES (:id, :cid, :amt, :cur, 'new', now())"
        ),
        {
            "id": order_id,
            "cid": payload.customer_id,
            "amt": payload.amount_cents,
            "cur": payload.currency,
        },
    )
    await session.commit()
    return order_id
```

## Background task

```python
# app/tasks/receipts.py:18
async def send_receipt(order_id: str) -> None:
    """Render the receipt email and post it to the SMTP relay."""
    order = await _load_order(order_id)
    body = _render_template("receipt.html", order=order)
    async with httpx.AsyncClient(timeout=8.0) as client:
        await client.post(
            f"{settings.smtp_relay_url}/v1/messages",
            headers={"Authorization": f"Bearer {settings.smtp_relay_token}"},
            json={
                "to": order.email,
                "subject": f"Receipt for order {order.id}",
                "html": body,
            },
        )
```

## Startup migration

```python
# app/main.py:32
@app.on_event("startup")
async def _on_startup() -> None:
    """Apply Alembic migrations once at boot."""
    await apply_migrations()  # app/db/migrations.py:14
```

## How the flows.json cites this README

Every step in `flows.json` carries a `note` of the form `src=app/.../file.py:NN`. The line numbers point at the snippets above. A reader can grep this README for the path and find the corresponding code block.
