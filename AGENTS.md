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

### Standard Unit-Tests (Mocked API)
Führt alle verlässlichen und schnellen Unit-Tests ohne externe API-Aufrufe aus:
```bash
uv run pytest -v -m "not e2e"
```
*(Alternativ via system/venv pytest: `pytest -v -m "not e2e"`)*

### End-to-End Tests (Real API)
Führt E2E-Tests aus, die eine echte Verbindung zur Gemini API erfordern (benötigt `GEMINI_API_KEY` in `.env`):
```bash
uv run pytest -v -m "e2e"
```
*(Hinweis: Für den MQTT-Testcontainer muss der Docker-Daemon laufen).*

