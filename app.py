import streamlit as st
import datetime
import smtplib
import time
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Importy pre Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- TITULOK STRÁNKY ---
st.title("🏨 Hlídač cen (Cookie-Buster v2) - Hotel Molindrio")
st.write("Skript spouští prohlížeč, odklikne anglickou cookie lištu a přečte klubovou cenu.")

URL = "https://www.plavalaguna.com/accommodation/hotel-molindrio/rooms/?adultNumber=2&childNumber=1&dateFrom=2026-10-26&dateTo=2026-11-01&childAges=10"

ODESILATEL_EMAIL = st.secrets["ODESILATEL_EMAIL"]
HESLO_APLIKACE = st.secrets["HESLO_APLIKACE"]
PRIJEMCE_EMAIL = ["v.nekovarik@gmail.com", "lucia.nekovarikova@gmail.com"]

def posli_email(predmet, telo):
    try:
        msg = MIMEMultipart()
        msg['From'] = ODESILATEL_EMAIL
        msg['To'] = ", ".join(PRIJEMCE_EMAIL)
        msg['Subject'] = predmet
        msg.attach(MIMEText(telo, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(ODESILATEL_EMAIL, HESLO_APLIKACE)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Chyba při odesílání e-mailu: {e}")
        return False

def ziskej_cenu():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920x1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    chrome_options.binary_location = "/usr/bin/chromium"

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        
        driver.get(URL)
        time.sleep(8) # Počkáme na plné načtení stránky a lišty
        
        # --- KROK: ODKLIKNUTÍ COOKIE LIŠTY (Cíleno na "Allow All") ---
        # Používáme podrobnější dotazy, které prohledají i vnitřní texty tlačítek
        cookie_selectors = [
            "//button[contains(., 'Allow All')]",
            "//button[contains(., 'Allow all')]",
            "//span[contains(., 'Allow All')]",
            "//span[contains(., 'Allow all')]",
            "//button[contains(., 'Accept')]",
            "//button[contains(@class, 'cookie')]"
        ]
        
        cookie_odkliknuto = False
        for selector in cookie_selectors:
            try:
                tlacitko = driver.find_element(By.XPATH, selector)
                # Klikneme na element
                tlacitko.click()
                cookie_odkliknuto = True
                st.toast("Cookie lišta ('Allow All') úspěšně odkliknuta!", icon="🍪")
                time.sleep(4) # Počkáme 4 sekundy, než lišta zmizí z obrazovky
                break
            except:
                continue
                
        if not cookie_odkliknuto:
            st.warning("Automatické odkliknutí 'Allow All' selhalo, zkouším číst cenu přes lištu...")

        # --- DIAGNOSTIKA: Vyfotíme stránku PO odkliknutí cookies ---
        screenshot_path = "vystup_po_allow_all.png"
        driver.save_screenshot(screenshot_path)
        if os.path.exists(screenshot_path):
            st.image(screenshot_path, caption="Snímek obrazovky po kliknutí na 'Allow All'")
        
        # --- KROK: ČTENÍ CENY ---
        cena = None
        cenove_bloky = driver.find_elements(By.CLASS_NAME, "price")
        
        for blok in cenove_bloky:
            try:
                title_element = blok.find_element(By.CLASS_NAME, "title")
                if "PLAVA LAGUNA CLUB" in title_element.text:
                    total_element = blok.find_element(By.CLASS_NAME, "total")
                    cena_str = total_element.text.replace("€", "").replace(",", ".").strip()
                    cena = float(cena_str)
                    break
            except:
                continue
                
        driver.quit()
        return cena
        
    except Exception as e:
        st.error(f"Chyba prohlížeče: {e}")
        try:
            driver.quit()
        except:
            pass
        return None

if "posledni_cena" not in st.session_state:
    st.session_state.posledni_cena = None

if st.button("Zkontrolovat cenu hned"):
    with st.spinner("Spouštím prohlížeč a klikám na Allow All..."):
        aktualni_cena = ziskej_cenu()
        
    if aktualni_cena:
        st.metric(label="Aktuální klubová cena", value=f"{aktualni_cena} €")
        
        if st.session_state.posledni_cena is None:
            st.session_state.posledni_cena = aktualni_cena
            posli_email("Hlídač aktivován", f"Cena: {aktualni_cena} €")
            st.success("Úvodní e-mail odeslán!")
        elif aktualni_cena != st.session_state.posledni_cena:
            posli_email("ZMĚNA CENY!", f"Nová klubová cena je {aktualni_cena} €")
            st.session_state.posledni_cena = aktualni_cena
            st.warning("Cena se změnila! E-mail byl odeslán.")
        else:
            st.info("Cena se od poslední kontroly nezměnila.")
    else:
        st.error("Cenu se nepodařilo vyndat. Podívej se na nový obrázek, jestli už ta lišta zmizela.")
