import os
import json
import requests
from bs4 import BeautifulSoup
import sys
from datetime import datetime
import pytz

# --- CONFIGURAZIONE ---
HISTORY_FILE = "history_radar.json"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("[!] Errore: Token o Chat ID mancanti.")
        return
    
    send_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    requests.post(send_url, data=payload)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                # Assicuriamoci che tutte le chiavi esistano
                for key in ["lum_master", "lum_jobs", "uniba", "regione_puglia"]:
                    if key not in data:
                        data[key] = []
                return data
        except:
            pass
    return {"lum_master": [], "lum_jobs": [], "uniba": [], "regione_puglia": []}

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

def check_targets():
    history = load_history()
    
    # Gestione Fuso Orario (Importato dal tuo LUM Sniper)
    utc_now = datetime.now(pytz.utc) 
    rome_tz = pytz.timezone('Europe/Rome') 
    rome_now = utc_now.astimezone(rome_tz) 
    now_str = rome_now.strftime("%d/%m/%Y alle %H:%M")
    
    updated = False

    # 1. TARGET LUM MASTER (Adattato dal tuo LUM Sniper)
    print("[*] Scansione LUM Master...")
    try:
        res = requests.get("https://management.lum.it/bandi-e-avvisi/", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Cerchiamo i link diretti per evitare la risalita del DOM
        links = soup.find_all('a', href=True)
        for a in links:
            href = a['href'].strip()
            text = a.get_text(strip=True)
            
            if "master" in href.lower() or "executive" in href.lower():
                if href not in history["lum_master"]:
                    msg = f"🎯 <b>[LUM] NUOVO MASTER RILEVATO!</b>\n\n📝 <b>{text}</b>\n🔗 <a href='{href}'>Vai al bando</a>\n\n<i>Rilevato il: {now_str}</i>"
                    send_telegram_alert(msg)
                    history["lum_master"].append(href)
                    updated = True
    except Exception as e:
        print(f"[!] Errore LUM Master: {e}")

    # 2. TARGET LUM JOBS (Dal tuo Radar Opportunità)
    print("[*] Scansione LUM Job Placement...")
    try:
        res = requests.get("https://www.lum.it/job-opportunities/", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        spans = soup.find_all('span')
        for span in spans:
            if "aperto" in span.get_text(strip=True).lower():
                card = span.find_parent(['div', 'article', 'li'])
                if card:
                    link_tag = card.find('a', href=True)
                    if link_tag:
                        link = link_tag['href']
                        if not link.startswith('http'):
                            link = "https://www.lum.it" + link
                        
                        if link not in history["lum_jobs"]:
                            msg = f"💼 <b>[LUM PLACEMENT] NUOVA OFFERTA DI LAVORO!</b>\n\n🔗 <a href='{link}'>Vedi dettagli offerta</a>\n\n<i>Rilevata il: {now_str}</i>"
                            send_telegram_alert(msg)
                            history["lum_jobs"].append(link)
                            updated = True
    except Exception as e:
        print(f"[!] Errore LUM Job Placement: {e}")

    # 3. TARGET UNIBA ALTA FORMAZIONE (Dal tuo Radar Opportunità)
    print("[*] Scansione UniBa Alta Formazione...")
    try:
        res = requests.get("https://www.uniba.it/it/didattica/corsi-universitari-di-formazione-finalizzata/corsi-e-progetti-di-alta-formazione", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        keywords = ["2026/2027", "2026-2027", "2027", "patti territoriali", "short master"]
        
        for link_tag in links:
            testo = link_tag.get_text(strip=True).lower()
            href = link_tag['href'].lower()
            
            if any(kw in testo for kw in keywords) or any(kw in href for kw in keywords):
                link_reale = link_tag['href']
                if not link_reale.startswith('http'):
                    link_reale = "https://www.uniba.it" + link_reale
                    
                if link_reale not in history["uniba"]:
                    titolo_pulito = link_tag.get_text(strip=True)
                    msg = f"🎓 <b>[UNIBA] NUOVO CORSO / SHORT MASTER!</b>\n\n📝 <b>{titolo_pulito}</b>\n🔗 <a href='{link_reale}'>Apri la pagina</a>\n\n<i>Rilevato il: {now_str}</i>"
                    send_telegram_alert(msg)
                    history["uniba"].append(link_reale)
                    updated = True
    except Exception as e:
        print(f"[!] Errore UniBa: {e}")

    # 4. TARGET REGIONE PUGLIA (Nuovo - Pass Laureati / Borse)
    print("[*] Scansione Regione Puglia (Bandi)...")
    try:
        res = requests.get("https://por.regione.puglia.it/it/bandi", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Cerca link generici ai bandi
        links = soup.find_all('a', href=True)
        keywords_regione = ["pass laureati", "alta formazione", "ritorno al futuro", "master"]
        
        for link_tag in links:
            testo = link_tag.get_text(strip=True).lower()
            href = link_tag['href'].lower()
            
            if any(kw in testo for kw in keywords_regione):
                link_reale = link_tag['href']
                if not link_reale.startswith('http'):
                    link_reale = "https://por.regione.puglia.it" + link_reale
                
                if link_reale not in history["regione_puglia"]:
                    titolo_pulito = link_tag.get_text(strip=True)
                    msg = f"🏛 <b>[REGIONE PUGLIA] NUOVO BANDO FORMAZIONE!</b>\n\n📝 <b>{titolo_pulito}</b>\n🔗 <a href='{link_reale}'>Apri la pagina</a>\n\n<i>Rilevato il: {now_str}</i>"
                    send_telegram_alert(msg)
                    history["regione_puglia"].append(link_reale)
                    updated = True
    except Exception as e:
         print(f"[!] Errore Regione Puglia: {e}")

    if updated:
        save_history(history)
        print("[*] Database aggiornato.")
    else:
        print("[*] Nessuna variazione rilevata nei bersagli.")

if __name__ == "__main__":
    check_targets()
