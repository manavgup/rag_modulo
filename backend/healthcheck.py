import http.client
import sys


def check_health() -> None:
    try:
        conn = http.client.HTTPConnection("localhost", 8000)  # Port needs to be aligned with one application uses
        conn.request("GET", "/api/health")
        response = conn.getresponse()
        if response.status == 200:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    check_health()
