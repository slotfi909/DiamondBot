import logging
import uvicorn
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from prisma.enums import PaymentStatus
from dotenv import load_dotenv

load_dotenv()

# Utils
from src.utils.db import connect_to_db, db
from src.utils.other import to_rial, to_utc, zarinpal
from src.utils.time import substract_minutes
from src.constants import PENDING_ORDER_LIFETIME_MINUTES
from src.payment.zarinpal.errors import RPCError

app = FastAPI()

app.add_middleware(GZipMiddleware)

templates = Jinja2Templates(directory='templates')


@app.on_event('startup')
async def start_up():
    await connect_to_db()


@app.get('/verify/{order_id}', response_class=HTMLResponse)
async def verify_order(req: Request, order_id: int, bot_username: str):
    order = await db.order.find_unique(where={
        'order_id': order_id
    }, include={
        'product': True,
        'payment': True
    })

    if not order:
        return templates.TemplateResponse(request=req, name='verify.html', context={
            "was_successful": False,
            "message": "شماره سفارش وارد شده یافت نشد.",
            "bot_username": bot_username
        })

    try:
        async with db.tx(timeout=timedelta(milliseconds=6000)) as tx:
            verify_result = await zarinpal.verify(
                    amount=to_rial(order.payment.amount),
                    authority=order.payment.authority
            )

            payment = await tx.payment.find_first(where={
               "payment_id": order.payment.payment_id,
               'created_at': {
                   'gte': to_utc(substract_minutes(to_utc(datetime.now()), PENDING_ORDER_LIFETIME_MINUTES))
               }
            })

            if not payment:
                await zarinpal.reverse(authority=order.payment.authority)

                return templates.TemplateResponse(request=req, name='verify.html', context={
                            "was_successful": False,
                            "message": "متاسفانه پرداخت شما خارج از بازه مجاز بوده است و وجه پرداخت شده عودت داده شد.",
                            "bot_username": bot_username
                        })

            await tx.payment.update(
                where={
                    "payment_id": payment.payment_id
                },
                data={
                    "status": PaymentStatus.COMPLETED
                }
            )

            return templates.TemplateResponse(request=req, name='verify.html', context={
                        "was_successful": True,
                        "message": "پرداخت شما با موفقیت صورت گرفت و می توانید که به ربات برگردید",
                        "bot_username": bot_username
                    })

    except RPCError as ex:
        return templates.TemplateResponse(request=req, name='verify.html', context={
                    "was_successful": False,
                    "message": ex.get_error(ex.code)["fa"],
                    "bot_username": bot_username
                })


if __name__ == '__main__':
    uvicorn.run(app, port=8000)
