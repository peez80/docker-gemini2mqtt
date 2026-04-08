# gemini2mqtt

> Ein MQTT-zu-Gemini-AI-Bridge-Dienst, der Prompts über MQTT empfängt, sie an die Gemini AI weiterleitet und die Antwort zurück per MQTT sendet.

---

## Funktionsweise

```
MQTT Broker
  │
  ├─► Topic: MQTT_PROMPT_TOPIC   (Eingang)
  │       Nachrichtenformat: "response_topic|prompt"
  │
  └─► Topic: <response_topic>    (Ausgang)
          Inhalt: Antwort von Gemini AI
```

### Nachrichtenformat

Eingehende Nachrichten müssen zwei durch `|` getrennte Felder enthalten:

| Feld | Beschreibung | Beispiel |
|---|---|---|
| `response_topic` | MQTT-Topic für die Antwort | `home/ai/response` |
| `prompt` | Der an Gemini gesendete Prompt | `Was ist 2+2?` |

**Beispiel:**
```
home/ai/response|Was ist die Hauptstadt von Bayern?
```

---

## Konfiguration (Umgebungsvariablen)

Alle Einstellungen erfolgen über Umgebungsvariablen. Kopiere `.env.example` nach `.env` und passe die Werte an:

```bash
cp .env.example .env
```

| Variable | Standard | Pflicht | Beschreibung |
|---|---|---|---|
| `MQTT_HOST` | `localhost` | – | Hostname des MQTT-Brokers |
| `MQTT_PORT` | `1883` | – | Port des MQTT-Brokers |
| `MQTT_USERNAME` | – | – | MQTT-Benutzername |
| `MQTT_PASSWORD` | – | – | MQTT-Passwort |
| `MQTT_PROMPT_TOPIC` | `gemini2mqtt/prompt` | **Ja** | Topic für eingehende Prompts |
| `GEMINI_CLI_PATH` | `gemini` | – | Pfad zum Gemini-CLI-Binary |
| `GEMINI_MODEL` | `gemini-2.5-pro-preview-03-25` | – | Gemini-Modell |
| `GEMINI_MAX_CONCURRENT` | `2` | – | Max. gleichzeitige Gemini-Aufrufe |
| `GEMINI_TIMEOUT_SECONDS` | `120` | – | Timeout für Gemini-CLI-Aufruf in Sekunden |

---

## Deployment mit Docker

### Schnellstart

```bash
# 1. .env anlegen
cp .env.example .env
# (Werte in .env anpassen)

# 2. Image bauen und Container starten
docker compose up -d --build
```

### Logs ansehen

```bash
docker compose logs -f gemini2mqtt
```

### Container stoppen

```bash
docker compose down
```

---

## Lokale Entwicklung (ohne Docker)

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Umgebungsvariablen setzen
cp .env.example .env
# .env nach Bedarf anpassen

# Starten
python gemini2mqtt.py
```

> **Voraussetzung:** Die Gemini CLI muss lokal installiert und auf dem `PATH` verfügbar sein.  
> Installation: `npm install -g @google/gemini-cli`

---

## Authentifizierung (Gemini CLI)

Um sich mit der Gemini API zu authentifizieren, müssen die Credentials einmalig im Container erzeugt und in ein lokales Verzeichnis persistiert werden:

```bash
# Lokales Verzeichnis für Credentials anlegen
mkdir -p /pfad/zum/credentials-verzeichnis

# Container interaktiv mit Gemini CLI starten und Verzeichnis mounten
docker run -it --rm --entrypoint gemini \
  -v "/pfad/zum/credentials-verzeichnis:/root/.gemini" \
  peez/gemini2mqtt
```

Im interaktiven CLI:

1. Mit den Pfeiltasten zu **„Sign in with Google"** navigieren und bestätigen.
2. Die angezeigte URL kopieren und im Browser öffnen.
3. Den Google-Auth-Flow abschließen und den angezeigten Code zurück in das CLI einfügen.
4. Nach erfolgreicher Authentifizierung werden die Credentials in `/pfad/zum/credentials-verzeichnis` gespeichert.

Dieses Verzeichnis dann als Volume in `docker-compose.yml` einbinden, damit der Dienst die gespeicherten Credentials beim Start nutzt.

---

## Projektstruktur

```
docker-ai2mqtt/
├── gemini2mqtt.py       # Hauptanwendung
├── Dockerfile           # Docker-Image (Python + Gemini CLI)
├── docker-compose.yml   # Compose-Konfiguration
├── requirements.txt     # Python-Abhängigkeiten
├── .env.example         # Vorlage für Umgebungsvariablen
├── .dockerignore
├── .gitignore
└── spec.md              # Projektspezifikation
```
