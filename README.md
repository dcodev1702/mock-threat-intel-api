# Mock STIX/TAXII v2.1 TI GENERATION & REST API 

- FastAPI app with in-container generator (every 3 hours by default).
- Auth via `API_KEYS` (X-API-Key or Bearer).
- Flat, collection, and TAXII endpoints.
- Cursor paging (`next`), `types=` filters, and TAXII `ETag`/`Last-Modified`.
- **Top-level `sourcesystem` field** included in list responses.

## Assumptions
- You have access docker
- You have basic familiarity with running containerized workloads
  * [Docker Crash Course](https://www.youtube.com/watch?v=pg19Z8LL06w)

### Build the containerized Mock TI Generation & API Endpoint solution
```python
docker build -t mock-sc-xgen-ti-api-alpine .
```
### Run the continaerized Mock TI API Endpoint solution <br/>
 -`Synthetic Threat Indicators are generated at boot and every 3 hours (default)`
```python
docker run -d --name mock-sc-xgen-ti-api -p 80:8000 -v $PWD/data:/app/data --env-file .\.env  mock-sc-xgen-ti-api-alpine:latest
```
### Query SC X-GEN TI API Endpoint (w/ auth) <br/>
-`Default API KEY is provided via .env (set it to whatever you want)`

```python
curl -s -H "X-API-Key: QUxMIFVSIEJBU0UgQU5EIEFQSSdTIEFSRSBCRUxPTkcgVE8gVVMh" http://192.168.10.27/api/v1/indicators | jq .
```

## Endpoints
- `GET /healthz`
  - Auth not required to get health status  
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
  * This is REQUIRED when Uploading TI to Microsoft Sentinels TI Preview REST API


<img width="1065" height="427" alt="image" src="https://github.com/user-attachments/assets/909c8d6b-3025-469b-af07-988689892f22" />

## MOCK TI REST API ENDPOINT
-`Generate synthetic TI indicators and provide a mock TI REST API endpoint to pull JSON array of stixobjects (indicators) from.` <br/>
```python
curl -s -H "X-API-Key: QUxMIFVSIEJBU0UgQU5EIEFQSSdTIEFSRSBCRUxPTkcgVE8gVVMh" http://192.168.10.27/api/v1/indicators | jq .`
```
<img width="893" height="1192" alt="image" src="https://github.com/user-attachments/assets/97b5a238-6408-475d-bc76-e17fa4efd17b" />

## Transmit TI JSON [stixobjects] from Mock REST API to Sentinel's TI Upload API (Preview) for enhanced Threat Detection
[Microsoft Sentinel TI Upload Preview API](https://learn.microsoft.com/en-us/azure/sentinel/stix-objects-api)
  * This assumes & requires the following:
    * An Azure Subscription
    * Priviledged Access
    * A Sentinel Enabled Log Analytics Workspace (LAW)
    * Application Registration & Secret/Cert
      * Microsoft Sentinel Contributor RBAC assigned to the LAW via IAM
<img width="2148" height="1039" alt="image" src="https://github.com/user-attachments/assets/083fde62-9bc7-43df-b082-cd697f09f643" />

