import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css'; // <- 必须导入，启用 Tailwind 输出

// 使用 npm 的 leaflet JS 并暴露到 window（App.jsx 依赖 window.L）
import * as L from 'leaflet';
window.L = L;

createRoot(document.getElementById('root')).render(<App />);