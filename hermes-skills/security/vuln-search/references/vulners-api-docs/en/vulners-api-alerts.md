# Alerts

Manage automated notifications for new or updated records — add, list, modify subscriptions, or use **polling** to retrieve updates on demand.

**Open interactive specs:**
- [Open Redoc (interactive)](https://docs.vulners.com/docs/api/redoc.html)
- [Open Swagger (interactive)](https://docs.vulners.com/docs/api/swagger.html)

---

## How it works

Alerts are built around **subscriptions** — saved search queries and delivery settings. Subscription evaluation + delivery happen on the schedule defined by `crontab`.

### Delivery methods

| Method      | How it works                                                                                                                      |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Email**   | Scheduled delivery (HTML or JSON) according to a cron expression.                                                                 |
| **Webhook** | Scheduled HTTP POST to your endpoint according to crontab (up to every minute).                                                   |
| **Polling** | Results are stored on Vulners side; your app fetches them via a pull endpoint.                                                    |

### Timestamp sources

The `timestamp_source` parameter defines which timestamp Vulners checks to decide if a bulletin is "new" or "updated".

| timestamp_source value            | Triggers when…                                            |
| -------------------------------- | --------------------------------------------------------- |
| published                        | Bulletin is newly published.                              |
| modified                         | Any core bulletin field changed (default).                |
| timestamps.updated               | Core content refreshed.                                   |
| timestamps.enriched              | AI enrichments, links, or correlations added.             |
| timestamps.metricsUpdated        | CVSS, EPSS, AI score recalculated.                        |
| timestamps.webApplicabilityUpdated | Web-applicability flags changed.                        |
| timestamps.reviewed              | Review/QA pass completed.                                 |

### Query types

| Type         | Meaning                                      |
| ------------ | -------------------------------------------- |
| query        | Classic Lucene query                         |
| software     | CPE-based software query                     |
| host/generic | Generic host (software + optional app/OS/hw) |
| host/linux   | Linux host (OS + package list)               |
| host/windows | Windows host (OS + KB list + packages)       |

---

## Subscriptions (v4)

### Create subscription

**Auth**: `X-Api-Key` header required.

**Query:** `POST /api/v4/subscriptions/create/`

```bash
curl -X POST "https://vulners.com/api/v4/subscriptions/create/" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Critical Linux vulns",
    "query": { "type": "query", "query": "cvss:[7 TO *] AND family:cve" },
    "delivery": { "type": "webhook", "address": "https://example.com/webhook", "crontab": "0 * * * *" },
    "bulletin_fields": ["id", "title", "description", "cvss"],
    "timestamp_source": "modified",
    "is_active": true,
    "send_empty_result": false
  }'
```

### List subscriptions

**Query:** `GET /api/v4/subscriptions/list/`

```bash
curl -G "https://vulners.com/api/v4/subscriptions/list/" -H "X-Api-Key: YOUR_API_KEY"
```

### Get subscription

**Query:** `GET /api/v4/subscriptions/get/`

```bash
curl -G "https://vulners.com/api/v4/subscriptions/get/" -H "X-Api-Key: YOUR_API_KEY" \
  --data-urlencode "subscription_id=subscription-uuid"
```

### Update subscription

**Query:** `PUT /api/v4/subscriptions/update/`

```bash
curl -X PUT "https://vulners.com/api/v4/subscriptions/update/" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "subscription-uuid",
    "name": "Updated name",
    "query": { "type": "query", "query": "package:nginx severity:high" },
    "delivery": { "type": "webhook", "address": "https://example.com/webhook", "crontab": "*/30 * * * *" },
    "sendEmptyResult": "true"
  }'
```

### Delete subscription

**Query:** `DELETE /api/v4/subscriptions/delete/`

```bash
curl -X DELETE "https://vulners.com/api/v4/subscriptions/delete/?id=subscription-uuid" \
  -H "X-Api-Key: YOUR_API_KEY"
```

---

## Polling (v3)

### Add polling subscription

**Query:** `POST /api/v3/subscriptions/addWebhookSubscription/`

```bash
curl -XPOST https://vulners.com/api/v3/subscriptions/addWebhookSubscription/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"query": "viewCount:[50 TO *] order:viewCount last 8 days"}'
```

**Python:**
```python
new_webhook = vulners_api.add_webhook("viewCount:[50 TO *] order:viewCount last 8 days")
```

### List polling subscriptions

**Query:** `GET /api/v3/subscriptions/listWebhookSubscriptions/`

```bash
curl -G "https://vulners.com/api/v3/subscriptions/listWebhookSubscriptions/" -H "X-Api-Key: YOUR_API_KEY"
```

### Enable/Disable polling

**Query:** `POST /api/v3/subscriptions/enableWebhookSubscription/`

```bash
curl -XPOST https://vulners.com/api/v3/subscriptions/enableWebhookSubscription/ \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"subscriptionid": "{subscription id}", "active": false}'
```

### Read polling subscription

**Query:** `GET /api/v3/subscriptions/webhook/`

```bash
curl -G "https://vulners.com/api/v3/subscriptions/webhook/" \
  -H "X-Api-Key: YOUR_API_KEY" \
  --data-urlencode "subscriptionid={subscription-id}" \
  --data-urlencode "newest_only=false"
```

---

## Email notifications

### List email subscriptions

**Query:** `GET /api/v3/subscriptions/listEmailSubscriptions/`

```bash
curl -X GET 'https://vulners.com/api/v3/subscriptions/listEmailSubscriptions/' \
  -H "X-Api-Key: YOUR_API_KEY"
```

### Add email subscription

**Query:** `POST /api/v3/subscriptions/addEmailSubscription/`

```bash
curl -X POST 'https://vulners.com/api/v3/subscriptions/addEmailSubscription/' \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "viewCount:[50 TO *] order:viewCount last 5 days",
    "email": "<EMAIL-REDACTED>",
    "format": "html",
    "crontab": "0 0 * * *",
    "query_type": "lucene"
  }'
```

### Edit email subscription

**Query:** `POST /api/v3/subscriptions/editEmailSubscription/`

```bash
curl -X POST 'https://vulners.com/api/v3/subscriptions/editEmailSubscription/' \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "subscriptionid": "{subscription id}",
    "format": "json",
    "crontab": "0 1 * * *",
    "active": "false"
  }'
```

### Delete email subscription

**Query:** `POST /api/v3/subscriptions/removeEmailSubscription/`

```bash
curl -X POST 'https://vulners.com/api/v3/subscriptions/removeEmailSubscription/' \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"subscriptionid": "{subscription id}"}'
```
