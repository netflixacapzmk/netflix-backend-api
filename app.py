from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# PENTING: CORS benarkan request dari mana-mana domain (termasuk Firebase kau)
CORS(app) 

@app.route('/')
def home():
    return "Netflix Checker API is Running on Vercel!"

@app.route('/get-netflix-code', methods=['POST'])
def get_netflix_code():
    try:
        data = request.json
        order_id = data.get('id') # ID dari HTML (contoh: #00076511)

        if not order_id:
            return jsonify({'success': False, 'message': 'Tiada ID diberikan'}), 400

        # Setup Session (Supaya Cookie & Token disimpan dalam satu flow ini)
        session = requests.Session()
        
        # Header tipu supaya nampak macam browser sebenar
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.join-digitalworld.com/nf/get-code',
            'Origin': 'https://www.join-digitalworld.com'
        }

        print(f"[*] Memulakan proses untuk ID: {order_id}...")

        # LANGKAH 1: Ambil CSRF Token
        try:
            first_page = session.get('https://www.join-digitalworld.com/nf/get-code', headers=headers, timeout=10)
            soup = BeautifulSoup(first_page.text, 'html.parser')
            
            token_input = soup.find('input', {'name': '_token'})
            token = token_input['value'] if token_input else None

            if not token:
                print("[!] Gagal jumpa token.")
                # Cuba teruskan juga manalah tahu
        except Exception as e:
            print(f"[!] Error fetching token page: {str(e)}")
            token = None

        # LANGKAH 2: Submit Data
        payload = {
            '_token': token,
            'order_id': order_id
        }

        post_url = 'https://www.join-digitalworld.com/nf/submit-get-code'
        response = session.post(post_url, data=payload, headers=headers, timeout=15)

        print(f"[*] Status Hantar: {response.status_code}")

        # LANGKAH 3: Parse Result
        result_text = response.text
        
        # Cari 4 digit yang berdiri sendiri menggunakan Regex
        codes = re.findall(r'(?<!\d)\d{4}(?!\d)', result_text)
        
        found_code = None
        clean_id = order_id.replace('#', '') # Buang # kalau ada untuk comparison

        for code in codes:
            # Pastikan kod tu bukan sebahagian dari order ID
            if code not in clean_id:
                found_code = code
                break
        
        if found_code:
             return jsonify({
                 'success': True, 
                 'code': found_code,
                 'message': 'Kod berjaya diperolehi'
             })
        else:
             # Debugging: hantar sikit snippet HTML kalau gagal
             return jsonify({
                 'success': False, 
                 'message': 'Kod tidak dijumpai dalam respon server.',
                 'debug': result_text[:200] 
             })

    except Exception as e:
        print(f"[X] Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Vercel perlukan ini, tapi jangan risau dia takkan run app.run() di production
if __name__ == '__main__':
    app.run(port=5000)