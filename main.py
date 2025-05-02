from FacebookAutomation import replace_semicolons_with_pipes, remove_first_line_from_file, count_pipes_in_first_line, extract_data_from_first_line, count_remaining_lines_in_file
import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.by import By

def click_auto(driver, label_or_id, use_id=False):
    try:
        if use_id:
            # Use ID to find the element
            element = driver.find_element(By.ID, label_or_id)
        else:
            # Use text to find the element
            element = driver.find_element(By.XPATH, f"//*[contains(text(), '{label_or_id}')]")
        element.click()
        time.sleep(5)
    except Exception as e:
        print(f"Error clicking element with {('ID' if use_id else 'text')} '{label_or_id}': {e}")

# Function to send keys with a delay
def send_keys_auto(driver, label_or_id, value, delay=0.3):
    try:
        time.sleep(1)
        try:
            input_element = driver.find_element(By.XPATH, f"//*[@aria-label='{label_or_id}']")
        except:
            # Fallback to finding by ID if aria-label is not found
            input_element = driver.find_element(By.ID, label_or_id)

        for char in value:
            input_element.send_keys(char)
            time.sleep(delay)
            time.sleep(1)

    except Exception as e:
        print(f"Error sending keys to '{label_or_id}': {e}")

# Path to chromedriver and data file
CHROME_DRIVER_PATH = "webdriver/chromedriver.exe"
file_path = 'results.txt'

# Function to process each user data
def all_file(N):
    print(f"Thread {N} running...")

    # File handling
    replace_semicolons_with_pipes(file_path)
    remove_first_line_from_file(file_path)
    pipe_count = count_pipes_in_first_line(file_path)
    user_data = extract_data_from_first_line(file_path, pipe_count)
    count_remaining_lines_in_file(file_path)

    # Browser setup
    options = Options()
    options.add_argument("--window-size=300,430")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument(
        'user-agent=Mozilla/5.0 (Linux; Android 8.1.0; SM-G960F) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/72.0.3626.121 Mobile Safari/537.36'
    )

    service = Service(executable_path=CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.get("https://mobile.facebook.com/reg")
    time.sleep(3)

    if user_data:
        First_Name = user_data['First_name']
        Last_Name = user_data['last_name']
        Birthday = user_data['birthday']

        Gender = user_data['Gender']
        Phone = user_data['Phone']
        Password = user_data['password']
        IUD = user_data['iud']
        XS = user_data['xs']
        SB = user_data['sb']
        FR = user_data['fr']
        C_USER = user_data['c_user']

        try:
            time.sleep(4)
            driver.find_element(By.XPATH, '//*[@aria-label="Get started"]').click()
            time.sleep(3)

            send_keys_auto(driver, "First name", First_Name)
            time.sleep(3)

            send_keys_auto(driver, "Last name", Last_Name)
            time.sleep(2)
            click_auto(driver,"Next")

        except Exception as e:
            print(f"Error during automation: {e}")
        finally:
            driver.quit()

        # Debugging: Print the user data
        print(f"User {N} Data:")
        print(f"First Name: {First_Name}")
        print(f"Last Name: {Last_Name}")
        print(f"Gender: {Gender}")
        print(f"Phone: {Phone}")
        print(f"Password: {Password}")
        print(f"Birthday: {Birthday}")
        print(f"Additional Info - IUD: {IUD}, XS: {XS}, SB: {SB}, FR: {FR}, C_USER: {C_USER}")

# Function to start threads
def start_threads():
    TH = 2  # Define number of threads to run
    threads = []

    for N in range(TH):
        time.sleep(1)  # Add delay between starting threads
        thread = threading.Thread(target=all_file, args=(N,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()  # Ensure all threads finish before proceeding

# Start all threads
start_threads()
