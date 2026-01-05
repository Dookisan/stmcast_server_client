from datetime import datetime

def print_request_start(endpoint, method="POST"):
    print("\n")
    print(f"🔵 REQUEST START:   {method} {endpoint}")
    print(f"🔵 Time: {datetime.now().strftime('%H:%M:%S')}")
   
def print_request_end(endpoint):
    print(f"✅ REQUEST END: {endpoint}")