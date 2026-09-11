import { useState, useEffect } from 'react';

interface Incident {
  id?: string;
  incident_id?: string;
  severity?: string;
  summary?: string;
  analysis?: string;
  recommended_action?: string;
  status?: string;
  resolution_message?: string;
  created_at?: string;
}

interface Metrics {
  cpu_percent: number;
  memory_percent: number;
  disk_usage_percent?: number;
}

interface TelemetryPoint {
  time: string;
  cpu: number;
  memory: number;
}

export default function App() {
  const [metrics, setMetrics] = useState<Metrics>({ cpu_percent: 0, memory_percent: 0, disk_usage_percent: 0 });
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryPoint[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  useEffect(() => {
    // 1. Fetch historical incidents from PostgreSQL
    fetch('http://localhost:8000/api/incidents')
      .then((res) => res.json())
      .then((data) => {
        if (data.incidents) setIncidents(data.incidents);
      })
      .catch((err) => console.error('Failed to load historical incidents:', err));

    // 2. Connect to WebSocket stream
    const ws = new WebSocket('ws://localhost:8000/ws/telemetry');

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'incident_report') {
        setIncidents((prev) => [data, ...prev]);
      } else if (data.type === 'incident_resolved') {
        setIncidents((prev) =>
          prev.map((inc) => {
            const currentId = inc.incident_id || inc.id;
            return currentId === data.id
              ? { ...inc, status: 'RESOLVED', resolution_message: data.message }
              : inc;
          })
        );
      } else if (data.cpu_percent !== undefined) {
        setMetrics(data);
        const timeLabel = new Date().toLocaleTimeString();
        setTelemetryHistory((prev) => [
          ...prev.slice(-14),
          { time: timeLabel, cpu: data.cpu_percent, memory: data.memory_percent },
        ]);
      }
    };

    return () => ws.close();
  }, []);

  const handleRemediate = async (incidentId: string, action: string, targetProcess: string | null = 'heavy_worker.py') => {
    try {
      await fetch('http://localhost:8000/api/remediate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          incident_id: incidentId,
          action: action,
          target_process: targetProcess,
        }),
      });
    } catch (error) {
      console.error('Failed to execute remediation:', error);
    }
  };

  return (
    <div style={{ backgroundColor: '#0b1329', color: '#f8fafc', minHeight: '100vh', padding: '20px', fontFamily: 'system-ui, sans-serif' }}>
      {/* Top Bar with Connection Status */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>AI Infrastructure Monitor</h1>
        <span
          style={{
            fontSize: '0.8rem',
            padding: '4px 10px',
            borderRadius: '12px',
            fontWeight: 600,
            backgroundColor: isConnected ? '#064e3b' : '#7f1d1d',
            color: isConnected ? '#34d399' : '#fca5a5',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          ● {isConnected ? 'Connected to Stream' : 'Disconnected'}
        </span>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '20px' }}>
        <div style={{ background: '#131f37', padding: '16px', borderRadius: '8px', border: '1px solid #1e2d4a' }}>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 700 }}>CPU USAGE</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#60a5fa', marginTop: '4px' }}>{metrics.cpu_percent}%</div>
        </div>
        <div style={{ background: '#131f37', padding: '16px', borderRadius: '8px', border: '1px solid #1e2d4a' }}>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 700 }}>MEMORY USAGE</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#34d399', marginTop: '4px' }}>{metrics.memory_percent}%</div>
        </div>
        <div style={{ background: '#131f37', padding: '16px', borderRadius: '8px', border: '1px solid #1e2d4a' }}>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 700 }}>DISK USAGE</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#fbbf24', marginTop: '4px' }}>{metrics.disk_usage_percent ?? 0}%</div>
        </div>
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '20px' }}>
        {/* Telemetry Visualizer */}
        <div style={{ background: '#131f37', padding: '20px', borderRadius: '8px', border: '1px solid #1e2d4a' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '0.9rem', fontWeight: 600, margin: 0, color: '#cbd5e1' }}>Real-Time Telemetry Trend</h2>
            <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem' }}>
              <span style={{ color: '#60a5fa', display: 'flex', alignItems: 'center', gap: '4px' }}>■ CPU</span>
              <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>■ RAM</span>
            </div>
          </div>

          <div style={{ height: '240px', display: 'flex', alignItems: 'flex-end', gap: '10px', padding: '10px 10px 0 10px', background: '#0b1329', borderRadius: '6px 6px 0 0', border: '1px solid #1e2d4a', borderBottom: 'none' }}>
            {telemetryHistory.length === 0 && (
              <div style={{ margin: 'auto', color: '#64748b', fontSize: '0.85rem' }}>Awaiting telemetry stream...</div>
            )}
            {telemetryHistory.map((point, idx) => (
              <div key={idx} style={{ flex: 1, display: 'flex', gap: '2px', height: '100%', alignItems: 'flex-end' }}>
                <div
                  style={{
                    flex: 1,
                    height: `${point.cpu}%`,
                    backgroundColor: point.cpu > 80 ? '#ef4444' : '#3b82f6',
                    borderRadius: '2px 2px 0 0',
                    transition: 'height 0.3s',
                  }}
                  title={`CPU: ${point.cpu}%`}
                />
                <div
                  style={{
                    flex: 1,
                    height: `${point.memory}%`,
                    backgroundColor: '#10b981',
                    borderRadius: '2px 2px 0 0',
                    transition: 'height 0.3s',
                  }}
                  title={`RAM: ${point.memory}%`}
                />
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '10px', padding: '8px 10px', background: '#070d1e', borderRadius: '0 0 6px 6px', border: '1px solid #1e2d4a', borderTop: 'none' }}>
            {telemetryHistory.map((point, idx) => (
              <div key={idx} style={{ flex: 1, textAlign: 'center', fontSize: '0.65rem', color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden' }}>
                {point.time.split(' ')[0]}
              </div>
            ))}
          </div>
        </div>

        {/* Autonomous SRE Feed */}
        <div style={{ background: '#131f37', padding: '20px', borderRadius: '8px', border: '1px solid #1e2d4a' }}>
          <h2 style={{ fontSize: '0.9rem', fontWeight: 600, marginTop: 0, marginBottom: '16px', color: '#cbd5e1' }}>Autonomous SRE Feed</h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '500px', overflowY: 'auto' }}>
            {incidents.length === 0 && <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>No active alerts recorded.</p>}

            {incidents.map((inc, idx) => {
              const incId = inc.incident_id || inc.id || `INC-${idx}`;
              const isResolved = inc.status === 'RESOLVED';

              // Fallback to current time if created_at is missing on live events
              const formattedTime = inc.created_at
                ? new Date(inc.created_at.endsWith('Z') ? inc.created_at : `${inc.created_at}Z`).toLocaleTimeString()
                : new Date().toLocaleTimeString();

              return (
                <div key={incId} style={{ background: '#0b1329', padding: '12px', borderRadius: '6px', border: '1px solid #1e2d4a', borderLeft: `4px solid ${isResolved ? '#22c55e' : '#f59e0b'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontSize: '0.65rem', fontWeight: 700, padding: '2px 6px', borderRadius: '3px', backgroundColor: isResolved ? '#14532d' : '#78350f', color: isResolved ? '#4ade80' : '#fde047' }}>
                      {isResolved ? 'RESOLVED' : inc.severity || 'WARNING'}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                      {incId} • {formattedTime}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc', marginBottom: '4px' }}>{inc.summary}</div>
                  <p style={{ fontSize: '0.75rem', color: '#94a3b8', margin: '4px 0' }}>{inc.analysis}</p>

                  {isResolved ? (
                    <div style={{ color: '#4ade80', fontSize: '0.75rem', marginTop: '8px', fontWeight: 500 }}>
                      ✓ {inc.resolution_message || 'Incident resolved.'}
                    </div>
                  ) : (
                    <div style={{ marginTop: '10px', display: 'flex', gap: '8px' }}>
                      <button onClick={() => handleRemediate(incId, 'kill_process', 'heavy_worker.py')} style={{ backgroundColor: '#dc2626', color: '#fff', border: 'none', padding: '6px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}>
                        Kill Process
                      </button>
                      <button onClick={() => handleRemediate(incId, 'clear_cache')} style={{ backgroundColor: '#2563eb', color: '#fff', border: 'none', padding: '6px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}>
                        Clear Cache
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}