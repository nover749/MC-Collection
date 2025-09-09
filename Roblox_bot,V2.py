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
from selenium.common.exceptions import ElementClickInterceptedException
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
        add_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "friend-button"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_button)
        
        # Retry clicking Add Connection button
        for attempt in range(3):
            try:
                actions = ActionChains(driver)
                actions.move_to_element(add_button).pause(0.5).click().perform()
                print(f"✅ Clicked 'Add Connection' button for user ID {user_id}.")
                break
            except ElementClickInterceptedException:
                print(f"⚠️ Attempt {attempt+1}/3 failed to click Add Connection button, retrying...")
                time.sleep(0.5)
        
    except Exception as e:
        print(f"⚠️ Could not click 'Add Connection' button at all. Error: {e}")

def main():
    user_to_friend_id = "2045998620"  # Change or make dynamic if needed
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

        # Robust checkbox click with retries and JS fallback
        checkbox_clicked = False
        for _ in range(10):  # retry for ~10 seconds
            try:
                tos_checkbox = driver.find_element(By.ID, "signup-checkbox")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tos_checkbox)
                try:
                    actions = ActionChains(driver)
                    actions.move_to_element(tos_checkbox).pause(0.5).click().perform()
                    print("✔️ Clicked 'I agree' checkbox via ActionChains.")
                except:
                    driver.execute_script("arguments[0].click();", tos_checkbox)
                    print("✔️ Clicked 'I agree' checkbox via JS fallback.")
                checkbox_clicked = True
                break
            except:
                time.sleep(1)

        if not checkbox_clicked:
            print("ℹ️ 'I agree' checkbox not detected, continuing...")

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
