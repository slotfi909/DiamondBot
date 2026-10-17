import re


def exact_matcher(data: str):
    def exact_matcher_action(callback_data: str):
        return data == callback_data

    return exact_matcher_action


def persian_matcher(data: str):
    if len(data) < 3:
        return False

    PERSIAN_REGEX = r"^[\u0600-\u06FF\s]+$"

    return re.match(PERSIAN_REGEX, data)


def national_code_matcher(national_code: str):
    if not re.search(r'^\d{10}$', national_code):
        return False

    check = int(national_code[9])
    s = sum(map(lambda x: int(national_code[x]) * (10 - x), range(0, 9))) % 11
    return (s < 2 and check == s) or (s >= 2 and check + s == 11)


def phone_number_matcher(phone_number: str):
    PHONE_NUMBER_REGEX = r'(0|\+98)?([0-9]){10}'

    return re.fullmatch(PHONE_NUMBER_REGEX, phone_number)


def dob_matcher(dob: str):
    DOB_REGEX = r'^\d{4}/\d{2}/\d{2}$'

    return re.match(DOB_REGEX, dob)
