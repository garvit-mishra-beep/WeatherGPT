"use client";

import React, { useRef, useState } from "react";
import { Search, MapPin, Navigation, Layers, CloudRain, X } from "lucide-react";

interface CityPreset {
  name: string;
  lat: number;
  lon: number;
}

const DEFAULT_CITIES: CityPreset[] = [
  { name: "Gwalior", lat: 26.2183, lon: 78.1828 },
  { name: "New Delhi", lat: 28.6139, lon: 77.2090 },
  { name: "Bhopal", lat: 23.2599, lon: 77.4126 },
  { name: "Indore", lat: 22.7196, lon: 75.8577 },
  { name: "Jabalpur", lat: 23.1815, lon: 79.9864 },
  { name: "Mumbai", lat: 19.0760, lon: 72.8777 },
  { name: "Jaipur", lat: 26.9124, lon: 75.7873 },
  { name: "Lucknow", lat: 26.8467, lon: 80.9462 },
];

export default function MapPage() {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [selectedCity, setSelectedCity] = useState("Gwalior");
  const [searchQuery, setSearchQuery] = useState("");
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [baseLayer, setBaseLayer] = useState<"satellite" | "street">("street");

  const sendMapMessage = (message: any) => {
    if (iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage(message, "*");
    }
  };

  const handleCitySelect = (city: CityPreset) => {
    setSelectedCity(city.name);
    sendMapMessage({
      action: "focusLocation",
      lat: city.lat,
      lon: city.lon,
      label: city.name,
    });
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      sendMapMessage({
        action: "searchCity",
        query: searchQuery.trim(),
      });
    }
  };

  const handleLocateUser = () => {
    sendMapMessage({ action: "locateUser" });
  };

  const toggleBaseLayer = (layer: "satellite" | "street") => {
    setBaseLayer(layer);
    sendMapMessage({
      action: "selectBaseLayer",
      layerType: layer,
    });
  };

  return (
    <div className="relative w-full h-[calc(100vh-8.5rem)] rounded-2xl overflow-hidden border border-slate-200 shadow-sm bg-[#F8FAF8]">
      {/* Top Floating Bar: Search & City Chips */}
      <div className="absolute top-3 left-3 right-3 z-10 flex flex-col gap-2 max-w-2xl mx-auto pointer-events-auto">
        {/* Search Pill */}
        <form
          onSubmit={handleSearchSubmit}
          className="flex items-center gap-2 bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-full border border-slate-200 shadow-md"
        >
          <Search className="w-4 h-4 text-green-800 shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search district, city or coordinate..."
            className="w-full text-xs font-medium text-slate-800 placeholder-slate-400 bg-transparent focus:outline-none"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="p-1 text-slate-400 hover:text-slate-600 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            type="button"
            onClick={handleLocateUser}
            title="My Location"
            className="p-1.5 text-green-800 hover:bg-green-50 rounded-full transition-colors cursor-pointer"
          >
            <Navigation className="w-4 h-4" />
          </button>
        </form>

        {/* Quick Location Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
          {DEFAULT_CITIES.map((city) => {
            const isSelected = selectedCity.toLowerCase() === city.name.toLowerCase();
            return (
              <button
                key={city.name}
                onClick={() => handleCitySelect(city)}
                className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition-all shadow-sm cursor-pointer ${
                  isSelected
                    ? "bg-green-800 text-white shadow-green-900/20"
                    : "bg-white/95 text-slate-700 hover:bg-slate-100 border border-slate-200"
                }`}
              >
                {city.name}
              </button>
            );
          })}
        </div>
      </div>

      {/* Layer Control Pills (Bottom Right) */}
      <div className="absolute bottom-4 right-4 z-10 flex items-center gap-1.5 bg-white/95 backdrop-blur-md p-1.5 rounded-xl border border-slate-200 shadow-md text-xs font-semibold text-slate-700 pointer-events-auto">
        <button
          onClick={() => toggleBaseLayer("street")}
          className={`px-2.5 py-1 rounded-lg transition-colors cursor-pointer ${
            baseLayer === "street" ? "bg-green-800 text-white" : "hover:bg-slate-100"
          }`}
        >
          Street
        </button>
        <button
          onClick={() => toggleBaseLayer("satellite")}
          className={`px-2.5 py-1 rounded-lg transition-colors cursor-pointer ${
            baseLayer === "satellite" ? "bg-green-800 text-white" : "hover:bg-slate-100"
          }`}
        >
          Satellite
        </button>
      </div>

      {/* Exposure / Context Badge (Bottom Left) */}
      <div className="absolute bottom-4 left-4 z-10 hidden sm:flex items-center gap-2 bg-white/95 backdrop-blur-md px-3 py-2 rounded-xl border border-slate-200 shadow-md text-xs pointer-events-auto">
        <MapPin className="w-4 h-4 text-green-800" />
        <div>
          <span className="font-bold text-slate-900">{selectedCity} District Focus</span>
          <span className="text-slate-500 block text-[10px]">
            Meteorological Telemetry & Rain Radar Active
          </span>
        </div>
      </div>

      {/* Loading Overlay */}
      {!isMapLoaded && (
        <div className="absolute inset-0 z-0 flex items-center justify-center bg-slate-100">
          <div className="flex items-center gap-2 bg-white px-4 py-2.5 rounded-xl border border-slate-200 shadow-sm text-xs font-medium text-slate-600">
            <div className="w-4 h-4 border-2 border-green-800 border-t-transparent rounded-full animate-spin" />
            Loading Meteorological Map...
          </div>
        </div>
      )}

      {/* Primary Map Viewport (Iframe of weather_map.html) */}
      <iframe
        ref={iframeRef}
        src="/weather_map.html"
        onLoad={() => setIsMapLoaded(true)}
        className="w-full h-full border-0"
        title="VAYUBODHAK Meteorological Map"
      />
    </div>
  );
}
