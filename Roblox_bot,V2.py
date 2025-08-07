import time
import random
import string
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.expected_conditions import any_of
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1200,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def check_username_available(username):
    url = "https://auth.roblox.com/v1/usernames/validate"
    payload = {"username": username, "birthday": "2000-01-01", "context": "Signup"}
    try:
        res = requests.post(url, json=payload)
        return res.json().get("code") == 0
    except Exception as e:
        print(f"Error checking username: {e}")
        return False

def generate_username():
    while True:
        number = random.randint(1000, 9999)
        username = f"BotFriend{number}"
        if check_username_available(username):
            return username
        else:
            print(f"Username {username} is taken, trying another...")

def wait_for_login(driver, timeout=30):
    try:
        WebDriverWait(driver, timeout).until(
            any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img.avatar")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "button#nav-settings")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='user-menu']")),
                EC.url_contains("/home")
            )
        )
        print("✅ Login confirmed.")
        return True
    except:
        print("⚠️ Login not detected after waiting.")
        return False

def friend_user(driver, user_id):
    try:
        driver.get(f"https://www.roblox.com/users/{user_id}/profile")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "friend-button"))
        )
        add_button = driver.find_element(By.ID, "friend-button")

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_button)
        
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "friend-button"))
        )

        actions = ActionChains(driver)
        actions.move_to_element(add_button).pause(0.5).click().perform()

        print(f"✅ Clicked 'Add Connection' button for user ID {user_id}.")

    except Exception as e:
        print(f"⚠️ Could not click 'Add Connection' button. Error: {e}")

def main():
    user_to_friend_id = "7706679074"
    username = generate_username()
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    print(f"Username found: {username}")
    print(f"Generated password: {password}")

    driver = setup_driver(headless=False)
    driver.get("https://www.roblox.com/signup")
    
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "signup-username"))).send_keys(username)
        driver.find_element(By.ID, "signup-password").send_keys(password)
        driver.find_element(By.NAME, "birthdayMonth").send_keys("Jan")
        driver.find_element(By.NAME, "birthdayDay").send_keys("1")
        driver.find_element(By.NAME, "birthdayYear").send_keys("2000")
        driver.find_element(By.ID, "MaleButton").click()  # or "FemaleButton"

        # Click Sign Up button automatically
        try:
            sign_up_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'signup-button') or contains(text(),'Sign Up')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", sign_up_button)
            time.sleep(1)
            sign_up_button.click()
            print("✔️ Clicked Sign Up button automatically. Please solve CAPTCHA now.")
        except Exception as e:
            print(f"⚠️ Could not click Sign Up automatically, please click it manually. Error: {e}")

        input("✅ Press Enter after you complete the CAPTCHA and signup...")

        if wait_for_login(driver):
            time.sleep(5)  # Let page settle
            friend_user(driver, user_to_friend_id)
        else:
            print("⚠️ Not logged in. Please log in manually and then press Enter to retry friend request.")
            input("Press Enter to try sending friend request again...")
            if wait_for_login(driver):
                friend_user(driver, user_to_friend_id)
            else:
                print("Still not logged in, skipping friend request.")

    except Exception as e:
        print(f"❌ Error during signup or friend request: {e}")

    input("Press Enter to close browser and end script...")
    driver.quit()

if __name__ == "__main__":
    while True:
        main()
        again = input("Press Enter to run again or type 'q' to quit: ").strip().lower()
        if again == "q":
            print("Exiting. Goodbye!")
            break
