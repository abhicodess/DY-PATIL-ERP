import urllib.request
import urllib.parse
from http.cookiejar import CookieJar

cj = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def test_login(role, username, password):
    print(f"Testing login for {role} ({username})...")
    try:
        # Get csrf token first
        r = opener.open('http://127.0.0.1:5000/login')
        text = r.read().decode('utf-8')
        if 'name="_csrf"' not in text:
            print("Error: CSRF token not found in login page.")
            return
        csrf = text.split('name="_csrf" value="')[1].split('"')[0]
        
        data = urllib.parse.urlencode({
            'role': role,
            'username': username,
            'password': password,
            '_csrf': csrf
        }).encode('ascii')
        
        r2 = opener.open('http://127.0.0.1:5000/login', data=data)
        final_url = r2.url
        content = r2.read().decode('utf-8')
        
        print('Final URL:', final_url)
        if 'Invalid' in content:
            print('Login failed: Invalid credentials or error message found in page.')
            # Extract the actual error message
            if 'al-err' in content:
                err = content.split('al-err')[1].split('>', 1)[1].split('</div>')[0]
                print('Error message:', err)
        elif final_url.endswith('/login'):
             print('Login failed: Still on login page without error message?')
        else:
            print('Login Success!')
    except urllib.error.HTTPError as e:
        print(f'HTTP Error {e.code}: {e.reason}')
        print(e.read().decode('utf-8'))
    except Exception as e:
        print('Error:', e)

if __name__ == "__main__":
    test_login('admin', 'admin', 'admin123')
    test_login('student', 'B01', 'student123')
