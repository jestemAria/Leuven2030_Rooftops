// ...existing code...
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';
import 'leaflet/dist/leaflet.css';

// 导入 leaflet 并暴露到 window（App.jsx 当前依赖 window.L）
import * as L from 'leaflet';
window.L = L;

createRoot(document.getElementById('root')).render(<App />);
// ...existing code...