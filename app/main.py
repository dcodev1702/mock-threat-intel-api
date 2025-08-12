import os, asyncio, hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .file_store import load_indicators, load_objects
from .generator import generate_payload, write_payload
from .paging import encode_token, decode_token
from .auth import require_api_key

load_dotenv()

DATA_DIR = os.getenv("DATA_DIR", "/app/data")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

GENERATE_EVERY_SECONDS = int(os.getenv("GENERATE_EVERY_SECONDS", str(3 * 60 * 60)))
GENERATE_ON_START = os.getenv("GENERATE_ON_START", "true").lower() == "true"
MIN_COUNT = int(os.getenv("MIN_COUNT", "10"))
MAX_COUNT = int(os.getenv("MAX_COUNT", "25"))

TAXII_API_ROOT_PATH = os.getenv("TAXII_API_ROOT_PATH", "/taxii2/root")
COLLECTION_ID = os.getenv("COLLECTION_ID", "indicators")
COLLECTION_TITLE = os.getenv("COLLECTION_TITLE", "Synthetic Indicators (STIX 2.1)")
TAXII_INDICATORS_ONLY = os.getenv("TAXII_INDICATORS_ONLY", "false").lower() == "true"
SOURCE_SYSTEM = os.getenv("SOURCE_SYSTEM", "STEELCAGE.AI X-GEN TI PLATFORM")

app = FastAPI(title="Mock TI API", version="2.2.0", description="Mock STIX/TAXII 2.1 Threat Intelligence API")

if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

def _parse_types_param(types_param: Optional[str]) -> Optional[List[str]]:
    if not types_param:
        return None
    parts = [t.strip() for t in types_param.split(",") if t.strip()]
    return parts or None

def _collect_items(since: Optional[str], types: Optional[List[str]]) -> List[Dict[str, Any]]:
    merged = load_objects(DATA_DIR, since=since, limit=10_000, types=types)["stixobjects"]
    return merged

def _page(items: List[Dict[str, Any]], offset: int, page_size: int):
    total = len(items)
    start = max(offset, 0)
    end = min(start + page_size, total)
    slice_ = items[start:end]
    more = end < total
    next_token = encode_token(end) if more else None
    return slice_, total, more, next_token

def _httpdate(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

def _max_timestamp(items: List[Dict[str, Any]]) -> datetime:
    def _get_ts(o: Dict[str, Any]) -> datetime:
        ts = o.get("valid_from") or o.get("created") or "1970-01-01T00:00:00Z"
        try:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                return datetime(1970,1,1,tzinfo=timezone.utc)
    if not items:
        return datetime(1970,1,1,tzinfo=timezone.utc)
    return max(_get_ts(o) for o in items)

def _build_etag(items: List[Dict[str, Any]], extras: str = "") -> str:
    lm = _max_timestamp(items).isoformat()
    import hashlib
    h = hashlib.sha256((lm + "|" + str(len(items)) + "|" + extras).encode("utf-8")).hexdigest()
    return f'W/"{h[:16]}"'

@app.on_event("startup")
async def _start_generator():
    if GENERATE_ON_START:
        payload = generate_payload(min_count=MIN_COUNT, max_count=MAX_COUNT)
        write_payload(DATA_DIR, payload)

    async def _loop():
        while True:
            try:
                await asyncio.sleep(GENERATE_EVERY_SECONDS)
                payload = generate_payload(min_count=MIN_COUNT, max_count=MAX_COUNT)
                write_payload(DATA_DIR, payload)
            except Exception as e:
                print(f"[generator] error: {e}")
                await asyncio.sleep(10)

    asyncio.create_task(_loop())

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/api/v1/indicators", dependencies=[Depends(require_api_key)])
def get_indicators(
    since: Optional[str] = Query(None, description="RFC3339 UTC, e.g., 2025-08-10T00:00:00Z"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Deprecated in favor of page_size"),
    page_size: Optional[int] = Query(None, ge=1, le=1000),
    next: Optional[str] = Query(None, description="Opaque paging token from previous response"),
):
    items = load_indicators(DATA_DIR, since=since, limit=10_000)["stixobjects"]
    if page_size is None:
        page_size = limit or len(items)
    offset = decode_token(next)
    page, total, more, next_token = _page(items, offset, page_size)
    return JSONResponse(content={
        "count": len(page),
        "total": total,
        "more": more,
        "next": next_token,
        "sourcesystem": SOURCE_SYSTEM,
        "stixobjects": page
    })

@app.get("/api/v1/collections", dependencies=[Depends(require_api_key)])
def list_collections():
    return {"collections": [{
        "id": COLLECTION_ID,
        "title": COLLECTION_TITLE,
        "type": "mixed",
        "can_read": True,
        "can_write": False
    }]}

@app.get("/api/v1/collections/{collection_id}/objects", dependencies=[Depends(require_api_key)])
def get_collection_objects(
    collection_id: str,
    since: Optional[str] = Query(None, description="RFC3339 UTC, e.g., 2025-08-10T00:00:00Z"),
    types: Optional[str] = Query(None, description="Comma-separated STIX types, e.g., indicator,attack-pattern"),
    page_size: int = Query(100, ge=1, le=1000),
    next: Optional[str] = Query(None),
):
    if collection_id != COLLECTION_ID:
        raise HTTPException(status_code=404, detail="Collection not found")
    type_list = _parse_types_param(types)
    items = _collect_items(since, types=type_list)
    offset = decode_token(next)
    page, total, more, next_token = _page(items, offset, page_size)
    return {
        "objects": page,
        "sourcesystem": SOURCE_SYSTEM,
        "total": total,
        "more": more,
        "next": next_token
    }

@app.get("/taxii2/", summary="TAXII Discovery", dependencies=[Depends(require_api_key)])
def taxii_discovery(request: Request):
    base = str(request.base_url).rstrip("/")
    api_root = f"{base}{TAXII_API_ROOT_PATH}"
    return JSONResponse(content={
        "title": "Mock TAXII Server",
        "description": "Discovery document for the mock TAXII 2.1 API",
        "default": api_root,
        "api_roots": [api_root]
    }, media_type="application/taxii+json")

@app.get("/taxii2/root/collections", summary="TAXII Collections", dependencies=[Depends(require_api_key)])
def taxii_collections():
    return JSONResponse(content={
        "collections": [{
            "id": COLLECTION_ID,
            "title": COLLECTION_TITLE,
            "description": "Synthetic STIX 2.1 content generated inside the container.",
            "can_read": True,
            "can_write": False,
            "media_types": ["application/stix+json;version=2.1"]
        }]
    }, media_type="application/taxii+json")

@app.get("/taxii2/root/collections/{collection_id}/objects", summary="TAXII Objects", dependencies=[Depends(require_api_key)])
def taxii_objects(
    request: Request,
    collection_id: str,
    added_after: Optional[str] = Query(None, description="RFC3339 timestamp; filters by valid_from/created"),
    limit: int = Query(100, ge=1, le=1000),
    next: Optional[str] = Query(None, description="Opaque paging token"),
    types: Optional[str] = Query(None, description="Comma-separated STIX types, e.g., indicator,attack-pattern"),
):
    if collection_id != COLLECTION_ID:
        raise HTTPException(status_code=404, detail="Collection not found")
    type_list = [ "indicator" ] if os.getenv("TAXII_INDICATORS_ONLY", "false").lower() == "true" else _parse_types_param(types)
    items = _collect_items(added_after, types=type_list)
    offset = decode_token(next)
    page, total, more, next_token = _page(items, offset, limit)

    def _max_ts(items):
        if not items:
            return datetime(1970,1,1,tzinfo=timezone.utc)
        vals = []
        for o in items:
            ts = o.get("valid_from") or o.get("created") or "1970-01-01T00:00:00Z"
            try:
                vals.append(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc))
            except ValueError:
                try:
                    vals.append(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc))
                except ValueError:
                    vals.append(datetime(1970,1,1,tzinfo=timezone.utc))
        return max(vals)

    last_modified = _max_ts(items)
    extras = f"types={','.join(type_list) if type_list else 'all'};total={total}"
    import hashlib
    etag = f'W/"{hashlib.sha256((last_modified.isoformat() + "|" + str(len(items)) + "|" + extras).encode()).hexdigest()[:16]}"'
    last_modified_http = last_modified.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    inm = request.headers.get("if-none-match")
    ims = request.headers.get("if-modified-since")
    if inm and inm == etag:
        return Response(status_code=304, headers={"ETag": etag, "Last-Modified": last_modified_http})
    if ims:
        try:
            ims_dt = datetime.strptime(ims, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
            if last_modified <= ims_dt:
                return Response(status_code=304, headers={"ETag": etag, "Last-Modified": last_modified_http})
        except Exception:
            pass

    return JSONResponse(
        content={
            "objects": page,
            "sourcesystem": SOURCE_SYSTEM,
            "more": more,
            "next": next_token
        },
        media_type="application/taxii+json",
        headers={"ETag": etag, "Last-Modified": last_modified_http}
    )
