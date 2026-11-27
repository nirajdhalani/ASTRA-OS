from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models import User
from ..security import current_user

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/checkout")
def create_checkout_session(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not settings.stripe_secret_key or not settings.stripe_price_id_pro_monthly:
        raise HTTPException(status_code=503, detail="Billing is not configured. Set STRIPE_SECRET_KEY and STRIPE_PRICE_ID_PRO_MONTHLY.")
    try:
        import stripe
        stripe.api_key = settings.stripe_secret_key
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(email=user.email, metadata={"astra_user_id": str(user.id)})
            customer_id = customer.id
            user.stripe_customer_id = customer_id
            db.commit()
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": settings.stripe_price_id_pro_monthly, "quantity": 1}],
            success_url=settings.stripe_success_url,
            cancel_url=settings.stripe_cancel_url,
            client_reference_id=str(user.id),
            metadata={"astra_user_id": str(user.id)},
            subscription_data={"metadata": {"astra_user_id": str(user.id)}},
        )
        return {"checkout_url": session.url}
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not create the Stripe checkout session") from exc


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        import stripe
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature or payload") from exc
    if event["type"] == "checkout.session.completed":
        obj = event["data"]["object"]
        paid = obj.get("payment_status") in ("paid", "no_payment_required")
        user_id = (obj.get("metadata") or {}).get("astra_user_id") or obj.get("client_reference_id")
        if paid and user_id:
            user = db.get(User, int(user_id))
            if user:
                user.plan = "pro"
                db.commit()
    elif event["type"] == "customer.subscription.updated":
        obj = event["data"]["object"]
        user_id = (obj.get("metadata") or {}).get("astra_user_id")
        if user_id:
            user = db.get(User, int(user_id))
            if user:
                user.plan = "pro" if obj.get("status") in ("active", "trialing") else "free"
                db.commit()
    elif event["type"] == "customer.subscription.deleted":
        obj = event["data"]["object"]
        customer_id = obj.get("customer")
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.plan = "free"
            db.commit()
    return {"received": True}
