import sys
import http.client

def check_health():
    try:
        conn = http.client.HTTPConnection('localhost', 5000)  # Port needs to be aligned with one application uses
        conn.request('GET', '/health')
        response = conn.getresponse()
        if response.status == 200:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        sys.exit(1)

if __name__ == '__main__':
    check_health()