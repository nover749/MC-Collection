import time
import random
import string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")  # Chrome 112+ headless mode
        options.add_argument("--window-size=1200,900")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def check_username_available(driver, username):
    driver.get(f"https://www.roblox.com/users/username-validation?username={username}")
    time.sleep(1)
    try:
        # This endpoint returns JSON like {"code":0,"message":"Username is available."}
        result = driver.find_element(By.TAG_NAME, "pre").text
        if '"code":0' in result:
            return True
        else:
            return False
    except Exception:
        # fallback, assume unavailable
        return False

def generate_username(driver):
    while True:
        number = random.randint(1000, 9999)
        username = f"BotFriend{number}"
        if check_username_available(driver, username):
            return username
        else:
            print(f"Username {username} is taken, trying another...")

def friend_user(driver, user_id):
    try:
        friend_url = f"https://www.roblox.com/users/{user_id}/profile"
        driver.get(friend_url)
        time.sleep(3)

        add_friend_button = driver.find_element(By.XPATH, "//button[contains(text(),'Add Friend')]")
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", add_friend_button)
        time.sleep(random.uniform(1, 2))
        add_friend_button.click()
        print(f"✅ Sent friend request to user ID {user_id}.")
    except Exception as e:
        print(f"⚠️ Could not send friend request to user ID {user_id}. Error: {e}")

def main():
    # EDIT THIS: Roblox user ID you want to friend (integer as a string)
    user_to_friend_id = "123456789"

    driver = setup_driver(headless=True)

    print("Generating available username starting with 'BotFriend'...")
    username = generate_username(driver)
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    print(f"Username found: {username}")
    print(f"Generated password: {password}")

    driver.get("https://www.roblox.com/account/signupredir")
    time.sleep(3)  # Wait for page to load

    # Fill username
    try:
        username_input = driver.find_element(By.ID, "username")
        username_input.clear()
        username_input.send_keys(username)
        print("Username entered.")
    except Exception as e:
        print("Failed to find username input:", e)
    
    # Fill password
    try:
        password_input = driver.find_element(By.ID, "password")
        password_input.clear()
        password_input.send_keys(password)
        print("Password entered.")
    except Exception as e:
        print("Failed to find password input:", e)

    # Select birthdate (just fixed safe date)
    try:
        month_select = driver.find_element(By.NAME, "Month")
        month_select.send_keys("Jan")
        day_select = driver.find_element(By.NAME, "Day")
        day_select.send_keys("1")
        year_select = driver.find_element(By.NAME, "Year")
        year_select.send_keys("2000")
        print("Birthdate selected.")
    except Exception as e:
        print("Failed to select birthdate:", e)

    # Switch to visible mode for captcha solving
    print("Switching to visible mode for captcha solving...")
    driver.quit()
    driver = setup_driver(headless=False)
    driver.get("https://www.roblox.com/account/signupredir")
    time.sleep(3)

    # Re-fill form
    try:
        username_input = driver.find_element(By.ID, "username")
        username_input.clear()
        username_input.send_keys(username)
        password_input = driver.find_element(By.ID, "password")
        password_input.clear()
        password_input.send_keys(password)
        month_select = driver.find_element(By.NAME, "Month")
        month_select.send_keys("Jan")
        day_select = driver.find_element(By.NAME, "Day")
        day_select.send_keys("1")
        year_select = driver.find_element(By.NAME, "Year")
        year_select.send_keys("2000")
        print("Re-filled signup form in visible mode. Please solve the captcha and complete the signup.")
    except Exception as e:
        print("Failed to re-fill form:", e)

    input("Press Enter after you complete the captcha and signup to continue...")

    # Friend the specified user
    friend_user(driver, user_to_friend_id)

    input("Press Enter to close the browser...")
    driver.quit()
    print("Done. Remember to save your username and password!")

if __name__ == "__main__":
    while True:
        main()
        user_input = input("Press Enter to run again or type 'q' to quit: ").strip().lower()
        if user_input == 'q':
            print("Exiting loop. Goodbye!")
            break
