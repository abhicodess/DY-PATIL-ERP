import urllib.request
import urllib.parse
from http.cookiejar import CookieJar

cj = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def test_login(role, username, password):
    print(f"Testing login for {role} ({username})...")
    try:
        r = opener.open('http://127.0.0.1:5000/login')
        text = r.read().decode('utf-8')
        csrf = text.split('name="_csrf" value="')[1].split('"')[0]
        data = urllib.parse.urlencode({'role': role,'username': username,'password': password,'_csrf': csrf}).encode('ascii')
        r2 = opener.open('http://127.0.0.1:5000/login', data=data)
        print('Final URL:', r2.url)
        if 'Invalid' in r2.read().decode('utf-8'): print('Login failed.')
        else: print('Login Success!')
    except Exception as e: print('Error:', e)

if __name__ == "__main__":
    test_login('faculty', 'nirmala.chede@dyptc.edu.in', 'faculty123')
