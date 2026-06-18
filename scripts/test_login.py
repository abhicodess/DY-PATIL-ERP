import urllib.request
import urllib.parse
from http.cookiejar import CookieJar

cj = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Get csrf token first
r = opener.open('http://127.0.0.1:5000/login')
text = r.read().decode('utf-8')
csrf = text.split('name="_csrf" value="')[1].split('"')[0]

data = urllib.parse.urlencode({
    'role': 'admin',
    'username': 'admin',
    'password': 'admin123',
    '_csrf': csrf
}).encode('ascii')

try:
    r2 = opener.open('http://127.0.0.1:5000/login', data=data)
    print('Url after login:', r2.url)
    if 'Invalid admin credentials' in r2.read().decode('utf-8'):
        print('Login failed: Invalid credentials.')
    else:
        print('Login success or other response.')
except Exception as e:
    print('Error:', e)
