from typing import Union, Optional

from .. import zarinpal
from ..objects import Data


class Reverse:
    async def reverse(
            self: "zarinpal.Zarinpal",
            authority: str,
    ) -> "object.Data":
        json = locals()
        del json["self"]

        json["merchant_id"] = self.merchant_id
        result = await self.connection.execute("reverse", json)
        return Data(**result)
