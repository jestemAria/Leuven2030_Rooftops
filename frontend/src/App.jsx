import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

export default function App() {
  return (
    <main className="min-h-screen grid place-items-center bg-gray-50">
      <div className="max-w-md w-full p-8 rounded-2xl shadow-lg bg-white">
        <h1 className="text-2xl font-bold mb-2">Hello, Tailwind + Vite + React 👋</h1>
        <p className="text-gray-600 mb-6">
          You’re all set. Edit <code className="font-mono">src/App.tsx</code> and save.
        </p>
        <button className="px-4 py-2 rounded-xl border hover:bg-gray-100 active:scale-[.98] transition">
          Nice button
        </button>
      </div>
    </main>
  );
}

