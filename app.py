import streamlit as st
import requests
import bs4
import datetime
import smtplib
import os
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- TITULEK STRÁNKY ---
st.title("🏨 Hlídač cen s grafem - Hotel Molindrio")
st.write("Skript kontroluje klubovou cenu a zaznamenává její vývoj do grafu.")

# --- KONFIGURACE (Sem vlož svou funkční URL) ---
URL = "https://www.plavalaguna.com/accommodation/hotel-molindrio/rooms/?adultNumber=2&childNumber=1&dateFrom=2026-10-26&dateTo=2026-11-01&childAges=10"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
CSV_FILE = "historie_cen.csv"

ODESILATEL_EMAIL = st.secrets["ODESILATEL_EMAIL"]
HESLO_APLIKACE = st.secrets["HESLO_APLIKACE"]
PRIJEMCE_EMAIL = ["v.nekovarik@gmail.com"]

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
                    cena_str = p_total.text.replace("€", "").replace(",", ".").strip()
                    return float(cena_str)
        return None
    except Exception as e:
        st.error(f"Chyba při stahování webu: {e}")
        return None

def uloz_do_historie(cena):
    ted = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    # Zde je opravené malé "n" na začátku názvu proměnné
    novy_radek = pd.DataFrame([[ted, cena]], columns=["Datum", "Cena"])
    
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        # Zapíšeme bod, jen pokud je cena jiná než poslední uložená
        if df.empty or df.iloc[-1]["Cena"] != cena:
            df = pd.concat([df, novy_radek], ignore_index=True)
            df.to_csv(CSV_FILE, index=False)
    else:
        novy_radek.to_csv(CSV_FILE, index=False)

# --- SKRIPT / ROZHRANÍ ---

if st.button("Zkontrolovat cenu hned"):
    aktualni_cena = ziskej_cenu()
    if aktualni_cena:
        st.metric(label="Aktuální klubová cena", value=f"{aktualni_cena} €")
        
        stara_cena = None
        if os.path.exists(CSV_FILE):
            df_stary = pd.read_csv(CSV_FILE)
            if not df_stary.empty:
                stara_cena = df_stary.iloc[-1]["Cena"]
        
        uloz_do_historie(aktualni_cena)
        
        if stara_cena is None:
            posli_email("Hlídač aktivován", f"První načtená cena: {aktualni_cena} €")
            st.success("Úvodní e-mail odeslán a cena zapsána do historie!")
        elif aktualni_cena != stara_cena:
            posli_email("ZMĚNA CENY!", f"Nová klubová cena je {aktualni_cena} € (původně {stara_cena} €)")
            st.warning("Cena se změnila! E-mail byl odeslán.")
        else:
            st.info("Cena se od poslední kontroly nezměnila. Bod byl přesto zaznamenán.")
    else:
        st.error("Cenu se nepodařilo z webu načíst.")

# --- VYKRESLENÍ GRAFU ---
st.subheader("📈 Vývoj ceny v čase")
if os.path.exists(CSV_FILE):
    data = pd.read_csv(CSV_FILE)
    if not data.empty:
        data_graf = data.set_index("Datum")
        st.line_chart(data_graf)
        st.dataframe(data)
    else:
        st.write("Zatím nejsou k dispozici žádná data pro graf.")
else:
    st.write("Historie je prázdná. Klikni na tlačítko nahoře pro první zápis.")
