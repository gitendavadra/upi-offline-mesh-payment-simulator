import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';

// In sandboxed/cloud environments, Vite HMR WebSockets are intentionally disabled or unrouted.
// Suppress benign Vite client WebSocket close unhandled rejections to keep console clean.
if (typeof window !== 'undefined') {
  window.addEventListener('unhandledrejection', (event) => {
    const msg = event.reason?.message || String(event.reason || '');
    const stack = event.reason?.stack || '';
    if (msg.includes('WebSocket closed without opened') || stack.includes('@vite/client')) {
      event.preventDefault();
    }
  });
}

createRoot(document.getElementById('root')!).render(<App />);
