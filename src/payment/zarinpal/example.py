# source: https://github.com/abolX/Zarinpal

# how to use:
from zarinpal import Zarinpal
from objects import MetaData
from asyncio import run 
from constants import MERCHANT_ID, DIAMOND_PACKAGE_PRICE, DIAMOND_PACKAGE_DESCRIPTION

zarinpal = Zarinpal(MERCHANT_ID) 
  

async def main(): 
    gatway_result = await zarinpal.request(
       amount=DIAMOND_PACKAGE_PRICE,
       description=DIAMOND_PACKAGE_DESCRIPTION,
       callback_url="t.me/diamond_edu_bot")
    #    metadata=MetaData(mobile="98900000000")
    # )
    print(f'final gateway: {gatway_result.payment_gateway_url}')

    verify_result = await zarinpal.verify(
        amount=DIAMOND_PACKAGE_PRICE,
        authority=gatway_result['authority']
    )
    print(f'verification result: {verify_result}')


if __name__ == "__main__":
    run(main())