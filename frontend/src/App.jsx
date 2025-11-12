import React, { useState, useEffect, useRef, useMemo } from 'react';

// --- MOCK DATA ---
// This data simulates the Top 200 list, seeded with data from the NGO's PPT.
// In a real application, you would fetch this from your backend/API.
const MOCK_ROOFTOPS = [
    {'rank': 1, 'name': "AB Inbev", 'area': 56691, 'co2': 3500, 'type': "EPDM", 'lat': 50.8930, 'lng': 4.7081},
    {'rank': 2, 'name': "UZ Gasthuisberg", 'area': 32149, 'co2': 2000, 'type': "Bitumen", 'lat': 50.8841, 'lng': 4.6788},
    {'rank': 3, 'name': "Commscope", 'area': 34308, 'co2': 2100, 'type': "EPDM", 'lat': 50.8870, 'lng': 4.6950},
    {'rank': 4, 'name': "Terumo Europe", 'area': 17971, 'co2': 1100, 'type': "Steel", 'lat': 50.8710, 'lng': 4.7200},
    {'rank': 5, 'name': "Depot Aveve", 'area': 14160, 'co2': 900, 'type': "Bitumen", 'lat': 50.9000, 'lng': 4.6650},
    {'rank': 6, 'name': "Beneo-Remy", 'area': 13190, 'co2': 850, 'type': "EPDM", 'lat': 50.8650, 'lng': 4.7100},
    // ... (omitting ranks 7-199 for brevity in this display)
    // Fill the rest of the 180 simulated data points
    ...Array.from({ length: 194 }, (_, i) => ({
      'rank': i + 7,
      'name': `Other Large Site ${i + 7}`,
      'area': Math.floor(Math.random() * (4500 - 500 + 1) + 500),
      'co2': Math.floor(Math.random() * (250 - 30 + 1) + 30),
      'type': ["Slate", "EPDM", "Tile"][Math.floor(Math.random() * 3)],
      'lat': 50.85 + Math.random() * 0.1,
      'lng': 4.65 + Math.random() * 0.15,
    }))
];

// --- MAIN APP COMPONENT ---
function App() {
  const [rooftops] = useState(MOCK_ROOFTOPS);
  const [selectedRooftop, setSelectedRooftop] = useState(null);

  // --- Filter state: minimum area (m²) ---
  const [minArea, setMinArea] = useState(0);
  // derived filtered list used by map and list UI
  const filteredRooftops = useMemo(
    () => rooftops.filter(r => r.area >= (minArea || 0)).sort((a,b)=>a.rank-b.rank),
    [rooftops, minArea]
  );
  
  // Refs for Leaflet map integration
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({}); // Store markers { id: marker }

  const LEUVEN_CENTER = [50.8792, 4.7001];

  // 1. Initialize Map on first render — wait for window.L if necessary
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return; // Only init once

    const initMap = (L) => {
      const map = L.map(mapContainerRef.current).setView(LEUVEN_CENTER, 12);
      
      L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
      }).addTo(map);
      
      mapInstanceRef.current = map;

      // markers will be managed by a separate effect (so they react to filters)
    };

    if (window.L) {
      initMap(window.L);
    } else {
      // Poll briefly for Leaflet to become available (CDN script may load slightly later)
      let tries = 0;
      const iv = setInterval(() => {
        if (window.L) {
          clearInterval(iv);
          initMap(window.L);
        } else if (++tries > 50) { // ~5s max
          clearInterval(iv);
          console.error('Leaflet not found after waiting — map will not initialize.');
        }
      }, 100);
    }

    // Cleanup
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [rooftops]);

  // 1b. Update markers whenever filteredRooftops changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // remove old markers
    Object.values(markersRef.current).forEach(m => m.remove());
    markersRef.current = {};

    // add markers for filtered roofs
    const L = window.L;
    if (!L) return;
    const newMarkers = {};
    filteredRooftops.forEach(roof => {
      const marker = L.marker([roof.lat, roof.lng]).addTo(map).bindTooltip(roof.name);
      marker.on('click', () => setSelectedRooftop(roof));
      newMarkers[roof.rank] = marker;
    });
    markersRef.current = newMarkers;

    // if selected rooftop is no longer in filtered list, clear selection
    if (selectedRooftop && !filteredRooftops.find(r => r.rank === selectedRooftop.rank)) {
      setSelectedRooftop(null);
    }
  }, [filteredRooftops]); // eslint-disable-line react-hooks/exhaustive-deps

  // 2. Handle map view changes when a rooftop is selected
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !selectedRooftop) return;

    const marker = markersRef.current[selectedRooftop.rank];
    if (!marker) return;

    map.flyTo([selectedRooftop.lat, selectedRooftop.lng], 16); // Zoom in
    
    // simpler popup binding to avoid API mismatch
    marker.bindPopup(`
      <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,'Helvetica Neue',Arial;">
        <h4 style="margin:0 0 4px 0; font-weight:700; color:#166534">#${selectedRooftop.rank}: ${selectedRooftop.name}</h4>
        <p style="margin:0; font-size:12px"><strong>Area:</strong> ${selectedRooftop.area.toLocaleString()} m²</p>
        <p style="margin:0; font-size:12px"><strong>CO₂:</strong> ${selectedRooftop.co2.toLocaleString()} tons/yr</p>
      </div>
    `).openPopup();

  }, [selectedRooftop]);

  return (
    <div className="flex h-screen w-screen bg-gray-100 font-sans overflow-hidden">
      
      {/* --- 1. Map Container --- */}
      <div className="flex-1 h-full relative min-h-0 flex">
        {/* map pane fills available space */}
        <div className="flex-1 min-h-0">
          <div ref={mapContainerRef} className="h-full w-full" />
        </div>
        {/* end map pane */}
         <div className="absolute top-4 left-4 z-[1000] p-3 bg-white rounded-lg shadow-lg">
           <h1 className="text-xl font-bold text-gray-800 m-0">☀️ Leuven Solar Rooftop Analyzer</h1>
           <p className="text-sm text-gray-600 m-0">Top 200 Potential Sites</p>
         </div>
       </div>
 
       {/* --- 2. Sidebar (List & Details) --- */}
      <aside className="w-[420px] flex-shrink-0 h-full bg-white shadow-xl flex flex-col z-10 overflow-hidden">
        {/* --- Filter controls --- */}
        <div className="p-4 border-b bg-white">
          <label className="text-sm font-medium text-gray-700">Minimum area (m²): <span className="font-semibold">{minArea}</span></label>
          <input
            type="range"
            min="0"
            max="60000"
            step="100"
            value={minArea}
            onChange={e => setMinArea(Number(e.target.value))}
            className="w-full mt-2"
          />
          <div className="flex items-center gap-2 mt-2">
            <input
              type="number"
              min="0"
              value={minArea}
              onChange={e => setMinArea(Number(e.target.value || 0))}
              className="w-28 p-1 border rounded"
            />
            <button onClick={() => setMinArea(0)} className="px-3 py-1 bg-gray-100 rounded text-sm">Reset</button>
            <div className="ml-auto text-xs text-gray-500">Showing {filteredRooftops.length} / {rooftops.length}</div>
          </div>
        </div>
        
        {/* --- Details Pane --- */}
        <div className="p-5 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Rooftop Details</h2>
          {selectedRooftop ? (
            <RooftopDetails rooftop={selectedRooftop} />
          ) : (
            <div className="flex items-center justify-center h-24 bg-gray-50 rounded-lg">
              <p className="text-gray-500">Click a site on the map or list</p>
            </div>
          )}
        </div>

        {/* --- List Pane --- */}
        <div className="flex-1 overflow-y-auto">
          <h2 className="text-lg font-semibold text-gray-800 p-5 sticky top-0 bg-white border-b border-gray-200">
            Potential Rooftops List
          </h2>
          <RooftopList 
            rooftops={filteredRooftops}
            selectedRank={selectedRooftop?.rank}
            onSelect={setSelectedRooftop}
          />
        </div>

      </aside>
    </div>
  );
}

// --- SUB-COMPONENTS ---

function RooftopDetails({ rooftop }) {
  return (
    <div className="space-y-4">
      <h3 className="text-xl font-bold text-green-700">
        #{rooftop.rank}: {rooftop.name}
      </h3>
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-green-50 p-3 rounded-lg">
          <p className="text-xs font-medium text-green-800 uppercase">Usable Area</p>
          <p className="text-2xl font-bold text-green-900">{rooftop.area.toLocaleString()} <span className="text-lg">m²</span></p>
        </div>
        <div className="bg-blue-50 p-3 rounded-lg">
          <p className="text-xs font-medium text-blue-800 uppercase">Est. CO₂ Reduction</p>
          <p className="text-2xl font-bold text-blue-900">{rooftop.co2.toLocaleString()} <span className="text-lg">tons/yr</span></p>
        </div>
      </div>
      <div className="bg-gray-50 p-3 rounded-lg">
        <p className="text-sm font-medium text-gray-700">Rooftop Type</p>
        <p className="text-lg font-semibold text-gray-900">{rooftop.type}</p>
      </div>
    </div>
  );
}

function RooftopList({ rooftops, selectedRank, onSelect }) {
  return (
    <ul className="divide-y divide-gray-100">
      {rooftops.map(roof => (
        <li 
          key={roof.rank}
          onClick={() => onSelect(roof)}
          className={`p-4 cursor-pointer hover:bg-green-50 transition-colors ${selectedRank === roof.rank ? 'bg-green-100 border-l-4 border-green-600' : ''}`}
        >
          <div className="flex justify-between items-center mb-1">
            <p className="text-sm font-semibold text-gray-900">
              <span className={`inline-block w-6 text-right mr-2 ${selectedRank === roof.rank ? 'font-bold text-green-700' : 'text-gray-500'}`}>
                #{roof.rank}
              </span>
              {roof.name}
            </p>
            <span className="text-xs font-medium text-gray-600">{roof.area.toLocaleString()} m²</span>
          </div>
          <p className="text-xs text-right text-blue-600">{roof.co2.toLocaleString()} tons/yr CO₂ reduction</p>
        </li>
      ))}
    </ul>
  );
}

export default App;