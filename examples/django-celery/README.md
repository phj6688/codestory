# django-celery — Django 5 + Celery 5 + Celery beat

A small Django project with a synchronous order-create view, a Celery worker that sends receipts and runs an inventory reconciliation, and a Celery beat schedule that fires a nightly purge. Five flows ship with this fixture.

## Layout

```
orders_project/
├── settings.py            # CELERY_*, DATABASES, INSTALLED_APPS
├── celery.py              # Celery app bootstrap
└── urls.py                # url routes
orders/
├── views.py               # order_create_view, order_detail_view
├── tasks.py               # @shared_task definitions
├── models.py              # Order, Receipt, StockAdjustment
└── urls.py
```

## View

```python
# orders/views.py:24
def order_create_view(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    form = OrderForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)
    order = form.save()
    send_receipt.delay(order.id)
    reconcile_inventory.delay(order.id)
    return JsonResponse({"id": str(order.id)}, status=201)
```

## Tasks

```python
# orders/tasks.py:18
@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_receipt(self, order_id: str) -> None:
    order = Order.objects.get(pk=order_id)
    body = render_to_string("emails/receipt.html", {"order": order})
    try:
        smtp.post(order.email, subject=f"Receipt {order.id}", html=body)
    except smtp.RelayError as exc:
        raise self.retry(exc=exc)
    Receipt.objects.create(order=order, sent_at=timezone.now())
```

```python
# orders/tasks.py:44
@shared_task
def reconcile_inventory(order_id: str) -> None:
    order = Order.objects.select_related("item").get(pk=order_id)
    StockAdjustment.objects.create(
        item=order.item,
        delta=-order.quantity,
        reason=f"order:{order.id}",
    )
```

```python
# orders/tasks.py:66
@shared_task
def nightly_purge() -> None:
    cutoff = timezone.now() - timedelta(days=90)
    Order.objects.filter(status="cancelled", created_at__lt=cutoff).delete()
```

## Celery beat schedule

```python
# orders_project/settings.py:88
CELERY_BEAT_SCHEDULE = {
    "nightly-purge": {
        "task": "orders.tasks.nightly_purge",
        "schedule": crontab(hour=3, minute=15),
    },
}
```

## Celery app

```python
# orders_project/celery.py:12
app = Celery("orders_project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

## How the flows.json cites this README

Every step in `flows.json` carries a `note` of the form `src=orders/.../*.py:NN` or `src=orders_project/.../*.py:NN`. The line numbers point at the snippets above. A reader can grep this README for the path and find the matching code block.
