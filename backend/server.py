from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import secrets
import asyncio
import uuid
import re
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import jwt
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '').strip().lower()
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
JWT_SECRET = os.environ.get('JWT_SECRET', 'change-me')
PUBLIC_URL = os.environ.get('PUBLIC_URL', '').rstrip('/')

MP_API = "https://api.mercadopago.com"
IP_LINK_URLS = [
    "https://api.infinitepay.io/invoices/public/checkout/links",
    "https://api.checkout.infinitepay.io/links",
]
IP_CHECK_URLS = [
    "https://api.infinitepay.io/invoices/public/checkout/payment_check",
    "https://api.checkout.infinitepay.io/payment_check",
]

app = FastAPI()
api = APIRouter(prefix="/api")
logger = logging.getLogger("sorte")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def now():
    return datetime.now(timezone.utc)


def iso(d):
    return d.isoformat() if isinstance(d, datetime) else d


# ---------------- Models ----------------
class LoginIn(BaseModel):
    email: str
    password: str


class RaffleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    goal: Optional[float] = None
    price: Optional[float] = None
    default_gateway: Optional[str] = None


class ExtraIn(BaseModel):
    amount: float


class KeysIn(BaseModel):
    mp_access_token: Optional[str] = None
    infinitepay_handle: Optional[str] = None


class OrderIn(BaseModel):
    name: str
    whatsapp: str
    quantity: int = Field(ge=1, le=10000)
    gateway: str


class ManualIn(BaseModel):
    name: str
    whatsapp: str = ""
    quantity: int = Field(ge=1, le=10000)


# ---------------- Auth ----------------
def make_token():
    return jwt.encode({"sub": ADMIN_EMAIL, "exp": now() + timedelta(days=7)}, JWT_SECRET, algorithm="HS256")


async def require_admin(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Não autorizado")
    try:
        jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Sessão expirada")
    return True


@api.post("/auth/login")
async def login(body: LoginIn):
    if body.email.strip().lower() != ADMIN_EMAIL or not secrets.compare_digest(body.password, ADMIN_PASSWORD):
        raise HTTPException(401, "Email ou senha inválidos")
    return {"token": make_token(), "email": ADMIN_EMAIL}


@api.get("/auth/me")
async def me(_=Depends(require_admin)):
    return {"email": ADMIN_EMAIL}


# ---------------- Helpers ----------------
async def get_active_raffle():
    r = await db.raffles.find_one({"status": {"$in": ["active", "drawn", "drawing"]}}, {"_id": 0}, sort=[("created_at", -1)])
    if not r:
        r = {
            "id": str(uuid.uuid4()), "title": "R$ 10.000 no PIX", "description": "Concorra!",
            "image_url": "https://images.unsplash.com/photo-1677522375387-4d41265a98c4?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200",
            "goal": 30.0, "price": 10.0, "default_gateway": "mercadopago", "status": "active",
            "manual_extra": 0.0, "next_coupon": 1, "draw_at": None, "created_at": iso(now()),
        }
        await db.raffles.insert_one(dict(r))
    return r


async def get_settings():
    s = await db.settings.find_one({"id": "keys"}, {"_id": 0})
    return s or {"id": "keys", "mp_access_token": "", "infinitepay_handle": ""}


async def raffle_stats(r):
    paid = await db.orders.find({"raffle_id": r["id"], "status": "paid"}, {"_id": 0, "amount": 1, "coupons": 1, "whatsapp": 1, "name": 1}).to_list(100000)
    amount = sum(o.get("amount", 0) for o in paid)
    coupons = sum(len(o.get("coupons", [])) for o in paid)
    people = len({(re.sub(r"\D", "", o.get("whatsapp") or ""), (o.get("name") or "").strip().lower()) for o in paid})
    total = amount + float(r.get("manual_extra", 0) or 0)
    goal = float(r.get("goal") or 0)
    pct = min(100, int(round(total / goal * 100))) if goal > 0 else 0
    return {"raised": round(amount, 2), "progress_total": round(total, 2), "coupons": coupons, "participants": people, "percent": pct}


def public_raffle(r, stats):
    keys = ["id", "title", "description", "image_url", "goal", "price", "default_gateway", "status", "created_at", "winner", "draw_id", "draw_at"]
    out = {k: r.get(k) for k in keys}
    out.update(stats)
    out["server_now"] = iso(now())
    return out


DRAW_DELAY_SECONDS = int(os.environ.get("DRAW_DELAY_SECONDS", "180"))


async def sync_goal(raffle_id):
    """Schedule the draw 3 minutes after the goal hits 100%; cancel if it drops below."""
    r = await db.raffles.find_one({"id": raffle_id}, {"_id": 0})
    if not r or r.get("status") != "active":
        return
    st = await raffle_stats(r)
    reached = float(r.get("goal") or 0) > 0 and st["progress_total"] >= float(r["goal"]) and st["coupons"] > 0
    if reached and not r.get("draw_at"):
        await db.raffles.update_one({"id": raffle_id, "draw_at": {"$in": [None, ""]}},
                                    {"$set": {"draw_at": iso(now() + timedelta(seconds=DRAW_DELAY_SECONDS))}})
    elif not reached and r.get("draw_at"):
        await db.raffles.update_one({"id": raffle_id}, {"$set": {"draw_at": None}})


async def perform_draw(r):
    """Atomically lock raffle and draw a winner among paid coupons of THIS raffle only."""
    locked = await db.raffles.find_one_and_update({"id": r["id"], "status": "active"}, {"$set": {"status": "drawing"}}, projection={"_id": 0})
    if not locked:
        raise HTTPException(400, "Este sorteio já foi realizado. Inicie um novo sorteio.")
    paid = await db.orders.find({"raffle_id": r["id"], "status": "paid"}, {"_id": 0}).to_list(100000)
    pool = [{"name": o["name"], "coupon": c} for o in paid for c in o.get("coupons", [])]
    if not pool:
        await db.raffles.update_one({"id": r["id"]}, {"$set": {"status": "active", "draw_at": None}})
        raise HTTPException(400, "Nenhum cupom pago para sortear")
    rng = secrets.SystemRandom()
    winner = rng.choice(pool)
    win_index = 52
    # reel built only from real paid coupons of this raffle, cycling through all of them
    shuffled = pool[:]
    rng.shuffle(shuffled)
    seq = [shuffled[i % len(shuffled)] for i in range(win_index + 8)]
    seq[win_index] = winner
    stats = await raffle_stats(r)
    draw = {"id": str(uuid.uuid4()), "raffle_id": r["id"], "title": r["title"], "image_url": r.get("image_url"),
            "winner": winner, "sequence": seq, "win_index": win_index, "participants": stats["participants"],
            "total_coupons": stats["coupons"], "amount": stats["raised"], "created_at": iso(now())}
    await db.draws.insert_one(dict(draw))
    await db.raffles.update_one({"id": r["id"]}, {"$set": {"status": "drawn", "winner": winner, "draw_id": draw["id"]}})
    return draw


async def auto_draw_tick():
    r = await db.raffles.find_one({"status": "active", "draw_at": {"$nin": [None, ""]}}, {"_id": 0})
    if r and r["draw_at"] <= iso(now()):
        try:
            await perform_draw(r)
            logger.info("Auto draw executed for raffle %s", r["id"])
        except HTTPException as e:
            logger.warning("Auto draw skipped: %s", e.detail)


async def assign_coupons(order_id):
    """Atomically mark order paid and assign sequential coupon numbers."""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order or order.get("status") == "paid":
        return order
    res = await db.orders.update_one({"id": order_id, "status": {"$ne": "paid"}}, {"$set": {"status": "paid", "paid_at": iso(now())}})
    if res.modified_count == 0:
        return await db.orders.find_one({"id": order_id}, {"_id": 0})
    qty = int(order["quantity"])
    r = await db.raffles.find_one_and_update({"id": order["raffle_id"]}, {"$inc": {"next_coupon": qty}}, projection={"_id": 0})
    start = int(r.get("next_coupon", 1))
    coupons = [f"{n:05d}" for n in range(start, start + qty)]
    await db.orders.update_one({"id": order_id}, {"$set": {"coupons": coupons}})
    await sync_goal(order["raffle_id"])
    return await db.orders.find_one({"id": order_id}, {"_id": 0})


def public_order(o):
    keys = ["id", "name", "quantity", "amount", "gateway", "status", "coupons", "created_at",
            "pix_qr_code", "pix_qr_base64", "ticket_url", "checkout_url"]
    return {k: o.get(k) for k in keys}


# ---------------- Public ----------------
@api.get("/")
async def root():
    return {"message": "SorteZeferius API"}


@api.get("/raffle")
async def raffle():
    r = await get_active_raffle()
    if r.get("status") == "active":
        await sync_goal(r["id"])
        r = await get_active_raffle()
    return public_raffle(r, await raffle_stats(r))


@api.get("/history")
async def history():
    items = await db.draws.find({}, {"_id": 0, "sequence": 0}).sort("created_at", -1).to_list(100)
    return items


@api.get("/draws/latest")
async def latest_draw():
    d = await db.draws.find_one({}, {"_id": 0}, sort=[("created_at", -1)])
    return d or {}


@api.get("/draws/{draw_id}")
async def get_draw(draw_id: str):
    d = await db.draws.find_one({"id": draw_id}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Sorteio não encontrado")
    return d


async def mp_create(order, token, r):
    digits = re.sub(r"\D", "", order["whatsapp"]) or "pix"
    payer_email = f"cliente{digits}@sortezeferius.com.br"
    first = order["name"].split(" ")[0]
    body = {
        "transaction_amount": round(float(order["amount"]), 2),
        "description": f"{r['title']} - {order['quantity']} cupom(ns)",
        "payment_method_id": "pix",
        "external_reference": order["id"],
        "payer": {"email": payer_email, "first_name": first},
    }
    if PUBLIC_URL.startswith("https://"):
        body["notification_url"] = f"{PUBLIC_URL}/api/webhooks/mercadopago"
    async with httpx.AsyncClient(timeout=30) as c:
        resp = await c.post(f"{MP_API}/v1/payments", json=body,
                            headers={"Authorization": f"Bearer {token}", "X-Idempotency-Key": order["id"]})
    data = resp.json()
    if resp.status_code >= 300:
        logger.error("MP error %s %s", resp.status_code, data)
        raise HTTPException(502, f"Mercado Pago: {data.get('message', 'erro ao gerar PIX')}")
    tx = (data.get("point_of_interaction") or {}).get("transaction_data") or {}
    return {"mp_payment_id": str(data.get("id")), "pix_qr_code": tx.get("qr_code"),
            "pix_qr_base64": tx.get("qr_code_base64"), "ticket_url": tx.get("ticket_url")}


async def ip_create(order, handle, r, origin):
    base = PUBLIC_URL or origin or ""
    body = {
        "handle": handle.lstrip("$"),
        "order_nsu": order["id"],
        "items": [{"quantity": int(order["quantity"]), "price": int(round(float(r["price"]) * 100)),
                   "description": f"Cupom - {r['title']}"[:100]}],
        "customer": {"name": order["name"], "phone_number": "+55" + re.sub(r"\D", "", order["whatsapp"])},
    }
    if base:
        body["redirect_url"] = f"{base}/pagamento/retorno"
    if base.startswith("https://"):
        body["webhook_url"] = f"{base}/api/webhooks/infinitepay"
    last = None
    async with httpx.AsyncClient(timeout=30) as c:
        for url in IP_LINK_URLS:
            try:
                resp = await c.post(url, json=body)
                data = resp.json() if resp.content else {}
                if resp.status_code < 300 and (data.get("url") or data.get("link")):
                    return {"checkout_url": data.get("url") or data.get("link"), "ip_slug": data.get("slug")}
                last = f"{resp.status_code} {data}"
            except Exception as e:  # noqa
                last = str(e)
    logger.error("InfinitePay error %s", last)
    raise HTTPException(502, "InfinitePay: não foi possível gerar o link de pagamento")


@api.post("/orders")
async def create_order(body: OrderIn, request: Request):
    name = body.name.strip()
    phone = re.sub(r"\D", "", body.whatsapp)
    if len(name) < 2:
        raise HTTPException(400, "Informe seu nome")
    if len(phone) < 10:
        raise HTTPException(400, "Informe um WhatsApp válido")
    if body.gateway not in ("mercadopago", "infinitepay"):
        raise HTTPException(400, "Gateway inválido")
    r = await get_active_raffle()
    if r.get("status") != "active":
        raise HTTPException(400, "Este sorteio já foi encerrado")
    if r.get("draw_at"):
        raise HTTPException(400, "Meta atingida! As vendas estão encerradas e o sorteio vai começar.")
    s = await get_settings()
    order = {
        "id": str(uuid.uuid4()), "raffle_id": r["id"], "name": name, "whatsapp": body.whatsapp.strip(),
        "quantity": body.quantity, "amount": round(body.quantity * float(r["price"]), 2),
        "gateway": body.gateway, "status": "pending", "coupons": [], "source": "site", "created_at": iso(now()),
    }
    if body.gateway == "mercadopago":
        if not s.get("mp_access_token"):
            raise HTTPException(400, "Mercado Pago não configurado. Contate o organizador.")
        order.update(await mp_create(order, s["mp_access_token"], r))
    else:
        if not s.get("infinitepay_handle"):
            raise HTTPException(400, "InfinitePay não configurado. Contate o organizador.")
        origin = request.headers.get("origin", "")
        order.update(await ip_create(order, s["infinitepay_handle"], r, origin))
    await db.orders.insert_one(dict(order))
    return public_order(order)


async def refresh_mp(order):
    s = await get_settings()
    if not order.get("mp_payment_id") or not s.get("mp_access_token"):
        return order
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            resp = await c.get(f"{MP_API}/v1/payments/{order['mp_payment_id']}",
                               headers={"Authorization": f"Bearer {s['mp_access_token']}"})
        st = resp.json().get("status")
        if st == "approved":
            return await assign_coupons(order["id"])
        if st in ("cancelled", "rejected", "refunded"):
            await db.orders.update_one({"id": order["id"]}, {"$set": {"status": "cancelled"}})
            order["status"] = "cancelled"
    except Exception as e:  # noqa
        logger.warning("MP refresh failed %s", e)
    return order


async def check_ip(order, transaction_nsu, slug):
    s = await get_settings()
    body = {"handle": (s.get("infinitepay_handle") or "").lstrip("$"), "order_nsu": order["id"],
            "transaction_nsu": transaction_nsu, "slug": slug}
    async with httpx.AsyncClient(timeout=20) as c:
        for url in IP_CHECK_URLS:
            try:
                resp = await c.post(url, json=body)
                data = resp.json() if resp.content else {}
                if resp.status_code < 300:
                    if data.get("paid") or data.get("success") and data.get("paid") is not False:
                        await db.orders.update_one({"id": order["id"]}, {"$set": {"ip_transaction_nsu": transaction_nsu, "ip_slug": slug}})
                        return await assign_coupons(order["id"])
                    return order
            except Exception as e:  # noqa
                logger.warning("IP check failed %s", e)
    return order


@api.get("/orders/{order_id}")
async def get_order(order_id: str):
    o = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not o:
        raise HTTPException(404, "Pedido não encontrado")
    if o["status"] == "pending" and o["gateway"] == "mercadopago":
        o = await refresh_mp(o)
    elif o["status"] == "pending" and o["gateway"] == "infinitepay" and o.get("ip_transaction_nsu"):
        o = await check_ip(o, o["ip_transaction_nsu"], o.get("ip_slug"))
    return public_order(o)


class IPConfirm(BaseModel):
    order_nsu: str
    transaction_nsu: Optional[str] = None
    slug: Optional[str] = None


@api.post("/orders/infinitepay/confirm")
async def ip_confirm(body: IPConfirm):
    o = await db.orders.find_one({"id": body.order_nsu}, {"_id": 0})
    if not o:
        raise HTTPException(404, "Pedido não encontrado")
    if o["status"] != "paid" and body.transaction_nsu:
        o = await check_ip(o, body.transaction_nsu, body.slug)
    return public_order(o)


@api.get("/coupons/lookup")
async def lookup(whatsapp: str):
    phone = re.sub(r"\D", "", whatsapp)
    if len(phone) < 8:
        raise HTTPException(400, "WhatsApp inválido")
    r = await get_active_raffle()
    orders = await db.orders.find({"raffle_id": r["id"], "status": "paid"}, {"_id": 0}).to_list(10000)
    mine = [o for o in orders if re.sub(r"\D", "", o.get("whatsapp", "")) == phone]
    return {"name": mine[0]["name"] if mine else None, "coupons": [c for o in mine for c in o.get("coupons", [])]}


# ---------------- Webhooks ----------------
@api.post("/webhooks/mercadopago")
async def mp_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    pid = str((payload.get("data") or {}).get("id") or request.query_params.get("data.id") or request.query_params.get("id") or "")
    if pid:
        o = await db.orders.find_one({"mp_payment_id": pid}, {"_id": 0})
        if o and o["status"] == "pending":
            await refresh_mp(o)
    return {"ok": True}


@api.post("/webhooks/infinitepay")
async def ip_webhook(request: Request):
    try:
        p = await request.json()
    except Exception:
        p = {}
    nsu = p.get("order_nsu")
    o = await db.orders.find_one({"id": nsu}, {"_id": 0}) if nsu else None
    if o and o["status"] == "pending":
        await check_ip(o, p.get("transaction_nsu"), p.get("invoice_slug") or p.get("slug"))
    return {"ok": True}


# ---------------- Admin ----------------
@api.get("/admin/overview")
async def admin_overview(_=Depends(require_admin)):
    r = await get_active_raffle()
    if r.get("status") == "active":
        await sync_goal(r["id"])
        r = await get_active_raffle()
    st = await raffle_stats(r)
    data = public_raffle(r, st)
    data["manual_extra"] = r.get("manual_extra", 0)
    return data


@api.put("/admin/raffle")
async def admin_update_raffle(body: RaffleUpdate, _=Depends(require_admin)):
    r = await get_active_raffle()
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if "default_gateway" in upd and upd["default_gateway"] not in ("mercadopago", "infinitepay"):
        raise HTTPException(400, "Gateway inválido")
    if upd:
        await db.raffles.update_one({"id": r["id"]}, {"$set": upd})
        await sync_goal(r["id"])
    return {"ok": True}


@api.post("/admin/raffle/extra")
async def admin_extra(body: ExtraIn, _=Depends(require_admin)):
    r = await get_active_raffle()
    await db.raffles.update_one({"id": r["id"]}, {"$set": {"manual_extra": float(body.amount)}})
    await sync_goal(r["id"])
    return {"ok": True}


def mask(v):
    if not v:
        return ""
    return v[:6] + "•" * 8 + v[-4:] if len(v) > 12 else "•" * len(v)


@api.get("/admin/keys")
async def admin_keys(_=Depends(require_admin)):
    s = await get_settings()
    return {"mp_access_token_masked": mask(s.get("mp_access_token")), "mp_configured": bool(s.get("mp_access_token")),
            "infinitepay_handle": s.get("infinitepay_handle", ""), "infinitepay_configured": bool(s.get("infinitepay_handle"))}


@api.put("/admin/keys")
async def admin_save_keys(body: KeysIn, _=Depends(require_admin)):
    upd = {}
    if body.mp_access_token is not None and body.mp_access_token.strip():
        upd["mp_access_token"] = body.mp_access_token.strip()
    if body.infinitepay_handle is not None:
        upd["infinitepay_handle"] = body.infinitepay_handle.strip().lstrip("$")
    if upd:
        await db.settings.update_one({"id": "keys"}, {"$set": upd}, upsert=True)
    return {"ok": True}


@api.get("/admin/participants")
async def admin_participants(_=Depends(require_admin)):
    r = await get_active_raffle()
    return await db.orders.find({"raffle_id": r["id"]}, {"_id": 0, "pix_qr_base64": 0}).sort("created_at", -1).to_list(10000)


@api.post("/admin/participants")
async def admin_add_participant(body: ManualIn, _=Depends(require_admin)):
    if len(body.name.strip()) < 1:
        raise HTTPException(400, "Informe o nome")
    r = await get_active_raffle()
    order = {"id": str(uuid.uuid4()), "raffle_id": r["id"], "name": body.name.strip(), "whatsapp": body.whatsapp.strip(),
             "quantity": body.quantity, "amount": round(body.quantity * float(r["price"]), 2), "gateway": "manual",
             "status": "pending", "coupons": [], "source": "manual", "created_at": iso(now())}
    await db.orders.insert_one(dict(order))
    return await assign_coupons(order["id"])


@api.post("/admin/participants/{order_id}/approve")
async def admin_approve(order_id: str, _=Depends(require_admin)):
    o = await assign_coupons(order_id)
    if not o:
        raise HTTPException(404, "Pedido não encontrado")
    return o


@api.delete("/admin/participants/{order_id}")
async def admin_delete(order_id: str, _=Depends(require_admin)):
    o = await db.orders.find_one({"id": order_id}, {"_id": 0, "raffle_id": 1})
    await db.orders.delete_one({"id": order_id})
    if o:
        await sync_goal(o["raffle_id"])
    return {"ok": True}


@api.post("/admin/draw")
async def admin_draw(_=Depends(require_admin)):
    r = await get_active_raffle()
    return await perform_draw(r)


@api.post("/admin/raffle/new")
async def admin_new_raffle(_=Depends(require_admin)):
    r = await get_active_raffle()
    last = await db.raffles.find_one({}, {"_id": 0}, sort=[("created_at", -1)]) or r
    await db.raffles.update_many({"status": {"$in": ["active", "drawn", "drawing"]}}, {"$set": {"status": "finished", "finished_at": iso(now())}})
    new = {"id": str(uuid.uuid4()), "title": last["title"], "description": last.get("description", ""),
           "image_url": last.get("image_url", ""), "goal": last.get("goal", 0), "price": last.get("price", 10),
           "default_gateway": last.get("default_gateway", "mercadopago"), "status": "active", "manual_extra": 0.0,
           "next_coupon": 1, "draw_at": None, "created_at": iso(now())}
    await db.raffles.insert_one(dict(new))
    return {"ok": True}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _auto_draw_loop():
    while True:
        try:
            await auto_draw_tick()
        except Exception as e:  # noqa
            logger.error("auto draw loop error %s", e)
        await asyncio.sleep(2)


@app.on_event("startup")
async def start_background():
    asyncio.create_task(_auto_draw_loop())


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
