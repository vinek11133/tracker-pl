import streamlit as st
import datetime
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Importy pro Selenium (prohlížeč na pozadí)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


# --- TITULEK STRÁNKY ---
st.title("🏨 Hlídač cen (Selenium Edice) - Hotel Molindrio")
st.write("Skript spouští virtuální prohlížeč pro obcházení ochrany webu.")

# --- KONFIGURACE ---
URL = "https://www.plavalaguna.com/booking/?adultNumber=2&childNumber=1&dateFrom=2026-10-26&dateTo=2026-11-01&childAges=10&property=hotel-molindrio&rateId=RATE525987&propertyId=8538b43c0352df0deb11cc7d20a9995a"

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
    chrome_options.add_argument("--headless")  # Skrytý režim
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920x1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    
    # !!! TATO ZMĚNA ŘÍKÁ SELENIU, KDE HLEDAT INSTALOVANÝ CHROMIUM V SYSTÉMU !!!
    chrome_options.binary_location = "/usr/bin/chromium"

    try:
        # Použijeme vestavěný driver ze systému, nebudeme instalovat přes webdriver-manager
        driver = webdriver.Chrome(options=chrome_options)
        
        driver.get(URL)
        time.sleep(10)  # Necháme delší čas (10s) na načtení v cloudu
        
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

# Tlačítko pro manuální kontrolu
if st.button("Zkontrolovat cenu hned"):
    with st.spinner("Spouštím virtuální prohlížeč a načítám cenu... (cca 15 sekund)"):
        aktualni_cena = ziskej_cenu()
        
    if aktualni_cena:
        st.metric(label="Aktuální klubová cena", value=f"{aktualni_cena} €")
        
        if st.session_state.posledni_cena is None:
            st.session_state.posledni_cena = aktualni_cena
            posli_email("Hlídač aktivován na Streamlitu (Selenium)", f"První načtená cena přes prohlížeč: {aktualni_cena} €")
            st.success("Úvodní e-mail odeslán!")
        elif aktualni_cena != st.session_state.posledni_cena:
            posli_email("ZMĚNA CENY!", f"Nová klubová cena je {aktualni_cena} €")
            st.session_state.posledni_cena = aktualni_cena
            st.warning("Cena se změnila! E-mail byl odeslán.")
        else:
            st.info("Cena se od poslední kontroly nezměnila.")
    else:
        st.error("Cenu se nepodařilo z webu načíst ani přes virtuální prohlížeč.")
