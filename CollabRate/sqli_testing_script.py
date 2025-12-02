import requests

def main():
    print("Running SQL injection tests...")
    payloads = ["' OR '1'='1", "' OR 1=1--", "'; DROP TABLE users; --"]

    for p in payloads:
        print(f"\nTesting payload: {p}")
        try:
            r = requests.get("http://127.0.0.1:8000/dashboard/?q=" + p)
            print("Status:", r.status_code)
            print("Response:", r.text[:200])
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    main()
