from datetime import datetime

def print_request_start(endpoint, method="POST"):
    print("\n")
    print(f"🔵 REQUEST START:   {method} {endpoint}")
    print(f"🔵 Time: {datetime.now().strftime('%H:%M:%S')}")
   
def print_request_end(endpoint):
    print(f"✅ REQUEST END: {endpoint}")

def print_ascii():
    
    try:
        with open("server/utils/art.txt", "r") as f:
            ascii_art = f.read()
            print(ascii_art)

    except FileNotFoundError:
        print("ASCII art file not found.")