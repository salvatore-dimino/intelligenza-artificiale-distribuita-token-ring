import json
import socket
import sys
import threading
import time

HOST = "127.0.0.1"

RING_CONFIG = {
    "ATM1": {"port": 5001, "next": ("ATM2", 5002)},
    "ATM2": {"port": 5002, "next": ("ATM3", 5003)},
    "ATM3": {"port": 5003, "next": ("ATM4", 5004)},
    "ATM4": {"port": 5004, "next": ("ATM1", 5001)},
}

# Piano di transazioni predefinito come da esempio della traccia:
# ATM1: nessuna transazione; ATM2: prelievo 200; ATM3: deposito 100; ATM4: prelievo 500
DEFAULT_TX = {
    "ATM1": None,
    "ATM2": ("PRELIEVO", 200),
    "ATM3": ("DEPOSITO", 100),
    "ATM4": ("PRELIEVO", 500),
}


def log(atm_id: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{atm_id}] {msg}", flush=True)


def send_message(target_port: int, payload: dict) -> None:
    # Invia un singolo messaggio JSON tramite connessione TCP su localhost
    raw = (json.dumps(payload) + "\n").encode("utf-8")
    while True:
        try:
            with socket.create_connection((HOST, target_port), timeout=5) as sock:
                sock.sendall(raw)
            return
        except ConnectionRefusedError:
            # Attende che il nodo successivo sia in ascolto all'avvio
            time.sleep(0.3)


def execute_critical_section(atm_id: str, token_data: dict, tx: tuple | None) -> dict:
    # Sezione critica: lettura, validazione, aggiornamento, scrittura e log atomici
    current_balance = token_data["balance"]

    if tx is None:
        log(atm_id, f"Nessuna transazione da eseguire. Saldo corrente: {current_balance}")
        return token_data

    op_type, amount = tx
    log(atm_id, f"INIZIO TRANSAZIONE -> {op_type} {amount} (saldo letto: {current_balance})")

    # 1-4. Lettura, validazione, aggiornamento e scrittura del nuovo saldo
    if op_type == "PRELIEVO":
        if amount > 0 and current_balance >= amount:
            new_balance = current_balance - amount
            status = "APPROVATA"
        else:
            new_balance = current_balance
            status = "RIFIUTATA (fondi insufficienti o importo non valido)"
    elif op_type == "DEPOSITO":
        if amount > 0:
            new_balance = current_balance + amount
            status = "APPROVATA"
        else:
            new_balance = current_balance
            status = "RIFIUTATA (importo non valido)"
    else:
        new_balance = current_balance
        status = "RIFIUTATA (operazione sconosciuta)"

    token_data["balance"] = new_balance
    token_data["history"].append({
        "atm": atm_id,
        "op": op_type,
        "amount": amount,
        "status": status,
        "balance_after": new_balance,
    })

    # Simula breve elaborazione in sezione critica per rendere visibile la mutua esclusione
    time.sleep(1.0)

    # 5. Registrazione (log) finale della transazione
    log(atm_id, f"FINE TRANSAZIONE [{status}]. Saldo aggiornato: {new_balance}")
    return token_data


def run_node(atm_id: str, has_initial_token: bool) -> None:
    cfg = RING_CONFIG[atm_id]
    listen_port = cfg["port"]
    next_id, next_port = cfg["next"]
    pending_tx = DEFAULT_TX.get(atm_id)
    tx_done = False

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, listen_port))
    server_sock.listen(8)

    log(atm_id, f"In ascolto su {HOST}:{listen_port} | Successore: {next_id} ({HOST}:{next_port})")

    def handle_token(token_payload: dict) -> None:
        nonlocal tx_done
        log(atm_id, f"TOKEN RICEVUTO (saldo nel token: {token_payload['balance']})")

        tx_to_run = None
        if pending_tx is not None and not tx_done:
            tx_to_run = pending_tx
            tx_done = True

        updated_token = execute_critical_section(atm_id, token_payload, tx_to_run)

        time.sleep(0.8)
        log(atm_id, f"TOKEN INOLTRATO a {next_id} (saldo: {updated_token['balance']})")
        send_message(next_port, updated_token)

    def listener_loop() -> None:
        while True:
            conn, _ = server_sock.accept()
            with conn:
                data = b""
                while not data.endswith(b"\n"):
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                if data:
                    msg = json.loads(data.decode("utf-8").strip())
                    if msg.get("type") == "TOKEN":
                        handle_token(msg)

    t = threading.Thread(target=listener_loop, daemon=True)
    t.start()

    if has_initial_token:
        time.sleep(1.5)
        initial_token = {
            "type": "TOKEN",
            "balance": 1000,
            "history": [],
        }
        log(atm_id, "Possiede il TOKEN iniziale (Saldo iniziale: 1000)")
        handle_token(initial_token)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log(atm_id, "Arresto nodo.")
        server_sock.close()


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in RING_CONFIG:
        print("Uso: python token_ring_atm.py <ATM1|ATM2|ATM3|ATM4> [--initial-token]")
        sys.exit(1)
    node_name = sys.argv[1]
    initial = "--initial-token" in sys.argv[2:]
    run_node(node_name, initial)