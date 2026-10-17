from datetime import datetime

# Utils
from src.utils.time import substract_hour, to_utc
from src.utils.db import db

# Constants
from src.constants import CHAT_LIFETIME_HOURS


async def get_user(tel_id: int):
    return await db.user.find_unique(
        where={
            "tel_id": tel_id
        }
    )


async def has_active_chat(user_id: int):
    return await db.chat.find_first(
        where={
            "AND": [
                {
                    "OR": [
                        {
                            "started_by_id": user_id
                        },
                        {
                            "received_by_id": user_id
                        }
                    ]
                },
                {
                    "updated_at": {
                        "gte": to_utc(substract_hour(to_utc(datetime.now()), CHAT_LIFETIME_HOURS))
                    },
                },
                {
                    "exited_at": None
                }
            ]
        },
        include={
            "started_by": True,
            "received_by": True
        }
    )
