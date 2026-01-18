import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from data_manager import DataManager


class MeanReversionStrategy:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.data_path = "data_cache"  # Stelle sicher, dass der Ordner existiert

    def load_and_clean_data(self, ticker):
        """
        Lädt die Daten und bereinigt die Daten
        """
        file_path = os.path.join(self.data_path, f"{ticker}.csv")
        if not os.path.exists(file_path):
            print(f"WARNUNG: Datei nicht gefunden: {file_path}")
            return None

        try:
            # Header=[0,1,2] ist wichtig für yfinance CSVs
            df = pd.read_csv(file_path, header=[0, 1, 2], index_col=0, parse_dates=True)

            clean_df = pd.DataFrame(index=df.index)
            # Wir holen uns die erste Spalte unter dem jeweiligen Header
            clean_df['Close'] = df['Close'].iloc[:, 0]
            clean_df['Open'] = df['Open'].iloc[:, 0]
            clean_df['High'] = df['High'].iloc[:, 0]

            # Lücken füllen
            clean_df.ffill(inplace=True)
            return clean_df
        except Exception as e:
            print(f"Fehler beim Laden von {ticker}: {e}")
            return None

    def backtest(self, ticker, drop_threshold_pct, lookback_days, hold_days, take_profit_pct, fee_rate):
        """
        Führt den Backtest durch
        """
        df = self.load_and_clean_data(ticker)
        if df is None or df.empty:
            return []

        df['change'] = df['Close'].pct_change(periods=lookback_days)


        threshold_decimal = -(drop_threshold_pct / 100)

        signal_indices = np.where(df['change'] < threshold_decimal)[0]

        trades = []
        last_exit_index = -1

        for idx in signal_indices:
            """
            Trade wird erst am nächsten Tag ausgeführt, da erst bei Börsenschluss der Tagesschluss bekannt ist.
            """
            entry_idx = idx + 1

            if entry_idx <= last_exit_index:
                continue
            if entry_idx >= len(df):
                continue

            entry_date = df.index[entry_idx]
            raw_entry_price = df['Open'].iloc[entry_idx]

            effective_entry_price = raw_entry_price * (1 + fee_rate)

            target_price = raw_entry_price * (1 + take_profit_pct / 100)

            exit_price = None
            exit_date = None
            exit_reason = ""
            days_held = 0

            found_exit = False

            for i in range(0, hold_days):
                current_idx = entry_idx + i

                if current_idx >= len(df):
                    break

                current_high = df['High'].iloc[current_idx]
                current_open = df['Open'].iloc[current_idx]
                current_close = df['Close'].iloc[current_idx]
                current_date = df.index[current_idx]

                # Take Profit Logik
                can_sell_at_open = (i > 0)

                if current_high >= target_price:
                    if can_sell_at_open and current_open > target_price:
                        raw_exit_price = current_open
                    else:
                        raw_exit_price = target_price

                    exit_reason = "Take Profit"
                    days_held = i
                    found_exit = True

                # Haltedauer wurde erreicht
                elif i == (hold_days - 1):
                    raw_exit_price = current_close
                    exit_reason = "Time Stop"
                    days_held = i
                    found_exit = True

                if found_exit:
                    last_exit_index = current_idx
                    exit_date = current_date

                    effective_exit_price = raw_exit_price * (1 - fee_rate)

                    profit_pct = (effective_exit_price - effective_entry_price) / effective_entry_price
                    profit_abs = self.initial_capital * profit_pct

                    trades.append({
                        "ticker": ticker,
                        "buy_date": entry_date.strftime('%Y-%m-%d'),
                        "sell_date": exit_date.strftime('%Y-%m-%d'),
                        "days_held": days_held,
                        "exit_reason": exit_reason,
                        "entry_price": round(raw_entry_price, 2),  # Chart-Preis anzeigen
                        "exit_price": round(raw_exit_price, 2),  # Chart-Preis anzeigen
                        "profit_pct": round(profit_pct * 100, 2),  # Netto-Profit %
                        "profit_abs": round(profit_abs, 2)  # Netto-Profit €
                    })
                    break

        return trades

    def run_portfolio(self, tickers, params):
        all_trades = []
        fee = params.get('fee', 0.001)

        print(f"\n--- Starte Backtest ---")
        print(f"Strategie: Next-Day-Open Entry nach {params['drop']}% Drop.")
        print(f"Kosten: {fee * 100:.2f}% pro Order (Spread+Gebühr).")

        for ticker in tickers:
            trades = self.backtest(
                ticker,
                drop_threshold_pct=params['drop'],
                lookback_days=params['lookback'],
                hold_days=params['hold'],
                take_profit_pct=params['take_profit'],
                fee_rate=fee
            )
            if trades:
                all_trades.extend(trades)
        return all_trades


def plot_equity_curve(trades_df, initial_capital):
    """
    Erstellt ein Diagramm für den Verlauf des Portfolios
    """
    if trades_df.empty:
        print("Keine Trades zum Plotten.")
        return

    df_sorted = trades_df.sort_values("sell_date")

    df_sorted['cumulative_profit'] = df_sorted['profit_abs'].cumsum()

    df_sorted['equity'] = initial_capital + df_sorted['cumulative_profit']

    start_date = df_sorted['sell_date'].min() - pd.Timedelta(days=1)

    plt.figure(figsize=(12, 6))

    plt.plot(df_sorted['sell_date'], df_sorted['equity'], label="Portfolio Wert", color="blue")

    plt.axhline(y=initial_capital, color='r', linestyle='--', label="Startkapital")

    plt.title("Portfolio Performance (Equity Curve)")
    plt.xlabel("Datum")
    plt.ylabel("Kapital in €")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_trades_on_chart(ticker, strategy_instance, trades_df):
    """
    Zeigt den Aktienkurs und markiert die Käufe und Verkäufe
    """
    print(f"Lade Chart-Daten für {ticker}...")
    df_prices = strategy_instance.load_and_clean_data(ticker)

    if df_prices is None or df_prices.empty:
        print(f"Keine Daten für {ticker} gefunden.")
        return

    ticker_trades = trades_df[trades_df['ticker'] == ticker]

    if ticker_trades.empty:
        print(f"Keine Trades für {ticker} gefunden.")
        return

    plt.figure(figsize=(14, 7))


    start_plot = pd.to_datetime(ticker_trades['buy_date'].min()) - pd.Timedelta(days=30)
    end_plot = pd.to_datetime(ticker_trades['sell_date'].max()) + pd.Timedelta(days=30)

    mask = (df_prices.index >= start_plot) & (df_prices.index <= end_plot)
    subset = df_prices.loc[mask]

    plt.plot(subset.index, subset['Close'], label=f"{ticker} Kurs", color="gray", alpha=0.5)

    plt.scatter(pd.to_datetime(ticker_trades['buy_date']),
                ticker_trades['entry_price'],
                color='green', marker='^', s=100, label='Kauf', zorder=5)


    plt.scatter(pd.to_datetime(ticker_trades['sell_date']),
                ticker_trades['exit_price'],
                color='red', marker='v', s=100, label='Verkauf', zorder=5)

    plt.title(f"Trade Analyse für {ticker}")
    plt.xlabel("Datum")
    plt.ylabel("Preis")
    plt.legend()
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    from data_manager import DataManager


    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)


    tickers = ["MSFT", "IBM", "SIE.DE", "^GDAXI"]
    dm = DataManager()
    dm.get_historical_data(tickers, "2000-01-01", "2025-01-01", reload=False)

    start_cap = 10000
    bot = MeanReversionStrategy(initial_capital=start_cap)

    params = {
        "drop": 10.0,
        "lookback": 15,
        "hold": 780,
        "take_profit": 5.0,
        "fee": 0.001
    }

    results = bot.run_portfolio(tickers, params)

    if results:
        df = pd.DataFrame(results)
        df['buy_date'] = pd.to_datetime(df['buy_date'])
        df['sell_date'] = pd.to_datetime(df['sell_date'])

        # --- 1. DIAGRAMM: PORTFOLIO VERLAUF ---
        print("Erstelle Portfolio-Chart...")
        plot_equity_curve(df, start_cap)

        # --- 2. DIAGRAMM: EINZELAKTIE ANALYSE ---
        # Wir suchen uns automatisch den Ticker mit den meisten Trades raus zum Zeigen
        top_ticker = df['ticker'].value_counts().idxmax()
        print(f"Erstelle Trade-Chart für die aktivste Aktie: {top_ticker}...")

        plot_trades_on_chart(top_ticker, bot, df)

    else:
        print("Keine Trades, keine Diagramme.")