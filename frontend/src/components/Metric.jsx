export default function Metric({ label, value, accent = 'cyan' }) { return <div className="metric"><span>{label}</span><strong className={`text-${accent}`}>{value ?? '—'}</strong></div> }
