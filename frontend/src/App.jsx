import { useState } from 'react'
import axios from 'axios'
import {
  ComposedChart, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Scatter
} from 'recharts';
import './App.css'

// --- VERBESSERTE MARKER (Position korrigiert) ---
const BuyMarker = (props) => {
  const { cx, cy } = props;
  if (!Number.isFinite(cx) || !Number.isFinite(cy)) return null;

  // Grüner Pfeil nach OBEN (▲), leicht UNTERHALB des Punktes platziert
  return (
    <svg x={cx - 8} y={cy + 10} width={16} height={16} fill="#27ae60" viewBox="0 0 1024 1024" style={{overflow: 'visible'}}>
      {/* Dreieckspitze zeigt nach oben */}
      <path d="M512 32l-448 896h896z" />
    </svg>
  );
};

const SellMarker = (props) => {
  const { cx, cy } = props;
  if (!Number.isFinite(cx) || !Number.isFinite(cy)) return null;

  // Roter Pfeil nach UNTEN (▼), leicht OBERHALB des Punktes platziert
  return (
    <svg x={cx - 8} y={cy - 26} width={16} height={16} fill="#c0392b" viewBox="0 0 1024 1024" style={{overflow: 'visible'}}>
      {/* Dreieckspitze zeigt nach unten */}
      <path d="M512 992l448-896h-896z" />
    </svg>
  );
};

function App() {
  const [tickers, setTickers] = useState("MSFT, IBM, ^GDAXI")
  const [dropMin, setDropMin] = useState(5.0)
  const [dropMax, setDropMax] = useState(8.0)
  const [holdMin, setHoldMin] = useState(250)
  const [holdMax, setHoldMax] = useState(255)
  const [tpMin, setTpMin] = useState(5.0)
  const [tpMax, setTpMax] = useState(8.0)

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const [selectedTicker, setSelectedTicker] = useState(null)
  const [chartData, setChartData] = useState([])
  const [loadingChart, setLoadingChart] = useState(false)

  const generateRange = (min, max, step) => {
    const arr = []
    for (let i = parseFloat(min); i <= parseFloat(max); i += step) {
      arr.push(parseFloat(i.toFixed(1)))
    }
    return arr
  }

  const handleOptimize = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    setChartData([])
    setSelectedTicker(null)

    try {
      const payload = {
        tickers: tickers.split(",").map(t => t.trim()),
        drop_options: generateRange(dropMin, dropMax, 1.0),
        hold_options: generateRange(holdMin, holdMax, 5),
        take_profit_options: generateRange(tpMin, tpMax, 1.0),
        initial_capital: 10000
      }

      console.log("Sende Anfrage...", payload)
      const response = await axios.post('http://127.0.0.1:8000/optimize', payload)
      setResult(response.data)

      if (response.data.trades.length > 0) {
        const counts = {};
        response.data.trades.forEach(t => { counts[t.ticker] = (counts[t.ticker] || 0) + 1; });
        const topTicker = Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b);

        loadTickerChart(topTicker, response.data.trades)
      }

    } catch (err) {
      console.error("Fehler im Frontend:", err)
      setError("Verbindung fehlgeschlagen. Backend prüfen.")
    } finally {
      setLoading(false)
    }
  }

  const loadTickerChart = async (ticker, allTrades) => {
    setLoadingChart(true)
    setSelectedTicker(ticker)
    setChartData([])

    try {
      const res = await axios.get(`http://127.0.0.1:8000/chart/${ticker}`)
      const prices = res.data
      const myTrades = allTrades.filter(t => t.ticker === ticker)

      const mergedData = prices.map(day => {
        const buyTrade = myTrades.find(t => t.buy_date === day.date)
        const sellTrade = myTrades.find(t => t.sell_date === day.date)

        return {
          ...day,
          buyPoint: buyTrade ? buyTrade.entry_price : undefined,
          sellPoint: sellTrade ? sellTrade.exit_price : undefined,
          action: buyTrade ? 'KAUF' : (sellTrade ? 'VERKAUF' : null)
        }
      })
      setChartData(mergedData)
    } catch (err) {
      console.error(err)
      setError(`Konnte Chart für ${ticker} nicht laden.`)
    } finally {
      setLoadingChart(false)
    }
  }

  return (
    <div className="dashboard-container">
      <div className="header">
        <h1>Quantitative Strategy Optimizer</h1>
        <div className="subtitle">Mean Reversion Backtesting Engine v1.0</div>
      </div>

      <div className="card">
        <h3 className="card-title">Parameter Konfiguration</h3>
        <div className="form-group" style={{marginBottom: '25px'}}>
          <label>Ticker Symbole (Kommagetrennt)</label>
          <input type="text" value={tickers} onChange={e => setTickers(e.target.value)} placeholder="z.B. AAPL, MSFT" />
        </div>
        <div className="input-grid">
          <div className="form-group">
            <label>Drop Threshold (%)</label>
            <div className="range-inputs">
              <input type="number" value={dropMin} onChange={e => setDropMin(e.target.value)} />
              <span className="range-separator">-</span>
              <input type="number" value={dropMax} onChange={e => setDropMax(e.target.value)} />
            </div>
          </div>
          <div className="form-group">
            <label>Holding Period (Tage)</label>
            <div className="range-inputs">
              <input type="number" value={holdMin} onChange={e => setHoldMin(e.target.value)} />
              <span className="range-separator">-</span>
              <input type="number" value={holdMax} onChange={e => setHoldMax(e.target.value)} />
            </div>
          </div>
          <div className="form-group">
            <label>Take Profit Target (%)</label>
            <div className="range-inputs">
              <input type="number" value={tpMin} onChange={e => setTpMin(e.target.value)} />
              <span className="range-separator">-</span>
              <input type="number" value={tpMax} onChange={e => setTpMax(e.target.value)} />
            </div>
          </div>
        </div>
        <button className="btn-primary" onClick={handleOptimize} disabled={loading}>
          {loading ? "Berechne Strategien..." : "Analyse Starten"}
        </button>
      </div>

      {error && <div style={{ color: '#c0392b', marginBottom: '20px', padding: '15px', background: '#fadbd8', borderRadius: '4px', border: '1px solid #f5b7b1' }}>{error}</div>}

      {result && (
        <div>
          {/* KPI Dashboard */}
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-label">Return on Investment</div>
              <div className={`kpi-value ${result.roi_pct >= 0 ? 'text-success' : 'text-danger'}`}>
                {result.roi_pct > 0 ? '+' : ''}{result.roi_pct}%
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Total Net Profit</div>
              <div className={`kpi-value ${result.total_profit >= 0 ? 'text-success' : 'text-danger'}`}>
                {result.total_profit.toLocaleString()} €
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Win Rate</div>
              <div className="kpi-value" style={{color: '#d35400'}}>{result.win_rate}%</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Total Trades</div>
              <div className="kpi-value">{result.total_trades}</div>
            </div>
          </div>

          <div className="card">
            <h3 className="card-title">Optimale Parameter</h3>
            <div style={{display: 'flex', gap: '40px', color: '#555', fontSize: '16px'}}>
              <div>Drop: <strong>{result.best_drop}%</strong></div>
              <div>Hold: <strong>{result.best_hold} Tage</strong></div>
              <div>Take Profit: <strong>{result.best_tp}%</strong></div>
            </div>
          </div>

          {/* SINGLE ASSET CHART - JETZT LOGARITHMISCH */}
          <div className="card">
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
              <h3 className="card-title" style={{margin:0}}>Trade Analyse: {selectedTicker || "-"} (Log. Skala)</h3>
              <div style={{display: 'flex', gap: '5px', flexWrap: 'wrap'}}>
                {result.trades && [...new Set(result.trades.map(t => t.ticker))].slice(0, 5).map(t => (
                  <button
                    key={t}
                    onClick={() => loadTickerChart(t, result.trades)}
                    style={{
                      padding: '5px 10px',
                      background: selectedTicker === t ? '#2c3e50' : '#ecf0f1',
                      color: selectedTicker === t ? 'white' : '#333',
                      border: '1px solid #2c3e50',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '12px'
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ height: '450px', width: '100%' }}>
              {loadingChart ? (
                <div style={{textAlign:'center', paddingTop: '100px', color: '#7f8c8d'}}>Lade Kursdaten...</div>
              ) : (
                chartData && chartData.length > 0 ? (
                  <ResponsiveContainer>
                    <ComposedChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e0e0e0" />
                      <XAxis dataKey="date" minTickGap={50} tick={{fontSize: 12, fill: '#7f8c8d'}} tickLine={false} axisLine={{stroke: '#e0e0e0'}} />

                      {/* LOG SCALE FÜR DEN PREIS-CHART */}
                      <YAxis
                        domain={['auto', 'auto']}
                        scale="log"
                        allowDataOverflow
                        tick={{fontSize: 12, fill: '#7f8c8d'}}
                        tickLine={false}
                        axisLine={false}
                      />

                      <Tooltip />
                      <Legend />
                      <Line type="natural" dataKey="close" stroke="#bdc3c7" strokeWidth={2} dot={false} name="Aktienkurs" />
                      {/* VERBESSERTE MARKER */}
                      <Scatter
                        name="Kauf Signal"
                        dataKey="buyPoint"
                        shape={<BuyMarker />}
                        fill="#27ae60"          // <-- WICHTIG: Macht das Symbol in der Legende GRÜN
                        legendType="triangle"   // <-- Macht ein DREIECK in der Legende
                        isAnimationActive={false}
                      />
                      
                      <Scatter
                        name="Verkauf"
                        dataKey="sellPoint"
                        shape={<SellMarker />}
                        fill="#c0392b"          // <-- WICHTIG: Macht das Symbol in der Legende ROT
                        legendType="triangle"   // <-- Macht ein DREIECK in der Legende
                        isAnimationActive={false}
                      />

                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{textAlign:'center', paddingTop: '100px', color: '#bdc3c7'}}>Warte auf Analyse...</div>
                )
              )}
            </div>
          </div>

          {/* EQUITY CHART - AUCH LOGARITHMISCH */}
          <div className="card">
            <h3 className="card-title">Portfolio Performance (Log. Skala)</h3>
            <div style={{ height: '350px', width: '100%' }}>
              <ResponsiveContainer>
                <LineChart data={result.equity_curve_data}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e0e0e0" />
                  <XAxis dataKey="date" minTickGap={50} tick={{fontSize: 12, fill: '#7f8c8d'}} tickLine={false} axisLine={{stroke: '#e0e0e0'}} />

                  {/* LOG SCALE FÜR EQUITY */}
                  <YAxis
                    domain={['auto', 'auto']}
                    scale="log"
                    allowDataOverflow
                    tick={{fontSize: 12, fill: '#7f8c8d'}}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => `${value}€`}
                  />

                  <Tooltip contentStyle={{borderRadius: '4px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)'}} />
                  <Legend />
                  <Line type="natural" dataKey="equity" stroke="#2c3e50" strokeWidth={3} dot={false} name="Optimierte Strategie" />
                  <Line type="natural" dataKey="buy_and_hold" stroke="#e67e22" strokeWidth={2} dot={false} strokeDasharray="5 5" name="Buy & Hold (Vergleich)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <h3 className="card-title">Trade Historie</h3>
            <div className="trade-table-container">
              <table className="trade-table">
                <thead>
                  <tr>
                    <th>Asset</th>
                    <th>Einstieg</th>
                    <th>Ausstieg</th>
                    <th>Preis In</th>
                    <th>Preis Out</th>
                    <th>Grund</th>
                    <th style={{textAlign: 'right'}}>P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((trade, idx) => (
                    <tr key={idx}>
                      <td><strong>{trade.ticker}</strong></td>
                      <td>{trade.buy_date}</td>
                      <td>{trade.sell_date}</td>
                      <td>{trade.entry_price.toFixed(2)}</td>
                      <td>{trade.exit_price.toFixed(2)}</td>
                      <td style={{fontSize: '12px', color: '#7f8c8d'}}>{trade.exit_reason}</td>
                      <td style={{textAlign: 'right'}} className={trade.profit_abs >= 0 ? "text-success" : "text-danger"}>
                         {trade.profit_abs > 0 ? '+' : ''}{trade.profit_abs.toFixed(2)} €
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App