# Mutua Esclusione a Token Ring — Sistema Distribuito (4 ATM)

Progetto per l'esame di **Intelligenza Artificiale Distribuita** (a.a. 2026) — **Salvatore Dimino** (`salvatore-dimino`).  
Implementazione di un algoritmo di **mutua esclusione distribuita ad anello logico (Token Ring)** su `localhost` (`127.0.0.1`) tramite socket TCP, senza memoria condivisa.

- **Repository:** https://github.com/salvatore-dimino/intelligenza-artificiale-distribuita-token-ring

## Architettura del Sistema

Il sistema è composto da **4 processi indipendenti** (`ATM1`, `ATM2`, `ATM3`, `ATM4`) collegati in un anello logico unidirezionale:

| Nodo | Indirizzo e Porta di Ascolto | Nodo Successivo | Operazione Predefinita |
| :--- | :--- | :--- | :--- |
| **ATM1** | `127.0.0.1:5001` | `ATM2` (`127.0.0.1:5002`) | Nessuna transazione (avvia token con saldo `1000`) |
| **ATM2** | `127.0.0.1:5002` | `ATM3` (`127.0.0.1:5003`) | Prelievo `200` → saldo `800` |
| **ATM3** | `127.0.0.1:5003` | `ATM4` (`127.0.0.1:5004`) | Deposito `100` → saldo `900` |
| **ATM4** | `127.0.0.1:5004` | `ATM1` (`127.0.0.1:5001`) | Prelievo `500` → saldo `400` |

### Funzionamento e Sezione Critica
- **Circolazione del Token:** solo il processo attualmente in possesso del messaggio JSON di tipo `TOKEN` ha il diritto di entrare in sezione critica.
- **Sezione Critica Atomica:** il possessore del token legge il saldo corrente, valida l'operazione (controllo importo positivo e disponibilità fondi per i prelievi), calcola il nuovo saldo, aggiorna lo stato del token e stampa il log prima di inoltrare il token al nodo successivo.
- **Sequenza attesa:** `1000` (`ATM1`) → `800` (`ATM2`) → `900` (`ATM3`) → `400` (`ATM4`), con mantenimento del saldo coerente (`400`) nei giri successivi.

## Istruzioni di Esecuzione

- **Linguaggio:** Python 3.x (verificato su CPython 3.15, Windows / PowerShell).
- **Dipendenze:** esclusivamente libreria standard Python (`socket`, `threading`, `json`, `sys`, `time`); nessuna installazione esterna richiesta.
- **Compilazione:** non necessaria (linguaggio interpretato).

Aprire **4 terminali separati**, posizionarsi nella cartella del progetto e lanciare i nodi in ordine (`ATM1` → `ATM4`):

```powershell
python token_ring_atm.py ATM1 --initial-token
python token_ring_atm.py ATM2
python token_ring_atm.py ATM3
python token_ring_atm.py ATM4