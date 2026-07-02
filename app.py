import streamlit as st
import requests
import bs4
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- TITULEK STRÁNKY ---
st.title("🏨 Hlídač cen - Hotel Molindrio")
st.write("Skript běží na pozadí a kontroluje klubovou cenu Plava Laguna.")

# --- KONFIGURACE (Získává se bezpečně ze Secrets) ---
URL = "https://www.plavalaguna.com/booking/?adultNumber=2&childNumber=1&dateFrom=2026-10-26&dateTo=2026-11-01&childAges=10&property=hotel-molindrio&rateId=RATE525987&propertyId=8538b43c0352df0deb11cc7d20a9995a"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Streamlit má sekci "Secrets", kam bezpečně schováš hesla (viz Krok 2)
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
    try:
        response = requests.get(URL, headers=HEADERS, timeout=20)
        soup = bs4.BeautifulSoup(response.text, "html.parser")
        cenove_bloky = soup.find_all("div", class_="price")
        
        for blok in cenove_bloky:
            if blok.find("p", class_="title") and "PLAVA LAGUNA CLUB" in blok.find("p", class_="title").text:
                p_total = blok.find("p", class_="total")
                if p_total:
                    cena_str = p_total.text.replace("€", "").replace(",", ".")
                    return float(cena_str)
        return None
    except Exception as e:
        st.error(f"Chyba při stahování webu: {e}")
        return None

# Použijeme st.session_state, aby si Streamlit pamatoval poslední cenu mezi obnoveními stránky
if "posledni_cena" not in st.session_state:
    st.session_state.posledni_cena = None

# Tlačítko pro manuální kontrolu na webu
if st.button("Zkontrolovat cenu hned"):
    aktualni_cena = ziskej_cenu()
    if aktualni_cena:
        st.metric(label="Aktuální klubová cena", value=f"{aktualni_cena} €")
        
        if st.session_state.posledni_cena is None:
            st.session_state.posledni_cena = aktualni_cena
            posli_email("Hlídač aktivován na Streamlitu", f"První načtená cena: {aktualni_cena} €")
            st.success("Úvodní e-mail odeslán!")
        elif aktualni_cena != st.session_state.posledni_cena:
            posli_email("ZMĚNA CENY!", f"Nová klubová cena je {aktualni_cena} €")
            st.session_state.posledni_cena = aktualni_cena
            st.warning("Cena se změnila! E-mail byl odeslán.")
        else:
            st.info("Cena se od poslední kontroly nezměnila.")
    else:
        st.error("Cenu se nepodařilo z webu načíst.")