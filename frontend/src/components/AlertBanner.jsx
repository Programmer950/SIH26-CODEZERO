import { AnimatePresence, motion } from 'framer-motion'
import { Siren, X } from 'lucide-react'

export default function AlertBanner({ alert, onClose }) {
  const plate = alert?.plate_text || alert?.plate || alert?.vehicle_plate || 'WATCHLIST MATCH'
  const alertKey = alert?.timestamp || alert?.id || `${alert?.camera_id || 'unknown'}-${plate}`

  return <div className="alert-stage"><AnimatePresence mode="wait">
    {alert && <motion.div
      key={alertKey}
      initial={{ opacity: 0, y: -50, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className="pointer-events-auto relative bg-rose-950/90 border border-rose-500/80 text-white p-4 rounded-xl shadow-[0_0_20px_rgba(225,29,72,0.4)] backdrop-blur-md flex items-start justify-between w-full max-w-md overflow-hidden"
    >
      <Siren className="mt-1 shrink-0 text-rose-400" size={20}/>
      <div className="ml-3 grid gap-1"><small className="font-mono text-[10px] tracking-widest text-rose-200">CRITICAL / LIVE WATCHLIST SIGNAL</small><strong className="font-mono text-xl tracking-wide">{plate}</strong><span className="font-mono text-[10px] text-rose-100">{alert?.camera_id || alert?.camera_name || 'UNKNOWN CAMERA'} · {alert?.alert?.reason || alert?.message || 'Unverified vehicle sighting detected'}</span></div>
      <button onClick={onClose} className="ml-3 rounded p-1 text-rose-100 hover:bg-rose-800/60" aria-label="Dismiss alert"><X size={18}/></button>
    </motion.div>}
  </AnimatePresence></div>
}
