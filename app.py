import streamlit as st
import requests
import bs4
import datetime
import smtplib
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- TITULEK STRÁNKY ---
st.title("🏨 Hlídač cen s Google Tabulkou - Hotel Molindrio")
st.write("Data se trvale ukládají do tvé Google Tabulky, takže se v Cloudu nikdy nesmažou.")

# --- KONFIGURACE ---
URL = "https://www.plavalaguna.com/accommodation/hotel-molindrio/rooms/?adultNumber=2&childNumber=1&dateFrom=2026-10-26&dateTo=2026-11-01&childAges=10"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# URL tvé Google tabulky
GSHEET_URL = "https://docs.google.com/spreadsheets/d/16QLqFTbWAzQD460sifLaEV_nC3ufOK4BloW9BqbSd5M/edit?gid=0#gid=0"

ODESILATEL_EMAIL = st.secrets["ODESILATEL_EMAIL"]
HESLO_APLIKACE = st.secrets["HESLO_APLIKACE"]
PRIJEMCE_EMAIL = ["v.nekovarik@gmail.com"]

# Propojení s Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

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

# --- SKRIPT / ROZHRANÍ ---

if st.button("Zkontrolovat cenu hned"):
    with st.spinner("Stahuji aktuální cenu a synchronizuji s Google Tabulkou..."):
        aktualni_cena = ziskej_cenu()
        
    if aktualni_cena:
        st.metric(label="Aktuální klubová cena", value=f"{aktualni_cena} €")
        
        # Načteme stávající data z Google Tabulky
        try:
            df_existujici = conn.read(spreadsheet=GSHEET_URL, ttl=0)
        except:
            # Pokud je tabulka úplně prázdná, vytvoříme prázdný DataFrame
            df_existujici = pd.DataFrame(columns=["Datum", "Cena"])
            
        stara_cena = None
        if not df_existujici.empty:
            stara_cena = float(df_existujici.iloc[-1]["Cena"])
            
        # Pokud je cena jiná než poslední uložená, zapíšeme ji
        if stara_cena is None or aktualni_cena != stara_cena:
            ted = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            novy_radek = pd.DataFrame([[ted, aktualni_cena]], columns=["Datum", "Cena"])
            
            # Spojíme stará data s novým řádkem
            df_aktualizovane = pd.concat([df_existujici, novy_radek], ignore_index=True)
            
            # Uložíme zpět do Google Tabulky
            conn.update(spreadsheet=GSHEET_URL, data=df_aktualizovane)
            st.toast("Nová cena zapsána do Google Tabulky!", icon="📊")
            
            # Odeslání e-mailů
            if stara_cena is None:
                posli_email("Hlídač aktivován", f"První načtená cena: {aktualni_cena} €")
                st.success("Úvodní e-mail odeslán!")
            else:
                posli_email("ZMĚNA CENY!", f"Nová klubová cena je {aktualni_cena} € (původně {stara_cena} €)")
                st.warning("Cena se změnila! E-mail byl odeslán.")
        else:
            st.info("Cena se nezměnila, zápis do Google Tabulky nebyl nutný.")
    else:
        st.error("Cenu se nepodařilo z webu načíst.")

# --- VYKRESLENÍ GRAFU Z GOOGLE TABULKY ---
st.subheader("📈 Vývoj ceny (Data z Google Sheets)")
try:
    data = conn.read(spreadsheet=GSHEET_URL, ttl=0)
    if not data.empty:
        data_graf = data.set_index("Datum")
        st.line_chart(data_graf)
        st.dataframe(data)
    else:
        st.write("Tabulka je zatím prázdná. Klikni na tlačítko pro první zápis.")
except Exception as e:
    st.write("Zatím se nepodařilo načíst žádná data. Nejspíše je potřeba tabulku veřejně sdílet pro zápis.")
