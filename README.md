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
See `.env`. Notable:
- `API_KEYS` — comma-separated keys (enables auth when set)
- `GENERATE_EVERY_SECONDS` — default 10800 (3h)
- `TAXII_INDICATORS_ONLY` — force TAXII to indicators only
- `SOURCE_SYSTEM` — defaults to `STEELCAGE.AI X-GEN TI PLATFORM`
  * This is REQUIRED when Uploading TI to Sentinels Preview API

  
[Microsoft Sentinel TI Upload Preview API](https://learn.microsoft.com/en-us/azure/sentinel/stix-objects-api)

<img width="1065" height="427" alt="image" src="https://github.com/user-attachments/assets/909c8d6b-3025-469b-af07-988689892f22" />

## MOCK TI REST API ENDPOINT
-`Generate synthetic TI indicators and provide a mock TI REST API endpoint to pull JSON array of stixobjects (indicators) from.`
<img width="893" height="1192" alt="image" src="https://github.com/user-attachments/assets/97b5a238-6408-475d-bc76-e17fa4efd17b" />

<img width="2148" height="1039" alt="image" src="https://github.com/user-attachments/assets/083fde62-9bc7-43df-b082-cd697f09f643" />

