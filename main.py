from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import pandas as pd
import numpy as np

# Deine existierenden Klassen
from strategy import MeanReversionStrategy
from data_manager import DataManager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- MODELS ---
class OptimizationRequest(BaseModel):
    tickers: List[str]
    drop_options: List[float]
    hold_options: List[int]
    take_profit_options: List[float]
    initial_capital: float = 10000.0


class TradeResult(BaseModel):
    ticker: str
    buy_date: str
    sell_date: str
    entry_price: float
    exit_price: float
    profit_abs: float
    exit_reason: str


class BestStrategyResponse(BaseModel):
    best_drop: float
    best_hold: int
    best_tp: float
    total_profit: float
    roi_pct: float
    win_rate: float
    total_trades: int
    equity_curve_data: List[dict]  # Jetzt mit "buy_and_hold" Key
    trades: List[TradeResult]


# --- NEU: INTELLIGENTE KURVEN-BERECHNUNG ---
def calculate_comparison_curves(trades, tickers, initial_capital, data_dict):
    """
    Berechnet tagesgenau die Strategie-Equity vs. Buy & Hold Benchmark.
    """
    # 1. Wir brauchen einen gemeinsamen Zeitstrahl (Index) über alle Jahre
    all_dates = pd.DatetimeIndex([])
    for t in tickers:
        if t in data_dict and not data_dict[t].empty:
            all_dates = all_dates.union(data_dict[t].index)

    if len(all_dates) == 0:
        return []

    all_dates = all_dates.sort_values().unique()

    # DataFrame erstellen, der jeden Tag abdeckt
    df_curve = pd.DataFrame(index=all_dates)

    # --- A. STRATEGIE KURVE (Realisierte Gewinne) ---
    # Wir starten mit Startkapital
    df_curve['strategy_equity'] = 0.0  # Wird später gefüllt
    daily_profits = pd.Series(0.0, index=all_dates)

    if trades:
        trades_df = pd.DataFrame(trades)
        trades_df['sell_date'] = pd.to_datetime(trades_df['sell_date'])
        # Wir summieren die Gewinne an den Verkaufstagen
        grouped_profits = trades_df.groupby('sell_date')['profit_abs'].sum()
        # Wir ordnen sie dem Zeitstrahl zu
        daily_profits = daily_profits.add(grouped_profits, fill_value=0)

    # Kumulierte Summe + Startkapital = Kontostand
    df_curve['strategy_equity'] = initial_capital + daily_profits.cumsum()
    # Lücken (Wochenenden/Feiertage) auffüllen
    df_curve['strategy_equity'] = df_curve['strategy_equity'].ffill()

    # --- B. BUY & HOLD BENCHMARK ---
    # Wir teilen das Kapital am Anfang gleichmäßig auf alle Ticker auf
    allocation_per_ticker = initial_capital / len(tickers)
    df_curve['benchmark_equity'] = 0.0

    for t in tickers:
        if t in data_dict and not data_dict[t].empty:
            # Wir holen die Close-Preise
            df_asset = data_dict[t]

            # Helper: Falls MultiIndex Header (yfinance)
            if isinstance(df_asset.columns, pd.MultiIndex):
                prices = df_asset['Close'].iloc[:, 0]
            else:
                prices = df_asset['Close']

            # An unseren Zeitstrahl anpassen
            prices = prices.reindex(all_dates).ffill().bfill()

            # Performance berechnen: (Aktueller Preis / Start Preis) * Investiertes Geld
            start_price = prices.iloc[0]
            if start_price > 0:
                val_series = (prices / start_price) * allocation_per_ticker
                df_curve['benchmark_equity'] += val_series
            else:
                df_curve['benchmark_equity'] += allocation_per_ticker

    # --- JSON FORMATIERUNG ---
    chart_data = []
    # Um Datenmenge zu sparen, nehmen wir jeden 5. Tag (reicht für Chart) oder alles
    # Wir nehmen alles, aber filtern NaNs
    df_curve = df_curve.fillna(method='ffill').fillna(initial_capital)

    for date, row in df_curve.iterrows():
        chart_data.append({
            "date": date.strftime('%Y-%m-%d'),
            "equity": round(row['strategy_equity'], 2),
            "buy_and_hold": round(row['benchmark_equity'], 2)
        })

    return chart_data


# --- ENDPUNKTE ---

@app.post("/optimize", response_model=BestStrategyResponse)
def get_best_strategy(request: OptimizationRequest):
    print(f"Starte Optimierung für {len(request.tickers)} Ticker...")

    dm = DataManager()
    # Wir speichern die Daten in einer Variable für die Benchmark-Berechnung
    data_dict = dm.get_historical_data(request.tickers, "2000-01-01", "2025-01-01", reload=False)

    bot = MeanReversionStrategy(initial_capital=request.initial_capital)

    best_roi = -999999.0
    best_result = None
    best_trades = []
    best_params = {}

    combinations = len(request.drop_options) * len(request.hold_options) * len(request.take_profit_options)
    print(f"Prüfe {combinations} Kombinationen...")

    for drop in request.drop_options:
        for hold in request.hold_options:
            for tp in request.take_profit_options:
                current_params = {
                    "drop": drop, "lookback": 3, "hold": hold, "take_profit": tp, "fee": 0.001
                }
                trades = bot.run_portfolio(request.tickers, current_params)

                if trades:
                    df = pd.DataFrame(trades)
                    profit = df['profit_abs'].sum()
                    roi = (profit / request.initial_capital) * 100
                    win_rate = len(df[df['profit_abs'] > 0]) / len(df) * 100
                else:
                    profit = 0;
                    roi = 0;
                    win_rate = 0

                if roi > best_roi:
                    best_roi = roi
                    best_trades = trades
                    best_params = {"drop": drop, "hold": hold, "tp": tp}
                    best_result = {"profit": profit, "win_rate": win_rate, "count": len(trades)}

    if not best_params:
        raise HTTPException(status_code=404, detail="Keine profitablen Trades gefunden.")

    # Hier rufen wir die NEUE Funktion auf
    equity_data = calculate_comparison_curves(
        best_trades, request.tickers, request.initial_capital, data_dict
    )

    return {
        "best_drop": best_params['drop'],
        "best_hold": best_params['hold'],
        "best_tp": best_params['tp'],
        "total_profit": round(best_result['profit'], 2),
        "roi_pct": round(best_roi, 2),
        "win_rate": round(best_result['win_rate'], 2),
        "total_trades": best_result['count'],
        "equity_curve_data": equity_data,
        "trades": best_trades
    }


@app.get("/chart/{ticker}")
def get_chart_data(ticker: str):
    dm = DataManager()
    data_dict = dm.get_historical_data([ticker], "2000-01-01", "2025-01-01", reload=False)

    if ticker not in data_dict or data_dict[ticker].empty:
        raise HTTPException(status_code=404, detail="Ticker nicht gefunden.")

    df = data_dict[ticker].copy()

    # Header Bereinigung
    if isinstance(df.columns, pd.MultiIndex):
        try:
            clean_df = pd.DataFrame(index=df.index)
            clean_df['Open'] = df['Open'].iloc[:, 0]
            clean_df['High'] = df['High'].iloc[:, 0]
            clean_df['Low'] = df['Low'].iloc[:, 0]
            clean_df['Close'] = df['Close'].iloc[:, 0]
            df = clean_df
        except:
            pass  # Fallback

    df = df.ffill().bfill().fillna(0.0)
    chart_data = []
    for index, row in df.iterrows():
        chart_data.append({
            "date": index.strftime('%Y-%m-%d'),
            "open": float(round(row['Open'], 2)),
            "high": float(round(row['High'], 2)),
            "low": float(round(row['Low'], 2)),
            "close": float(round(row['Close'], 2))
        })
    return chart_data