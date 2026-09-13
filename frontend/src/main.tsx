import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// No <StrictMode>: its deliberate dev-mode double-invoke of effects opens
// and immediately closes a second WebSocket connection on every mount.
// That's harmless for a pure side-effect-free effect, but useGameSocket's
// connect/disconnect has broadcast-visible side effects on the SERVER
// (seat assignment, team auto-balance, notifying every other connected
// player) - the phantom connect+disconnect races real joins and corrupts
// lobby state for other players. Worth revisiting if this app grows enough
// non-networking UI code that StrictMode's other render-purity checks
// become valuable again.
createRoot(document.getElementById('root')!).render(<App />)
