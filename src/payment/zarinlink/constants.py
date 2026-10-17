import os

COOKIE_ADDR = "assets/cookies.json"
GENERATED_RAND_NUM_LEN = 9
LOGIN_PAGE_ADDR = 'https://next.zarinpal.com/auth/login'
LOGIN_SUCCESSFUL_ADDR = 'https://next.zarinpal.com/panel/dashboard'
SUCCESSFULY_PAYMENTS_URL = os.getenv('ZARINLINK_PAYMENTS_URL', '')
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
PHONE_NUMBERS = [os.getenv('ZARINLINK_PHONE_NUMBER', '')]
PAYMENT_LINKS = [os.getenv('ZARINLINK_PAYMENT_LINK', '')]
SLEEP_WHILE_LOADING_SECOND = 5
TIMEOUT_MS = 10000
WAIT_UNTIL = 'domcontentloaded'  # domcontentloaded, commit, load, networkidle

DEBUG_MODE = False
