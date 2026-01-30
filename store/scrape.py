from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pickle
import time

def get_driver():
    """Setup Chrome driver"""
    service = Service(ChromeDriverManager().install())
    chrome_options = Options()
    # Uncomment below to run without browser window
    # chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def load_cookies(driver, url):
    """Load cookies from file and add to driver"""
    try:
        # Load cookies from file
        with open('cookies.pkl', 'rb') as file:
            cookies = pickle.load(file)
        
        # First go to the domain
        driver.get(url)
        time.sleep(2)
        
        # Clear existing cookies and add saved ones
        driver.delete_all_cookies()
        
        for cookie in cookies:
            try:
                # Only add cookies for the correct domain
                if 'ethiopianairlines.com' in cookie.get('domain', ''):
                    driver.add_cookie(cookie)
            except Exception as e:
                print(f"⚠️ Could not add cookie {cookie.get('name')}: {e}")
        
        print(f"✅ Loaded {len(cookies)} cookies")
        return True
        
    except FileNotFoundError:
        print("❌ Cookies file not found. Please run the login script first.")
        return False
    except Exception as e:
        print(f"❌ Error loading cookies: {e}")
        return False

def main():
    driver = get_driver()
    
    try:
        # URL to scrape
        url = 'http://etmxi.ethiopianairlines.com/maintenix/common/ToDoList.jsp'
        
        # Try to load cookies
        if load_cookies(driver, url):
            # Refresh page with cookies
            driver.refresh()
            time.sleep(3)
            
            # Check if login was successful
            if "login" in driver.title.lower() or "sign in" in driver.page_source.lower():
                print("❌ Login failed. Cookies may have expired.")
                print("Please run the login script again.")
                return
            
            print("✅ Successfully logged in with cookies!")
            
            # Now you can interact with the page
            # Example: Click fleet list button
            try:
                wait = WebDriverWait(driver, 10)
                fleet_button = wait.until(
                    EC.element_to_be_clickable((By.ID, 'idTabFleetList_link'))
                )
                fleet_button.click()
                print("✅ Clicked fleet list button")
                time.sleep(2)
                
                # Add your scraping code here...
                
            except Exception as e:
                print(f"⚠️ Could not find fleet button: {e}")
            
            # Keep browser open for inspection
            input("Press Enter to close browser...")
            
        else:
            print("Starting manual login process...")
            # If cookies fail, do manual login
            driver.get(url)
            input("Please login manually and press Enter when done...")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()