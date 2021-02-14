import typing

from selenium import webdriver

from netkeiba.errors import LoginError


def login(email: str, password: str) -> typing.List[typing.Dict]:
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)

    driver.get('https://regist.netkeiba.com/account/?pid=login')
    driver.find_element_by_xpath('//input[@name="login_id"]').send_keys(email)
    driver.find_element_by_xpath('//input[@name="pswd"]').send_keys(password)
    driver.find_element_by_xpath('//input[@alt="ログイン"]').click()

    cookies = driver.get_cookies()

    driver.quit()

    if not any([cookie.get('name') == 'nkauth' for cookie in cookies]):
        raise LoginError('Failed to login to netkeiba')

    return cookies
