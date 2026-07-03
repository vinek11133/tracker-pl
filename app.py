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
st.title("🔒 Bezpečný hlídač cen - Hotel Molindrio")
st.write("Aplikace je propojena přes zabezpečený Google Servisní účet.")

# --- KONFIGURACE (Sem vlož pouze veřejnou URL hotelu) ---
URL = "https://www.plavalaguna.com/accommodation/hotel-molindrio/rooms/?adultNumber=2&childNumber=1&dateFrom=2026-10-26&dateTo=2026-11-01&childAges=10"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

ODESILATEL_EMAIL = st.secrets["ODESILATEL_EMAIL"]
HESLO_APLIKACE = st.secrets["HESLO_APLIKACE"]
PRIJEMCE_EMAIL = ["v.nekovarik@gmail.com"]

# Bezpečné připojení k Google Sheets (vše si bere ze Secrets)
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
    with st.spinner("Stahuji aktuální cenu a bezpečně zapisuji do Google Sheets..."):
        aktualni_cena = ziskej_cenu()
        
    if aktualni_cena:
        st.metric(label="Aktuální klubová cena", value=f"{aktualni_cena} €")
        
        # Načtení dat (bez nutnosti zadávat URL v kódu)
        try:
            df_existujici = conn.read(ttl=0)
        except Exception as e:
            df_existujici = pd.DataFrame(columns=["Datum", "Cena"])
            
        stara_cena = None
        if not df_existujici.empty:
            stara_cena = float(df_existujici.iloc[-1]["Cena"])
            
        if stara_cena is None or aktualni_cena != stara_cena:
            ted = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            novy_radek = pd.DataFrame([[ted, aktualni_cena]], columns=["Datum", "Cena"])
            df_aktualizovane = pd.concat([df_existujici, novy_radek], ignore_index=True)
            
            # Bezpečný zápis pod identitou robota
            conn.update(data=df_aktualizovane)
            st.toast("Nová cena bezpečně zapsána!", icon="💾")
            
            if stara_cena is None:
                posli_email("Hlídač aktivován", f"První načtená cena: {aktualni_cena} €")
                st.success("Úvodní e-mail odeslán!")
            else:
                posli_email("ZMĚNA CENY!", f"Nová klubová cena je {aktualni_cena} € (původně {stara_cena} €)")
                st.warning("Cena se změnila! E-mail byl odeslán.")
        else:
            st.info("Cena se nezměnila, zápis nebyl nutný.")
    else:
        st.error("Cenu se nepodařilo z webu načíst.")

# --- VYKRESLENÍ GRAFU ---
st.subheader("📈 Vývoj ceny (Zabezpečená data)")
try:
    data = conn.read(ttl=0)
    if not data.empty:
        data_graf = data.set_index("Datum")
        st.line_chart(data_graf)
        st.dataframe(data)
    else:
        st.write("Tabulka je zatím prázdná. Klikni na tlačítko pro první zápis.")
except Exception as e:
    st.error(f"Chyba při načítání dat. Zkontroluj správnost klíčů v Secrets. Detaily: {e}")
    # =========================================================================
# 🤖 AUTOMATICKÁ KONTROLA NA POZADÍ (KAŽDÝCH 6 HODIN)
# =========================================================================
import threading
import time

def kontrola_na_pozadi(gc_info, spreadsheet_url, url, headers, odesilatel, heslo, prijemci):
    import requests
    import bs4
    import gspread
    import datetime
    import smtplib
    from google.oauth2.service_account import Credentials
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    print("🚀 Vlákno automatického hlídače na pozadí úspěšně nastartováno.")
    
    while True:
        try:
            # 1. Stažení ceny z webu (bezpečně na pozadí)
            response = requests.get(url, headers=headers, timeout=20)
            soup = bs4.BeautifulSoup(response.text, "html.parser")
            cenove_bloky = soup.find_all("div", class_="price")
            
            aktualni_cena = None
            for blok in cenove_bloky:
                if blok.find("p", class_="title") and "PLAVA LAGUNA CLUB" in blok.find("p", class_="title").text:
                    p_total = blok.find("p", class_="total")
                    if p_total:
                        cena_str = p_total.text.replace("€", "").replace(",", ".").strip()
                        aktualni_cena = float(cena_str)
                        break
            
            if aktualni_cena:
                # 2. Připojení k Google Sheets přes gspread (vláknově bezpečné pro pozadí)
                scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                creds = Credentials.from_service_account_info(gc_info, scopes=scopes)
                client = gspread.authorize(creds)
                
                sheet = client.open_by_url(spreadsheet_url).sheet1
                vsechna_data = sheet.get_all_records()
                
                stara_cena = None
                if vsechna_data:
                    posledni_radek = vsechna_data[-1]
                    if "Cena" in posledni_radek:
                        stara_cena = float(posledni_radek["Cena"])
                
                # 3. Vyhodnocení změny ceny
                if stara_cena is None or aktualni_cena != stara_cena:
                    ted = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    sheet.append_row([ted, aktualni_cena])
                    
                    # Příprava a odeslání emailu
                    msg = MIMEMultipart()
                    msg['From'] = odesilatel
                    msg['To'] = ", ".join(prijemci)
                    
                    if stara_cena is None:
                        msg['Subject'] = "Automatický hlídač aktivován"
                        telo = f"První načtená cena automatem na pozadí: {aktualni_cena} €"
                    else:
                        msg['Subject'] = "ZMĚNA CENY! (Automat)"
                        telo = f"Automat na pozadí zjistil změnu! Nová klubová cena je {aktualni_cena} € (původně {stara_cena} €)"
                    
                    msg.attach(MIMEText(telo, 'plain'))
                    
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(odesilatel, heslo)
                    server.send_message(msg)
                    server.quit()
                    print(f"[Automat] Cena aktualizována na {aktualni_cena} € a email odeslán.")
                else:
                    print("[Automat] Cena se nezměnila.")
            else:
                print("[Automat] Cenu se nepodařilo z webu vyčíst.")
                
        except Exception as e:
            # Chyby na pozadí tiskneme do interní konzole Streamlitu (Manage App -> Logs)
            print(f"❌ Chyba v automatické kontrole na pozadí: {e}")
        
        # Počkej 6 hodin (6 hodin * 60 minut * 60 sekund = 21600 sekund)
        time.sleep(21600)

# Bezpečné spuštění robota pouze jednou pro celý server
@st.cache_resource
def spustit_automaticky_hlidac():
    # Vytáhneme šifry ze secrets, abychom je bezpečně předali robotovi na pozadí
    gc_info = {
        "type": st.secrets["connections"]["gsheets"]["type"],
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": st.secrets["connections"]["gsheets"]["private_key"],
        "client_email": st.secrets["connections"]["gsheets"]["client_email"],
        "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"]
    }
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # Nastartování robota v samostatném vlákně (daemon=True zajistí, že neumře s uživatelem)
    t = threading.Thread(
        target=kontrola_na_pozadi, 
        args=(gc_info, spreadsheet_url, URL, HEADERS, ODESILATEL_EMAIL, HESLO_APLIKACE, PRIJEMCE_EMAIL),
        daemon=True
    )
    t.start()
    return True

# Spuštění hlídače
spustit_automaticky_hlidac()
