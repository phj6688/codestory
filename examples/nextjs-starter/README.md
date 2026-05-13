# nextjs-starter — Next.js 15 App Router with a Stripe webhook

A minimal Next.js 15 App Router project that lists orders on a server-rendered page, exposes a JSON API route for clients, and verifies an incoming Stripe webhook. Three flows ship with this fixture: one page render, one API write, one webhook receive.

## Layout

```
app/
├── layout.tsx
├── orders/
│   ├── page.tsx           # server-rendered orders list
│   └── new/page.tsx       # client form posting to the API
└── api/
    ├── orders/
    │   └── route.ts       # POST /api/orders
    └── webhooks/
        └── stripe/
            └── route.ts   # POST /api/webhooks/stripe (signature validated)
lib/
├── stripe.ts              # Stripe client + signature helper
└── db.ts                  # Postgres client (postgres-js)
```

## Server page

```tsx
// app/orders/page.tsx:12
export default async function OrdersPage() {
  const rows = await sql`
    SELECT id, customer_id, amount_cents, currency, created_at
    FROM orders
    ORDER BY created_at DESC
    LIMIT 50
  `;
  return (
    <main>
      <h1>Recent orders</h1>
      <OrderList rows={rows} />
    </main>
  );
}
```

## API route

```ts
// app/api/orders/route.ts:18
export async function POST(req: NextRequest) {
  const body = OrderCreate.parse(await req.json());
  const [{ id }] = await sql<{ id: string }[]>`
    INSERT INTO orders (customer_id, amount_cents, currency, status)
    VALUES (${body.customerId}, ${body.amountCents}, ${body.currency}, 'new')
    RETURNING id
  `;
  return NextResponse.json({ id }, { status: 201 });
}
```

## Stripe webhook receiver

```ts
// app/api/webhooks/stripe/route.ts:14
export async function POST(req: NextRequest) {
  const signature = req.headers.get("stripe-signature");
  if (!signature) {
    return NextResponse.json({ error: "missing stripe-signature" }, { status: 400 });
  }
  const raw = await req.text();
  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(raw, signature, env.STRIPE_WEBHOOK_SECRET);
  } catch (e) {
    return NextResponse.json({ error: "invalid signature" }, { status: 400 });
  }

  if (event.type === "payment_intent.succeeded") {
    const pi = event.data.object as Stripe.PaymentIntent;
    await sql`UPDATE orders SET status = 'paid' WHERE stripe_pi_id = ${pi.id}`;
  }
  return NextResponse.json({ received: true });
}
```

## How the flows.json cites this README

Every step in `flows.json` carries a `note` of the form `src=app/.../route.ts:NN` or `src=app/.../page.tsx:NN`. The line numbers point at the snippets above. A reader can grep this README for the path and find the matching block.
