import socket

def run_sniffer(port=5001):
    # Erstelle UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Erlaube Mehrfachnutzung des Ports
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(('', port))
        print(f"📡 Sniffer aktiv auf Port {port}... Warte auf Broadcasts.")
        print("Drücke Strg+C zum Beenden.")
        
        while True:
            data, addr = sock.recvfrom(1024)
            print(f"✅ PAKET ERHALTEN von {addr}: {data.decode()}")
    except Exception as e:
        print(f"❌ Fehler: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    run_sniffer(5001)