# Agent Guidelines

## Test-Driven Development (TDD) Workflow

Bei allen Code-Änderungen und Neuimplementierungen **muss** strikt nach dem **TDD-Ansatz** (Test-Driven Development) vorgegangen werden:

1. **Phase Rot (Red):** 
   - Zuerst einen fehlschlagenden Test schreiben, der das gewünschte Verhalten oder die Funktion beschreibt.
   - Den Test ausführen und bestätigen, dass er erwartungsgemäß fehlschlägt.

2. **Phase Grün (Green):**
   - Nur so viel Code implementieren, wie nötig ist, um den Test erfolgreich zum Bestehen zu bringen.
   - Den Test erneut ausführen und sicherstellen, dass er grün ist.

3. **Refactoring:**
   - Nach dem erfolgreichen Test immer einen Refactoring-Schritt durchführen.
   - Code aufräumen, Struktur und Lesbarkeit verbessern oder Redundanzen entfernen.
   - Anschließend sicherstellen, dass alle Tests weiterhin grün bleiben.

## Planungspflicht für TDD

- Es muss **immer** sichergestellt werden, dass dieser TDD-Ansatz (Phase Rot, Grün, Refactoring) in allen erstellten Plänen/Tasks explizit als Vorgehen beschrieben und eingeplant wird.

## Test-Ausführung (Test Execution)

Alle Tests befinden sich im Ordner `tests/` und nutzen `pytest` sowie `testcontainers` (für den MQTT Broker).

> [!IMPORTANT]
> **Pflicht zur Test-Ausführung im Docker-Container:**
> Tests **müssen IMMER via Docker-Container** ausgeführt werden, um die reale Produktionsumgebung und Abhängigkeiten (inklusive `agy`-Installation und Container-Dateipfade) bestmöglich widerzuspiegeln.

### 1. Docker-Image bauen
Vor der Testausführung das Test-Image aktualisieren:
```bash
docker build -t gemini2mqtt:test .
```

### 2. Standard Unit-Tests (Mocked API) im Docker-Container
Führt alle verlässlichen und schnellen Unit-Tests ohne externe API-Aufrufe isoliert im Container aus:
```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /root/.gemini:/root/.gemini \
  -v /apps:/app \
  -w /app \
  --entrypoint bash \
  gemini2mqtt:test \
  -c "pip install uv && uv run pytest -v -m 'not e2e'"
```

### 3. End-to-End Tests (Real API / agy CLI) im Docker-Container
Führt E2E-Tests aus (z. B. mit echter Gemini API oder lokaler `agy` CLI und Dateikontext):
```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /root/.gemini:/root/.gemini \
  -v /apps:/app \
  -w /app \
  --entrypoint bash \
  gemini2mqtt:test \
  -c "pip install uv && uv run pytest -v --run-e2e"
```
*(Hinweis: Durch das Mounten von `/var/run/docker.sock` kann `testcontainers` auch aus dem Test-Container heraus den MQTT-Broker starten).*


