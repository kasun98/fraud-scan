import { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps"
import { API } from '../App'

const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

const countryCoords = {
  US: [-95.7129, 37.0902], GB: [-3.4359, 55.3781], CA: [-106.3468, 56.1304],
  AU: [133.7751, -25.2744], DE: [10.4515, 51.1657], FR: [2.2137, 46.2276],
  JP: [138.2529, 36.2048], IN: [78.9629, 20.5937], BR: [-51.9253, -14.2350],
  RU: [105.3188, 61.5240], CN: [104.1954, 35.8617], MX: [-102.5528, 23.6345],
  NL: [5.2913, 52.1326], SG: [103.8198, 1.3521], NG: [8.6753, 9.0820],
  ZA: [22.9375, -30.5595], AE: [53.8478, 23.4241], CH: [8.2275, 46.8182],
  SE: [18.6435, 60.1282], KR: [127.7669, 35.9078]
};

export default function Charts() {
  const [data, setData] = useState([])
  const [mapData, setMapData] = useState([])
  const [tooltipData, setTooltipData] = useState(null)
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 })

  useEffect(() => {
    fetch(`${API}/chart_data`)
      .then(res => res.json())
      .then(setData)
      .catch(console.error)
      
    fetch(`${API}/map_data`)
      .then(res => res.json())
      .then(setMapData)
      .catch(console.error)
  }, [])

  return (
    <div>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
        FraudScan Charts & Statistics
      </h2>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem', marginBottom: '2rem' }}>
        The FraudScan Charts and Statistics page displays key metrics and trends for the entire ecosystem.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', paddingBottom: '2rem' }}>
        
        {/* Chart 7: Global Fraud Distribution (Map) */}
        <div className="card" style={{ overflow: 'hidden', gridColumn: '1 / -1' }}>
          <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
              Global Fraud Distribution
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-light)', margin: '0.25rem 0 0 0' }}>
              Geographic map of fraudulent transaction values for the current day
            </p>
          </div>
          <div style={{ padding: '1.5rem', height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-main)' }}>
            <div style={{ width: '100%', height: '100%' }}>
              <ComposableMap width={980} height={400} projectionConfig={{ scale: 160, center: [0, 20] }} style={{ width: "100%", height: "100%" }}>
                <Geographies geography={geoUrl}>
                  {({ geographies }) => {
                    const maxAmount = Math.max(0, ...mapData.map(d => d.fraud_amount));
                    const countryNameMapping = {
                      US: "United States of America", GB: "United Kingdom", CA: "Canada",
                      AU: "Australia", DE: "Germany", FR: "France", JP: "Japan", IN: "India",
                      BR: "Brazil", RU: "Russia", CN: "China", MX: "Mexico", NL: "Netherlands",
                      SG: "Singapore", NG: "Nigeria", ZA: "South Africa", AE: "United Arab Emirates",
                      CH: "Switzerland", SE: "Sweden", KR: "South Korea"
                    };

                    return geographies.map((geo) => {
                      const geoName = geo.properties.name;
                      const mappedCode = Object.keys(countryNameMapping).find(k => countryNameMapping[k] === geoName);
                      const dataItem = mappedCode ? mapData.find(d => d.country === mappedCode) : null;
                      
                      let fillColor = "var(--map-empty)";
                      if (dataItem && maxAmount > 0) {
                        const intensity = 0.1 + (dataItem.fraud_amount / maxAmount) * 0.9;
                        fillColor = `rgba(232, 38, 70, ${intensity})`;
                      }

                      return (
                        <Geography
                          key={geo.rsmKey}
                          geography={geo}
                          fill={fillColor}
                          stroke="var(--border-color)"
                          strokeWidth={0.5}
                          style={{
                            default: { outline: "none" },
                            hover: { fill: fillColor !== "var(--map-empty)" ? fillColor : "var(--bg-active)", outline: "none" },
                            pressed: { outline: "none" },
                          }}
                        />
                      );
                    });
                  }}
                </Geographies>
                {mapData.map((d) => {
                  const coords = countryCoords[d.country];
                  if (!coords) return null;
                  return (
                    <Marker key={d.country} coordinates={coords}>
                      <g
                        fill="#e82646"
                        stroke="var(--bg-card)"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        transform="translate(-12, -24)"
                        style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
                        onMouseEnter={(e) => {
                          setTooltipData({ country: d.country, amount: d.fraud_amount, count: d.fraud_count });
                          setTooltipPos({ x: e.clientX, y: e.clientY });
                        }}
                        onMouseMove={(e) => {
                          setTooltipPos({ x: e.clientX, y: e.clientY });
                        }}
                        onMouseLeave={() => setTooltipData(null)}
                      >
                        <path d="M12 21.7C17.3 17 20 13 20 10a8 8 0 1 0-16 0c0 3 2.7 7 8 11.7z" />
                        <circle cx="12" cy="10" r="3" fill="var(--bg-card)" />
                      </g>
                    </Marker>
                  );
                })}
              </ComposableMap>
            </div>
          </div>
        </div>

        {/* Chart 1: Daily Transactions */}
        <div className="card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
              Daily Transactions
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-light)', margin: '0.25rem 0 0 0' }}>
              Historical transactions over the last 30 days
            </p>
          </div>
          <div style={{ padding: '1.5rem', height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="colorTx" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0784c3" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#0784c3" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} tickFormatter={(val) => (val / 1000).toFixed(0) + 'k'} dx={-10} />
                <Tooltip contentStyle={{ background: 'var(--bg-card)', borderRadius: '0.5rem', border: '1px solid var(--border-color)', boxShadow: '0 0.5rem 1.2rem rgba(0,0,0,0.1)', color: 'var(--text-main)' }} />
                <Area type="monotone" dataKey="transactions" stroke="#0784c3" strokeWidth={2} fillOpacity={1} fill="url(#colorTx)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Average Fraud Score */}
        <div className="card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
              Average Fraud Score
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-light)', margin: '0.25rem 0 0 0' }}>
              Average score assigned by the ML model
            </p>
          </div>
          <div style={{ padding: '1.5rem', height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e82646" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#e82646" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} tickFormatter={(val) => Number(val).toFixed(2)} dx={-10} />
                <Tooltip formatter={(value) => [Number(value).toFixed(2), "Average Score"]} contentStyle={{ background: 'var(--bg-card)', borderRadius: '0.5rem', border: '1px solid var(--border-color)', boxShadow: '0 0.5rem 1.2rem rgba(0,0,0,0.1)', color: 'var(--text-main)' }} />
                <Area type="monotone" dataKey="score" stroke="#e82646" strokeWidth={2} fillOpacity={1} fill="url(#colorScore)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 3: Total Transaction Volume */}
        <div className="card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
              Total Transaction Volume
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-light)', margin: '0.25rem 0 0 0' }}>
              Total dollar amount processed
            </p>
          </div>
          <div style={{ padding: '1.5rem', height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="colorTotalAmt" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#23325b" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#23325b" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} tickFormatter={(val) => '$' + (val / 1000).toFixed(0) + 'k'} dx={-10} />
                <Tooltip formatter={(value) => ['$' + Number(value).toLocaleString(), "Total Volume"]} contentStyle={{ background: 'var(--bg-card)', borderRadius: '0.5rem', border: '1px solid var(--border-color)', boxShadow: '0 0.5rem 1.2rem rgba(0,0,0,0.1)', color: 'var(--text-main)' }} />
                <Area type="monotone" dataKey="total_amount" stroke="#23325b" strokeWidth={2} fillOpacity={1} fill="url(#colorTotalAmt)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 4: Fraudulent Value Detected */}
        <div className="card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
              Fraudulent Value Detected
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-light)', margin: '0.25rem 0 0 0' }}>
              Dollar amount of blocked and confirmed fraud
            </p>
          </div>
          <div style={{ padding: '1.5rem', height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="colorFraudAmt" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f5c200" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#f5c200" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} tickFormatter={(val) => '$' + (val / 1000).toFixed(0) + 'k'} dx={-10} />
                <Tooltip formatter={(value) => ['$' + Number(value).toLocaleString(), "Fraud Volume"]} contentStyle={{ background: 'var(--bg-card)', borderRadius: '0.5rem', border: '1px solid var(--border-color)', boxShadow: '0 0.5rem 1.2rem rgba(0,0,0,0.1)', color: 'var(--text-main)' }} />
                <Area type="monotone" dataKey="fraud_amount" stroke="#f5c200" strokeWidth={2} fillOpacity={1} fill="url(#colorFraudAmt)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 5: Approved Transactions */}
        <div className="card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
              Approved Transactions
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-light)', margin: '0.25rem 0 0 0' }}>
              Count of safe and approved transactions
            </p>
          </div>
          <div style={{ padding: '1.5rem', height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="colorApprove" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00a186" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#00a186" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} tickFormatter={(val) => (val / 1000).toFixed(1) + 'k'} dx={-10} />
                <Tooltip formatter={(value) => [value, "Approved"]} contentStyle={{ background: 'var(--bg-card)', borderRadius: '0.5rem', border: '1px solid var(--border-color)', boxShadow: '0 0.5rem 1.2rem rgba(0,0,0,0.1)', color: 'var(--text-main)' }} />
                <Area type="monotone" dataKey="approved_count" stroke="#00a186" strokeWidth={2} fillOpacity={1} fill="url(#colorApprove)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 6: Blocked Transactions */}
        <div className="card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
              Blocked Transactions
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-light)', margin: '0.25rem 0 0 0' }}>
              Count of blocked and confirmed fraud
            </p>
          </div>
          <div style={{ padding: '1.5rem', height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="colorBlock" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e82646" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#e82646" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-light)' }} dx={-10} />
                <Tooltip formatter={(value) => [value, "Blocked"]} contentStyle={{ background: 'var(--bg-card)', borderRadius: '0.5rem', border: '1px solid var(--border-color)', boxShadow: '0 0.5rem 1.2rem rgba(0,0,0,0.1)', color: 'var(--text-main)' }} />
                <Area type="monotone" dataKey="blocked_count" stroke="#e82646" strokeWidth={2} fillOpacity={1} fill="url(#colorBlock)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        

      </div>
      
      {/* Custom Tooltip for Map */}
      {tooltipData && (
        <div style={{
          position: 'fixed',
          top: tooltipPos.y - 10,
          left: tooltipPos.x + 10,
          pointerEvents: 'none',
          background: 'var(--bg-card)',
          padding: '0.75rem 1rem',
          borderRadius: '0.5rem',
          border: '1px solid var(--border-color)',
          boxShadow: '0 0.5rem 1.2rem rgba(0,0,0,0.1)',
          color: 'var(--text-main)',
          zIndex: 1000,
          fontSize: '0.875rem'
        }}>
          <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{tooltipData.country}</div>
          <div><span style={{ color: 'var(--text-light)' }}>Value:</span> ${Number(tooltipData.amount).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
          <div><span style={{ color: 'var(--text-light)' }}>Count:</span> {tooltipData.count} txs</div>
        </div>
      )}
    </div>
  )
}
