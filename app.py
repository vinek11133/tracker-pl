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

# --- KONFIGURACE ---
URL = "https://www.plavalaguna.com/accommodation/hotel-molindrio/rooms/?adultNumber=2&childNumber=1&dateFrom=2026-10-26&dateTo=2026-11-01&childAges=10"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
CSV_FILE = "historie_cen.csv"

ODESILATEL_EMAIL = st.secrets["ODESILATEL_EMAIL"]
HESLO_APLIKACE = st.secrets["HESLO_APLIKACE"]
PRIJEMCE_EMAIL = ["v.nekovarik = mail.com"]

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
    # Získáme aktuální čas
    ted = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    Novy_radek = pd.DataFrame([[ted, cena]], columns=["Datum", "Cena"])
    
    if os.path.exists(CSV_FILE):
        # Pokud soubor existuje, načteme ho a přidáme řádek
        df = pd.read_csv(CSV_FILE)
        # Ochrana: Zapíšeme cenu, jen pokud je jiná než úplně poslední záznam (at nemáme hromadu stejných bodů)
        if df.empty or df.iloc[-1]["Cena"] != cena:
            df = pd.concat([df, novy_radek], ignore_index=True)
            df.to_csv(CSV_FILE, index=False)
    else:
        # Pokud neexistuje, vytvoříme nový
        novy_radek.to_csv(CSV_FILE, index=False)

# --- SKRIPT / ROZHRANÍ ---

# Tlačítko pro manuální kontrolu na webu
if st.button("Zkontrolovat cenu hned"):
    aktualni_cena = ziskej_cenu()
    if aktualni_cena:
        st.metric(label="Aktuální klubová cena", value=f"{aktualni_cena} €")
        
        # Načteme předchozí cenu z CSV (pokud existuje) pro porovnání kvůli e-mailu
        stara_cena = None
        if os.path.exists(CSV_FILE):
            df_stary = pd.read_csv(CSV_FILE)
            if not df_stary.empty:
                stara_cena = df_stary.iloc[-1]["Cena"]
        
        # Uložíme nový bod do historie
        uloz_do_historie(aktualni_cena)
        
        # Logika e-mailů
        if stara_cena is None:
            posli_email("Hlídač aktivován", f"První načtená cena: {aktualni_cena} €")
            st.success("Úvodní e-mail odeslán a cena zapsána do historie!")
        elif aktualni_cena != stara_cena:
            posli_email("ZMĚNA CENY!", f"Nová klubová cena je {aktualni_cena} € (původně {stara_cena} €)")
            st.warning(f"Cena se změnila! E-mail byl odeslán.")
        else:
            st.info("Cena se od poslední kontroly nezměnila. Bod byl přesto zaznamenán.")
    else:
        st.error("Cenu se nepodařilo z webu načíst.")

# --- VYKRESLENÍ GRAFU ---
st.subheader("📈 Vývoj ceny v čase")
if os.path.exists(CSV_FILE):
    data = pd.read_csv(CSV_FILE)
    if not data.empty:
        # Převod sloupce Datum na index pro hezké zobrazení na ose X
        data_graf = data.set_index("Datum")
        # Streamlit vestavěný čárový graf
        st.line_chart(data_graf)
        # Ukážeme i tabulku pod grafem
        st.dataframe(data)
    else:
        st.write("Zatím nejsou k dispozici žádná data pro graf.")
else:
    st.write("Historie je prázdná. Klikni na tlačítko nahoře pro první zápis.")
