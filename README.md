# STM Cast — Systemübersicht, Discovery & Debugging

Dieses Repository enthält einen FastAPI‑Server (Windows) und einen Python‑Client (Raspberry Pi). Die Komponenten finden sich per UDP‑Discovery (Broadcast) auf den Ports 5001–5005; danach kommuniziert der Client per HTTP mit dem Server.

Dieses README erklärt:

- Architektur und Datenfluss (einfach und technisch)
- Relevante Code‑Snippets (Server + Client Discovery, Herzschlag)
- Warum Discovery in manchen Netzen versagt
- Stärken, Schwächen und bekannte Fixes
- Debug‑Pipeline (Linux / Windows) mit Kommandos, die du nacheinander abarbeiten kannst

Siehe auch: `docs/network_report.md` für eine kürzere, bildhafte Darstellung.

---

## 1) Architektureller Überblick (Kurz)

Mermaid: Topologie (vereinfachte Sicht)

```mermaid
flowchart LR
  C[Client (RPi)] -->|UDP Discovery (Broadcast)| AP[Access Point / Router]
  AP -->|LAN| S[Server (Windows)]
  C -->|HTTP| S
```

Kurz: Der Client sendet ein UDP‑Broadcast (Discovery). Wenn der Server die Anfrage empfängt, sendet er als UDP‑Unicast eine JSON‑Antwort zurück mit der IP, unter der er erreichbar ist. Der Client baut daraus `http://{ip}:{port}` und nutzt HTTP für weitere Aktionen.

---

## 2) Relevante Code‑Snippets

### Server — Discovery (Wichtiges Muster)

```py
import socket, json

def get_reachable_ip_for(client_addr):
    # UDP connect trick: kein Traffic, nur Routing/Interface-Ermittlung
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((client_addr[0], client_addr[1]))
        local_ip = s.getsockname()[0]
    finally:
        s.close()
    return local_ip

def handle_discovery_request(data, client_addr, udp_sock):
    # data geprüft
    my_ip = get_reachable_ip_for(client_addr)
    reply = {"service": "stedgeai-api", "ip": my_ip, "port": 5000}
    udp_sock.sendto(json.dumps(reply).encode(), client_addr)
```

### Client — Discovery (Kernlogik)

```py
import socket, json, time

def discover_server(timeout=5, retries=3):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", 0))
    sock.settimeout(timeout)

    request = {"action":"discover","service":"stedgeai-api"}
    ports = [5001,5002,5003]
    for _ in range(retries):
        for p in ports:
            sock.sendto(json.dumps(request).encode(), ("<broadcast>", p))
            try:
                data, addr = sock.recvfrom(2048)
                resp = json.loads(data.decode())
                return f"http://{resp['ip']}:{resp['port']}"
            except socket.timeout:
                continue
        # optional: directed broadcast or unicast probe here
    return None
```

### Heartbeat (einfach)

```py
import requests

def heartbeat(server_url):
    try:
        r = requests.get(f"{server_url}/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False
```

### Safe handling in `generate_code` response

```py
result = response.json()
name = result.get("name")
if name:
    self.generated.append(name)
else:
    logger.error("generate_code: missing name in result: %s", result)
```

---

## 3) Warum Discovery in manchen Netzen fehlschlägt

- Broadcast‑Filtering / Client Isolation: WLAN/APs und Campus‑Netze isolieren oft Clients oder filtern Broadcasts.
- Multihoming: Server mit mehreren Interfaces liefert eventuell eine lokale IP, die der Client nicht erreichen kann.
- Firewall/AV: Eingehende UDP‑Pakete können blockiert werden.

Analogie: Broadcast = laut im Flur rufen. In kleinen Häusern hört dich jeder; in großen Büros sind Türen oder Regeln, die das Rufen blockieren.

---

## 4) Stärken, Schwächen, Fixes

- Stärken:
  - Einfach, keine Infrastruktur nötig
  - Schnell und leichtgewichtig

- Schwächen:
  - Abhängig vom Netzwerk (Broadcast‑Filtering)
  - Probleme bei Multihoming

- Bekannte Fixes:
  - Server sendet die tatsächlich erreichbare IP (UDP connect trick)
  - Client probiert directed broadcast + unicast probe
  - Persistenter Fallback: letzte erfolgreiche Server‑URL cachen
  - Alternative: mDNS/DNS‑SD oder zentraler Registry‑Server

---

## 5) Debug‑Pipeline (Schritt für Schritt)

Ziel: systematisch prüfen, ob Discovery‑Pakete ankommen und Antworten gesendet werden.

### Raspberry Pi (Linux)

```bash
# 1) Zeige Outbound/Inbound UDP Discovery
sudo tcpdump -n -i wlan0 udp port 5001 -vv

# 2) Sende manuell einen Broadcast
python3 - <<'PY'
import socket,json
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
s.sendto(json.dumps({"action":"discover","service":"stedgeai-api"}).encode(), ("192.168.199.255",5001))
s.close()
PY

# 3) Netzwerkinfos
ip addr show wlan0
ip route show
```

### Windows (Server)

```powershell
# 1) Zeige UDP Endpoints für Port 5001
Get-NetUDPEndpoint -LocalPort 5001

# 2) Zeige Prozess für den Port
Get-Process -Id (Get-NetUDPEndpoint -LocalPort 5001).OwningProcess

# 3) Paketaufzeichnung: pktmon
pktmon start --capture --comp nics
# reproduce traffic, then
pktmon stop
pktmon format PktMon.etl -o pktmon.pcapng

# 4) Analysiere pcapng mit tshark
tshark -r pktmon.pcapng -Y "udp.port==5001" -V
```

### Allgemeine Checks

```bash
# Server (Linux): socket bind prüfen
ss -u -lpn | grep 5001

# Windows: offene Sockets
netstat -ano | findstr ":5001"

# Firewall Regeln (Windows PowerShell)
Get-NetFirewallRule | Where-Object DisplayName -Like '*stedgeai*'
```

Fehleranalyse‑Workflow (empfohlen):

1. Auf Pi: starte tcpdump und sende Discovery.
2. Wenn tcpdump sendet, aber keine Reply: auf Windows pktmon/tshark prüfen, ob Server das Paket sieht.
3. Wenn Windows nichts sieht: Firewall/AP/Router prüfen (AP Logs oder Konfig).
4. Wenn Windows sieht, aber Serverlog zeigt keinen Handler: prüfe Server‑Process/Mehrfachstarts/Permissions.

---

## 6) Nächste Schritte (optional)

- Ich kann die Mermaid‑Diagramme als PNGs in `docs/` exportieren (zeigt sie überall an).
- Ich kann ein kurzes Debug‑Script hinzufügen, das die obigen Befehle automatisiert und Log‑Schnappschüsse sammelt.
- Ich kann `server/discovery.py` mit erklärenden Kommentaren versehen (z.B. zum UDP‑connect trick).

Sag mir, welche der drei Optionen du möchtest — ich implementiere sie dann.
# STM Cast — Kurzüberblick

Dieses Repository enthält einen kleinen Server (Windows, FastAPI) und einen Raspberry Pi Client, die per UDP‑Discovery zueinanderfinden. Die Discovery benutzt UDP‑Broadcasts (Ports 5001–5005). Dieses Repo enthält außerdem Debug‑Werkzeuge und eine Dokumentation zur Netzwerkanalyse.

Kurze Links:

- Detaillierter Netzwerkbericht und einfache Diagramme: `docs/network_report.md`
- LaTeX Bericht: `docs/report.tex`

Problem & Lösung in einem Satz:
- Problem: Discovery‑Broadcasts wurden in manchen Schul‑Netzen gefiltert.
- Lösung: Server antwortet mit der tatsächlich erreichbaren IP; Client probiert gerichteten Broadcast und Unicast‑Probe als Fallback.

Mehr Details und Anleitungen findest du in `docs/network_report.md`.

