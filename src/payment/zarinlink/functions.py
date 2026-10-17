import random
import os
import json
import asyncio
from playwright.async_api import async_playwright
from src.payment.constants import *

async def get_payment_link():
    random_number = "".join([str(random.randint(0, 9)) for _ in range(GENERATED_RAND_NUM_LEN)])
    payment_link = PAYMENT_LINKS[0]
    return random_number, payment_link

# this function must change
async def _get_confirm_code_from_user():
    print("please enter recieved code: ")
    recieved_code = str(input())
    result = []
    for i in range(len(recieved_code)):
        result.append(recieved_code[i])
    
    return result

def _check_for_cookies(input_addr: str):
    cookie_exists = False
    if os.path.isfile(input_addr):
        cookie_exists = True
        with open(input_addr,'r') as f:
            loaded_cookies = json.load(f)
        return True, loaded_cookies
    else:
        return False, None

async def verify_payment(payment_code: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=(not DEBUG_MODE))
        context = await browser.new_context(user_agent=USER_AGENT)

        cookie_exists, loaded_cookies = _check_for_cookies(COOKIE_ADDR)

        if cookie_exists:
            await context.add_cookies(loaded_cookies)

        page = await context.new_page()
        
        await page.goto(LOGIN_PAGE_ADDR,wait_until=WAIT_UNTIL ,timeout=TIMEOUT_MS)
        # await page.wait_for_load_state('load')
        await asyncio.sleep(SLEEP_WHILE_LOADING_SECOND)
        # await page.wait_for_selector('#username-mdc-text-field', state='visible')
        
        if DEBUG_MODE:
            print("page fully loaded..")
            print(f"current page url: {page.url}")

        if page.url == LOGIN_PAGE_ADDR:
            if DEBUG_MODE:
                print("didn't redirect.. need logging in")

            phone_number_css_selector = 'input[name="username"][class="mdc-text-field__input ltr"]'
            await page.type(phone_number_css_selector, PHONE_NUMBERS[0])
            await page.get_by_text('تایید و ادامه').click()

            confirm_code_list = await _get_confirm_code_from_user()
            confirm_code_inputs = await page.query_selector_all('.otp-input')      

            # Iterate through each input element and fill it
            cnt = 0
            for input_element in confirm_code_inputs:
                value_to_fill = confirm_code_list[cnt]; cnt += 1
                # await asyncio.sleep(1) # to not be detected as robot
                await input_element.fill(value_to_fill)

            await page.wait_for_load_state(WAIT_UNTIL)
            await asyncio.sleep(SLEEP_WHILE_LOADING_SECOND)
            # await page.wait_for_load_state('load')
            # await page.wait_for_selector('.ol-lg-12.col-md-12.col-sm-12.col-xs-12.top-box', state='visible')
                


        else:
            if DEBUG_MODE:
                print("doesn't need logging in")

        await page.goto(SUCCESSFULY_PAYMENTS_URL, wait_until=WAIT_UNTIL, timeout=TIMEOUT_MS)
        # await page.wait_for_load_state('load')
        await asyncio.sleep(SLEEP_WHILE_LOADING_SECOND)

        paid_info_identifiers_links = await page.query_selector_all('a.pointer.fa-number')
        urls = []
        for link in paid_info_identifiers_links:
            url = await page.evaluate('(element) => element.href', link)
            urls.append(url)

        unique_urls = list(dict.fromkeys(urls))
        if DEBUG_MODE:
            print(f'collected urls: {unique_urls}')

        found = False
        for payment_result_page in unique_urls:
            if found == True:
                break
            await page.goto(payment_result_page, wait_until=WAIT_UNTIL, timeout=TIMEOUT_MS)
            await page.wait_for_selector('.col-lg-7.col-md-8.col-xs-7.col-sm-7.info > p', state="visible")
            p_tags = await page.query_selector_all('.col-lg-7.col-md-8.col-xs-7.col-sm-7.info > p')
            for p_tag in p_tags:
                text_content = await p_tag.inner_text()
                if len(text_content) == GENERATED_RAND_NUM_LEN:
                    if DEBUG_MODE:
                        print(f"in payment result {payment_result_page}, extracted text from P tag: {text_content}")
                    if text_content == payment_code:
                        found = True
                        break

        if DEBUG_MODE:        
            print(f"final url before closing: {page.url}")
            print(f'found: {found}')

        # update cookies
        if os.path.isfile(COOKIE_ADDR):
            os.remove(COOKIE_ADDR)
        retrieved_cookies = await context.cookies()
        with open(COOKIE_ADDR,'w') as f:
            json.dump(retrieved_cookies, f)
        if DEBUG_MODE:
            print("cookie saved..")

        await browser.close()
        return found
