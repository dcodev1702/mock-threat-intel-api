# Mock STIX/TAXII 2.1 TI API (Indicators + Mixed Types)

- FastAPI app with in-container generator (every 3 hours by default).
- Auth via `API_KEYS` (X-API-Key or Bearer).
- Flat, collection, and TAXII endpoints.
- Cursor paging (`next`), `types=` filters, and TAXII `ETag`/`Last-Modified`.
- **Top-level `sourcesystem` field** included in list responses.

## Build the containerized Mock TI API Endpoint solution
```python
docker build -t mock-sc-xgen-ti-api-alpine .
```
 Run the continaerized Mock TI API Endpoint solution 
```python
docker run -d --name mock-sc-xgen-ti-api -p 80:8000 -v $PWD/data:/app/data --env-file .\.env  mock-sc-xgen-ti-api-alpine:latest
```
Query SC X-GEN TI API Endpoint (w/ auth)
```python
curl -H "X-API-Key: QUxMIFVSIEJBU0UgQU5EIEFQSSdTIEFSRSBCRUxPTkcgVE8gVVMh" http://192.168.10.27/api/v1/indicators | jq .
```

## Endpoints
- `GET /healthz`
- `GET /api/v1/indicators?since=...&page_size=...&next=...`
  - Response: `{ count, total, more, next, sourcesystem, stixobjects }`
- `GET /api/v1/collections`
- `GET /api/v1/collections/{id}/objects?since=...&types=indicator,attack-pattern&page_size=...&next=...`
  - Response: `{ objects, sourcesystem, total, more, next }`
- `GET /taxii2/`
- `GET /taxii2/root/collections`
- `GET /taxii2/root/collections/{id}/objects?limit=...&added_after=...&types=...&next=...`
  - Response (`application/taxii+json`): `{ objects, sourcesystem, more, next }` with `ETag`, `Last-Modified`

## Env
See `.env.example`. Notable:
- `API_KEYS` — comma-separated keys (enables auth when set)
- `GENERATE_EVERY_SECONDS` — default 10800 (3h)
- `TAXII_INDICATORS_ONLY` — force TAXII to indicators only
- `SOURCE_SYSTEM` — defaults to `STEELCAGE.AI X-GEN TI PLATFORM`
