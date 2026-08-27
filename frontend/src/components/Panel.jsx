import { motion } from 'framer-motion'
import { X } from 'lucide-react'
export default function Panel({ title, icon: Icon, children, className = '', onClose, side = 'left' }) {
  return <motion.section initial={{ opacity: 0, x: side === 'left' ? -28 : 28 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: side === 'left' ? -28 : 28 }} className={`glass-panel ${className}`}>
    <div className="panel-title"><span>{Icon && <Icon size={16} />} {title}</span>{onClose && <button className="icon-button" onClick={onClose}><X size={16}/></button>}</div>{children}
  </motion.section>
}
