import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns  # Falls Fehler: 'pip install seaborn' im Terminal
from strategy import MeanReversionStrategy
from data_manager import DataManager

# --- KONFIGURATION DES OPTIMIERERS ---

# 1. Das Test-Universum (Mix aus Stabil & Wild)
# Wir wollen Parameter finden, die sowohl für Indizes als auch für Tech-Aktien funktionieren.
TICKERS = ["^GDAXI", "^GSPC", "MSFT", "IBM", "SIE.DE", "NVDA", "TSLA"]

# 2. Das Parameter-Raster (128 Kombinationen)

# DROP: Sehr fein abgestuft von "Markt-Korrektur" (2.5%) bis "Crash" (12%)
DROP_OPTIONS = [2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0]

# HOLD: Von Swing-Trading (eine Woche) bis Position-Trading (knapp 2 Monate)
HOLD_OPTIONS = [5, 10, 20, 40]

# TAKE PROFIT: Von schnell Gewinne mitnehmen bis gierig laufen lassen
TP_OPTIONS = [2.0, 4.0, 6.0, 8.0]

# Gebühr (0.1% pro Order)
FEE = 0.001


def run_optimization():
    print("--- Bereite Daten vor ---")
    # Wir laden die Daten einmal zentral (reload=True beim ersten Mal empfohlen, falls NVDA fehlt)
    dm = DataManager()
    dm.get_historical_data(TICKERS, "2000-01-01", "2025-01-01", reload=False)

    bot = MeanReversionStrategy(initial_capital=10000)
    results = []

    total_combinations = len(DROP_OPTIONS) * len(HOLD_OPTIONS) * len(TP_OPTIONS)
    counter = 0

    print(f"\n--- Starte Grid Search ({total_combinations} Kombinationen für {len(TICKERS)} Assets) ---")
    print("Dies kann einen Moment dauern... Ich melde mich bei Highlights.\n")

    # --- DIE DREIFACHE SCHLEIFE ---
    for drop in DROP_OPTIONS:
        for hold in HOLD_OPTIONS:
            for tp in TP_OPTIONS:
                counter += 1

                # Parameter setzen
                params = {
                    "drop": drop,
                    "lookback": 3,  # Fix auf 3 Tage (Standard)
                    "hold": hold,
                    "take_profit": tp,
                    "fee": FEE
                }

                # Strategie ausführen
                trades = bot.run_portfolio(TICKERS, params)

                if not trades:
                    # Nichts passiert -> Ergebnis 0 speichern
                    results.append({
                        "drop": drop, "hold": hold, "tp": tp,
                        "profit": 0, "roi": 0, "trades": 0, "win_rate": 0
                    })
                    continue

                # Ergebnis berechnen
                df = pd.DataFrame(trades)
                total_profit = df['profit_abs'].sum()
                roi = (total_profit / 10000) * 100
                win_rate = len(df[df['profit_abs'] > 0]) / len(df) * 100

                # --- INTELLIGENTE AUSGABE ---
                # Wir zeigen den Fortschritt nur alle 10 Schritte an,
                # ODER wenn wir ein sehr gutes Ergebnis (> 50% ROI) gefunden haben.
                is_highlight = roi > 50.0
                if counter % 10 == 0 or is_highlight:
                    marker = "🔥 SUPER TREFFER!" if is_highlight else ""
                    print(
                        f"[{counter}/{total_combinations}] Drop:{drop}% | Hold:{hold}d | TP:{tp}% -> ROI: {roi:.2f}% {marker}")

                results.append({
                    "drop": drop,
                    "hold": hold,
                    "tp": tp,
                    "profit": total_profit,
                    "roi": roi,
                    "trades": len(df),
                    "win_rate": win_rate
                })

    return pd.DataFrame(results)


def plot_heatmap(df_results):
    """
    Erstellt eine Heatmap: Drop vs. Hold (mit ROI als Farbe)
    """
    # Da wir 3 Variablen haben (Drop, Hold, TP), aggregieren wir TP weg.
    # Wir nehmen den DURCHSCHNITTLICHEN ROI aller TP-Varianten für diese Drop/Hold Zelle.
    pivot_table = df_results.pivot_table(
        index='drop',
        columns='hold',
        values='roi',
        aggfunc='mean'
    )

    plt.figure(figsize=(12, 8))
    # cmap="RdYlGn" macht rot (Verlust) zu grün (Gewinn)
    sns.heatmap(pivot_table, annot=True, fmt=".1f", cmap="RdYlGn", cbar_kws={'label': 'Ø ROI %'})

    plt.title("Grid Search Heatmap: Wo liegt der Sweetspot?")
    plt.ylabel("Drop Schwellwert (%)")
    plt.xlabel("Haltedauer (Tage)")

    # Erklärungstext unter dem Chart
    plt.figtext(0.5, 0.01, "Zahlen zeigen den Durchschnitts-ROI über alle Take-Profit Varianten",
                wrap=True, horizontalalignment='center', fontsize=10)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # Pandas Anzeige-Optionen
    pd.set_option('display.max_rows', 50)
    pd.set_option('display.width', 1000)

    # 1. Optimierung starten
    df_results = run_optimization()

    # 2. Beste Ergebnisse sortieren
    print("\n" + "=" * 60)
    print("TOP 10 PARAMETER-SETS (Sortiert nach Gewinn)")
    print("=" * 60)

    # Sortiere nach ROI absteigend
    top_results = df_results.sort_values(by="roi", ascending=False).head(10)
    print(top_results)

    # 3. Den allerbesten Parametersatz extrahieren
    best = top_results.iloc[0]
    print("\n" + "=" * 60)
    print(f"🏆 SIEGER KONFIGURATION 🏆")
    print(f"Drop Schwellwert: {best['drop']}%")
    print(f"Haltedauer:       {int(best['hold'])} Tage")
    print(f"Take Profit:      {best['tp']}%")
    print("-" * 30)
    print(f"Gesamt-Rendite:   {best['roi']:.2f}%")
    print(f"Anzahl Trades:    {int(best['trades'])}")
    print(f"Trefferquote:     {best['win_rate']:.2f}%")
    print("=" * 60)

    # 4. Visualisierung
    print("Erstelle Heatmap...")
    try:
        plot_heatmap(df_results)
    except Exception as e:
        print(f"Hinweis: Konnte Heatmap nicht erstellen: {e}")