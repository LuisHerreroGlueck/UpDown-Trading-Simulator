# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

# Quantitative Trading Strategy Optimizer

![Status](https://img.shields.io/badge/Status-Prototyp-blue) ![Python](https://img.shields.io/badge/Backend-Python%20FastAPI-green) ![React](https://img.shields.io/badge/Frontend-React%20Vite-blue)

Eine Full-Stack Web-Applikation zur Simulation und Optimierung quantitativer Handelsstrategien auf Basis historischer Finanzdaten. Das Tool nutzt einen **Mean-Reversion-Ansatz** und ermittelt durch algorithmisches Backtesting (Grid Search) die profitabelsten Ein- und Ausstiegsparameter für Aktien und Indizes.

## Features

* **Multi-Asset Backtesting:** Analyse von Aktien (z.B. MSFT, TSLA) und Indizes (z.B. ^GDAXI) über 20+ Jahre.
* **Grid Search Algorithmus:** Automatische Ermittlung der optimalen Parameter-Kombination (Drop %, Haltedauer, Take Profit).
* **Interaktive Charts:** Visualisierung der Aktienkurse mit exakten Kauf- (🟢) und Verkaufsmarkern (🔴).
* **Benchmark-Vergleich:** Direkte Gegenüberstellung der Strategie-Performance vs. "Buy & Hold".
* **Professionelles Dashboard:** Responsive UI mit React & Recharts, inkl. logarithmischer Skalierung und KPI-Analyse.

## Tech Stack

**Backend:**
* Python 3.12+
* **FastAPI:** High-Performance API Framework.
* **Pandas & NumPy:** Für Vektorisierte Finanzberechnungen.
* **yfinance:** Zum Abruf historischer Marktdaten.

**Frontend:**
* **React:** UI-Library.
* **Vite:** Build Tool.
* **Recharts:** Charting Bibliothek.
* **Axios:** API Kommunikation.

---

## Installation & Start (Windows)

Das Projekt besteht aus zwei Teilen (Backend & Frontend), die parallel laufen müssen.

### 1. Backend starten (Python)

Öffne ein Terminal im Hauptverzeichnis des Projekts:

```powershell
# 1. Virtuelle Umgebung erstellen (falls noch nicht vorhanden)
python -m venv .venv

# 2. Umgebung aktivieren
.\.venv\Scripts\Activate

# 3. Abhängigkeiten installieren
pip install -r requirements.txt

# 4. Server starten
python -m uvicorn main:app --reload
```

Der Backend-Server läuft nun unter: **http://127.0.0.1:8000**

---

### 2. Frontend starten (React)

Öffne ein **zweites Terminal** im Hauptverzeichnis des Projekts:

```powershell
# 1. In das Frontend-Verzeichnis wechseln
cd frontend

# 2. Abhängigkeiten installieren (nur beim ersten Mal nötig)
npm install

# 3. Entwicklungsserver starten
npm run dev
```

Das Frontend läuft nun unter: **http://localhost:5173**

---

## Nutzung

1. Öffne **http://localhost:5173** im Browser
2. Gib die gewünschten Ticker-Symbole ein (z.B. `MSFT, IBM, ^GDAXI`)
3. Konfiguriere die Strategie-Parameter (Drop %, Haltedauer, Take Profit)
4. Klicke auf **"Analyse Starten"**
5. Die Ergebnisse werden als KPIs, Charts und Trade-Historie angezeigt
