import os
import json
import requests
from bs4 import BeautifulSoup
import sys
from datetime import datetime

# --- CONFIGURAZIONE RADAR ---
URL_LUM_JOBS = "https://www.lum.it/job-opportunities/"
URL_UNIBA = "https://www.uniba.it/it/didattica/corsi-universitari-di-formazione-finalizzata/corsi-e-progetti-di-alta-formazione"

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
                if isinstance(data, dict):
                    return data
        except:
            pass
    return {"lum_jobs": [], "uniba": []}

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

def check_targets():
    history = load_history()
    now_str = datetime.now().strftime("%d/%m/%Y alle %H:%M")
    updated = False

    # TARGET 1: LUM JOB PLACEMENT
    print(f"[*] Scansione LUM Job Placement...")
    try:
        res = requests.get(URL_LUM_JOBS, headers=HEADERS, timeout=15)
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

    # TARGET 2: UNIBA ALTA FORMAZIONE
    print(f"[*] Scansione UniBa Alta Formazione...")
    try:
        res = requests.get(URL_UNIBA, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        keywords = ["2026/2027", "2026-2027", "2027", "patti territoriali"]
        
        for link_tag in links:
            testo = link_tag.get_text(strip=True).lower()
            href = link_tag['href'].lower()
            
            is_target = any(kw in testo for kw in keywords) or any(kw in href for kw in keywords)
            
            if is_target:
                link_reale = link_tag['href']
                if not link_reale.startswith('http'):
                    link_reale = "https://www.uniba.it" + link_reale
                    
                if link_reale not in history["uniba"]:
                    titolo_pulito = link_tag.get_text(strip=True)
                    msg = f"🎓 <b>[UNIBA] NUOVO CORSO / PATTI TERRITORIALI!</b>\n\n📝 <b>{titolo_pulito}</b>\n🔗 <a href='{link_reale}'>Apri la pagina</a>\n\n<i>Rilevato il: {now_str}</i>"
                    send_telegram_alert(msg)
                    history["uniba"].append(link_reale)
                    updated = True
    except Exception as e:
        print(f"[!] Errore UniBa: {e}")

    if updated:
        save_history(history)
        print("[*] Database aggiornato.")
    else:
        print("[*] Nessuna variazione rilevata nei 2 bersagli.")

if __name__ == "__main__":
    check_targets()
