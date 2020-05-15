from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains


driver = webdriver.Firefox()
actionchains = ActionChains(driver)


driver.get('http://localhost:3000/')


wait = WebDriverWait(driver, 300)
wait.until(EC.url_contains("?access_token="))
body = driver.find_element_by_tag_name('body')
body_height = body.size['height']
body_width = body.size['width']


actionchains.move_by_offset(100,500).context_click().perform()