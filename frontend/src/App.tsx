import { useEffect, useState } from 'react'
import WebApp from '@twa-dev/sdk'
import { motion } from 'framer-motion'
import confetti from 'canvas-confetti'
import { Howl } from 'howler'
import { TonConnectUIProvider } from '@tonconnect/ui-react'

function App() {
  const [honey, setHoney] = useState(0)
  const [hsp, setHsp] = useState(1.0)
  const [energy, setEnergy] = useState(200)

  useEffect(() => {
    WebApp.ready()
    WebApp.expand()

    // Aquí más adelante pediremos datos reales al backend
    setHoney(1234.5)
    setHsp(2.1)
    setEnergy(150)
  }, [])

  const tap = () => {
    if (energy <= 0) return
    setHoney(honey + hsp)
    setEnergy(energy - 1)

    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 }
    })

    new Howl({
      src: ['https://cdn.jsdelivr.net/gh/marmelab/gremlins.js@master/assets/horde/release-the-gremlins.mp3'],
      volume: 0.3
    }).play()

    WebApp.HapticFeedback.impactOccurred('heavy')
  }

  return (
    <TonConnectUIProvider manifestUrl="https://tu-dominio.onrender.com/tonconnect-manifest.json">
      <div className="min-h-screen flex flex-col items-center justify-center text-orange-400 px-4">
        <h1 className="text-5xl font-bold mb-8 animate-pulse">🐝 THE ONE HIVE</h1>
        
        <div className="text-2xl mb-2">🍯 Néctar: {Math.floor(honey)}</div>
        <div className="text-xl mb-2">🌐 HSP: x{hsp.toFixed(2)}</div>
        <div className="text-xl mb-8">⚡ Energía: {energy}/500</div>

        <motion.button
          whileTap={{ scale: 0.8 }}
          onTouchStart={tap}
          onMouseDown={tap}
          className="text-9xl select-none"
        >
          🐝
        </motion.button>

        <p className="mt-12 text-center opacity-70">
          Toca la abeja para generar néctar
        </p>
      </div>
    </TonConnectUIProvider>
  )
}

export default App
