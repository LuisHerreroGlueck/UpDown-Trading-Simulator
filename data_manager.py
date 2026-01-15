# data_manager.py
import yfinance as yf
import pandas as pd
import os
from datetime import datetime


class DataManager:
    def __init__(self, storage_path="data_cache"):
        """
        Initialisiert den Manager.
        storage_path: Ordner, in dem die CSV-Dateien gespeichert werden.
        """
        self.storage_path = storage_path
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)

    def get_historical_data(self, tickers, start_date, end_date, reload=False):
        """
        Lädt Daten für eine Liste von Tickern.
        Prüft zuerst, ob lokale Daten vorhanden sind.

        reload: Wenn True, wird der Download erzwungen (Cache ignoriert).
        """
        all_data = {}

        print(f"--- Starte Datenbeschaffung für {len(tickers)} Aktien ---")

        for ticker in tickers:
            file_path = os.path.join(self.storage_path, f"{ticker}.csv")

            # Prüfen: Haben wir die Datei schon und wollen wir nicht neu laden?
            if os.path.exists(file_path) and not reload:
                print(f"[{ticker}] Lade aus Cache...")
                df = df = pd.read_csv(file_path, header=[0, 1, 2], index_col=0, parse_dates=True)

                # Optional: Prüfen ob die lokalen Daten den angeforderten Zeitraum abdecken
                # Das lassen wir für den ersten Prototypen weg, um es einfach zu halten.

            else:
                print(f"[{ticker}] Lade von Yahoo Finance herunter...")
                # auto_adjust=True ist WICHTIG! Es bereinigt Aktiensplits und Dividenden.
                df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)

                if not df.empty:
                    # Wir speichern es lokal ab
                    df.to_csv(file_path)
                else:
                    print(f"WARNUNG: Keine Daten für {ticker} gefunden.")

            all_data[ticker] = df

        print("--- Datenbeschaffung abgeschlossen ---\n")
        return all_data


# --- Kleiner Testbereich (wird nur ausgeführt, wenn man die Datei direkt startet) ---
if __name__ == "__main__":
    # Beispiel: Blue Chips (Tech USA + DAX Deutschland)
    # Hinweis: Deutsche Aktien bei Yahoo haben oft das Suffix .DE
    my_tickers = ["AAPL", "MSFT", "IBM", "SIE.DE", "BMW.DE", "KO"]

    manager = DataManager()
    data = manager.get_historical_data(
        tickers=my_tickers,
        start_date="2020-01-01",
        end_date=datetime.today().strftime('%Y-%m-%d')
    )

    # Kurzer Check, wie die Daten aussehen
    print("Beispiel Daten für Apple:")
    print(data["AAPL"].head())