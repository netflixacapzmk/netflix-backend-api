from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import time

app = Flask(__name__)
CORS(app) 

# --- CONFIGURATION ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.join-digitalworld.com/',
    'Connection': 'keep-alive'
}

def cf_decode_email(encoded_string):
    """Decode Cloudflare protected emails"""
    try:
        r = int(encoded_string[:2], 16)
        email = ''.join([chr(int(encoded_string[i:i+2], 16) ^ r) for i in range(2, len(encoded_string), 2)])
        return email
    except:
        return ""

def clean_html_text(html_content):
    """Convert HTML to clean text for parsing"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Decode CF emails first
        for el in soup.select('[data-cfemail]'):
            decoded = cf_decode_email(el['data-cfemail'])
            el.replace_with(decoded)
            
        # Remove scripts and styles
        for script in soup(["script", "style", "meta", "noscript"]):
            script.extract()
            
        text = soup.get_text(separator=' ')
        return " ".join(text.split())
    except:
        return html_content

@app.route('/')
def home():
    return "Netflix Checker Backend V2 is Running!"

@app.route('/check-account', methods=['POST'])
def check_account():
    data = request.json
    order_id = data.get('id')
    
    if not order_id:
        return jsonify({'status': 'error', 'message': 'No ID provided'}), 400

    servers = [
        {"name": "STABLE", "url": f"https://www.join-digitalworld.com/nf/stable/access/web{order_id}"},
        {"name": "PREMIUM", "url": f"https://www.join-digitalworld.com/nf/premium/access/web{order_id}"},
        {"name": "ACCESS", "url": f"https://www.join-digitalworld.com/nf/access/web{order_id}"}
    ]

    session = requests.Session()
    
    for server in servers:
        print(f"[*] Scanning {server['name']} for {order_id}...")
        try:
            response = session.get(server['url'], headers=HEADERS, timeout=10)
            
            # Anti-bot check
            if "Verify you are human" in response.text or response.status_code == 403:
                print(f"[!] Bot detection on {server['name']}")
                continue
                
            clean_text = clean_html_text(response.text)
            
            # Basic validation
            if len(clean_text) < 50 or "Not Found" in clean_text or "Error" in clean_text or "Sorry" in clean_text:
                continue

            # --- EXTRACTION LOGIC (Ported from JS) ---
            
            # 1. Email
            email = "N/A"
            email_match = re.search(r'Email\s*.{0,50}?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', clean_text, re.IGNORECASE)
            if email_match:
                email = email_match.group(1)
            else:
                # Fallback extraction
                all_emails = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', clean_text)
                valid_emails = [e for e in all_emails if "example" not in e and "sentry" not in e]
                if valid_emails:
                    email = valid_emails[0]

            # 2. Country
            country = "Unknown"
            country_match = re.search(r'Country\s*[:|-]?\s*(.*?)(?=\s*(?:Profile|Validity|Email|$|\(no need vpn\)))', clean_text, re.IGNORECASE)
            if country_match:
                country = country_match.group(1).strip()
            
            # 3. Validity
            validity = "Unknown"
            validity_match = re.search(r'Validity\s*(?:Left)?\s*[:|-]?\s*(.*?)(?=\s*(?:Profile|Email|$))', clean_text, re.IGNORECASE)
            if validity_match:
                raw_validity = validity_match.group(1).strip()
                validity = re.split(r'Profile|Email|Status', raw_validity, flags=re.IGNORECASE)[0].strip()

            # 4. Profiles
            profiles = ["User"]
            profile_match = re.search(r'Profile\s*[:|-]?\s*([^\n\r<]+)', clean_text, re.IGNORECASE)
            if profile_match:
                p_text = profile_match.group(1).strip()
                # Cleaning logic specific to server types
                if "DO NOT LOGOUT" in p_text.upper():
                    idx = p_text.upper().find("DO NOT LOGOUT")
                    p_text = p_text[:idx].strip()
                
                # Split if comma separated
                if ',' in p_text:
                    profiles = [p.strip() for p in p_text.split(',')]
                else:
                    profiles = [p_text]

            # Warning Check
            warning_text = ""
            if "DO NOT USE PASSWORD" in clean_text.upper():
                warning_text = "(DO NOT USE PASSWORD TO SIGN-IN) Please use sign-in with code to login."

            # Final check if extraction worked
            if email != "N/A" or country != "Unknown":
                return jsonify({
                    'status': 'found',
                    'serverName': server['name'],
                    'data': {
                        'email': email,
                        'country': country,
                        'validity': validity,
                        'profiles': profiles,
                        'warningText': warning_text
                    }
                })

        except Exception as e:
            print(f"[X] Error scanning {server['name']}: {e}")
            continue

    return jsonify({'status': 'missing', 'message': 'Not found in any database'})

@app.route('/get-netflix-code', methods=['POST'])
def get_netflix_code():
    # ... (KEKALKAN KOD GET CODE YANG KAU DAH ADA SBLM NI KAT SINI) ...
    # SAYA SINGKATKAN UTK CONTOH, TAPI PASTIKAN KOD LAMA ADA
    try:
        data = request.json
        order_id = data.get('id')
        if not order_id: return jsonify({'success': False}), 400
        
        session = requests.Session()
        headers = HEADERS.copy()
        
        # 1. Get Token
        try:
            r1 = session.get('https://www.join-digitalworld.com/nf/get-code', headers=headers, timeout=10)
            soup = BeautifulSoup(r1.text, 'html.parser')
            token = soup.find('input', {'name': '_token'})['value']
        except:
            return jsonify({'success': False, 'message': 'Failed to connect'}), 500

        # 2. Post
        payload = {'_token': token, 'order_id': order_id}
        r2 = session.post('https://www.join-digitalworld.com/nf/submit-get-code', data=payload, headers=headers, timeout=15)
        
        # 3. Find Code
        codes = re.findall(r'(?<!\d)\d{4}(?!\d)', r2.text)
        clean_id = order_id.replace('#', '')
        found = next((c for c in codes if c not in clean_id), None)
        
        if found:
            return jsonify({'success': True, 'code': found})
        else:
            return jsonify({'success': False, 'message': 'Code not found'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)