# gemini2mqtt

> Ein MQTT-zu-Gemini-AI-Bridge-Dienst, der Prompts über MQTT empfängt, sie an die Gemini AI (Standard oder Vertex AI) weiterleitet und die Antwort zurück per MQTT sendet.

---

## Funktionsweise

```
MQTT Broker
  │
  ├─► Topic: MQTT_PROMPT_TOPIC   (Eingang)
  │       Nachrichtenformat: "response_topic|use_vertex_api|prompt"
  │
  └─► Topic: <response_topic>    (Ausgang)
          Inhalt: Antwort von Gemini AI
```

### Nachrichtenformat

Eingehende Nachrichten müssen drei durch `|` getrennte Felder enthalten:

| Feld | Beschreibung | Beispiel |
|---|---|---|
| `response_topic` | MQTT-Topic für die Antwort | `home/ai/response` |
| `use_vertex_api` | Vertex AI verwenden? (`true`/`false`) | `false` |
| `prompt` | Der an Gemini gesendete Prompt | `Was ist 2+2?` |

**Beispiel:**
```
home/ai/response|false|Was ist die Hauptstadt von Bayern?
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
| `VERTEX_CLI_PATH` | `gemini` | – | Pfad zum Vertex-AI-CLI-Binary |
| `VERTEX_PROJECT` | – | – | Google Cloud Projekt-ID (für Vertex AI) |
| `VERTEX_LOCATION` | `europe-west3` | – | Google Cloud Region (für Vertex AI) |

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

## Vertex AI vs. Standard-Gemini

| | Standard Gemini | Vertex AI |
|---|---|---|
| `use_vertex_api` im Prompt | `false` | `true` |
| Quota | Gemini-Standard-Quota | Vertex-AI-Quota |
| Datenschutz | Daten können für Training genutzt werden | Keine Nutzung für Training (geeignet für sensible Daten) |
| Erforderliche Konfiguration | – | `VERTEX_PROJECT`, `VERTEX_LOCATION` |

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
