/// pro.js — debug-enhanced (drop-in). Add this replacing your current pro.js.
// It logs all major steps, shows an error banner, and writes request/response details to UI.
(() => {
  const API_BASE = 'http://localhost:8000'; // change if needed
  const USE_MOCK = false;

  // DOM helpers
  const $ = (id) => document.getElementById(id);

  // UI elements
  const cityInput = $('cityInput');
  const checkBtn = $('checkBtn');
  const resetBtn = $('resetBtn');

  const emptyState = $('emptyState');
  const resultState = $('resultState');
  const cityName = $('cityName');
  const coordsEl = $('coords');
  const riskPill = $('riskPill');
  const scoreEl = $('score');
  const reasonEl = $('reason');
  const r3 = $('r3');
  const r24 = $('r24');
  const alertsCount = $('alertsCount');
  const adviceList = $('adviceList');

  // create a visible banner for errors
  let banner = document.getElementById('debugBanner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'debugBanner';
    banner.style.position = 'fixed';
    banner.style.left = '12px';
    banner.style.right = '12px';
    banner.style.top = '12px';
    banner.style.padding = '10px 12px';
    banner.style.zIndex = '9999';
    banner.style.borderRadius = '8px';
    banner.style.display = 'none';
    banner.style.fontWeight = '700';
    banner.style.boxShadow = '0 6px 18px rgba(0,0,0,0.12)';
    document.body.appendChild(banner);
  }
  function showBanner(msg, isError = true) {
    banner.textContent = msg;
    banner.style.background = isError ? '#ffefef' : '#e8f9ef';
    banner.style.color = isError ? '#9b111e' : '#064e3b';
    banner.style.display = 'block';
    setTimeout(()=>{ banner.style.display = 'none'; }, 8000);
  }

  // Map init
  let map = null;
  let marker = null;
  function ensureMap(lat = 20.5937, lon = 78.9629) {
    if (!window.L) {
      console.warn("Leaflet not loaded (window.L missing)");
      showBanner("Leaflet not loaded — check pro.html includes Leaflet script", true);
      return;
    }
    if (!map) {
      map = L.map('map', { zoomControl: true, attributionControl: false }).setView([lat, lon], 6);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
      console.log("Map initialized");
    }
  }
  function setMapMarker(lat, lon, popupHtml) {
    ensureMap(lat, lon);
    if (!map) return;
    if (marker) marker.remove();
    marker = L.marker([lat, lon]).addTo(map).bindPopup(popupHtml).openPopup();
    map.setView([lat, lon], 11);
  }

  // utilities
  function escapeHtml(s='') { return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

  // Backend wrapper with logs
  async function backendFetchJson(url, opts = {}) {
    console.log("[fetch] ->", url, opts.method || 'GET');
    try {
      const res = await fetch(url, opts);
      console.log("[fetch] status:", res.status, res.statusText);
      const text = await res.text();
      // try parse JSON but keep raw text
      try {
        const json = JSON.parse(text);
        console.log("[fetch] json:", json);
        return json;
      } catch (e) {
        console.log("[fetch] text:", text);
        // if not JSON, throw to be handled
        throw new Error("Non-JSON response: " + text);
      }
    } catch (err) {
      console.error("[fetch] error:", err);
      throw err;
    }
  }

  // API calls
  async function callGeocode(city) {
    if (USE_MOCK) return { name: city + ' (mock)', lat: 19.076, lon: 72.8777 };
    return await backendFetchJson(`${API_BASE}/geocode?city=${encodeURIComponent(city)}`);
  }
  async function callRisk(lat, lon) {
    if (USE_MOCK) return { level: 'Moderate', score: 52, reason: 'Mock', signals:{rain_3h_mm:12,rain_24h_mm:68}, alerts:[] };
    return await backendFetchJson(`${API_BASE}/risk?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`);
  }
  async function callPredictFlood(city) {
    if (USE_MOCK) return { city, prediction:0.6, status:'✅ SAFE', checklist:'Mock' };
    return await backendFetchJson(`${API_BASE}/predict_flood?city=${encodeURIComponent(city)}`);
  }

  // Render / show combined result (with visible debug area)
  function showCombinedResult(geo, riskResult, aiResult) {
    if (emptyState) emptyState.style.display = 'none';
    if (resultState) resultState.style.display = 'block';

    cityName.textContent = geo?.name || 'Unknown';
    coordsEl.textContent = geo?.lat ? `Lat: ${Number(geo.lat).toFixed(4)} • Lon: ${Number(geo.lon).toFixed(4)}` : 'Coords not available';

    let label = riskResult?.level || (aiResult && (aiResult.status && (aiResult.status.includes('WARNING') ? 'High' : 'Low'))) || 'Unknown';
    let scoreText = '';
    if (aiResult && typeof aiResult.prediction === 'number') scoreText = `AI Predicted: ${aiResult.prediction.toFixed(2)}`;
    if (riskResult?.score != null) scoreText = (scoreText ? scoreText + ' • ' : '') + `Engine: ${riskResult.score}`;
    scoreEl.textContent = scoreText || 'Score: —';

    riskPill.className = 'pill ' + (label === 'High' ? 'high' : label === 'Moderate' ? 'mod' : 'low');
    riskPill.textContent = label;

    reasonEl.textContent = (aiResult?.status ? `AI: ${aiResult.status}. ` : '') + (riskResult?.reason ? `Rule: ${riskResult.reason}` : '');

    r3.textContent = String(riskResult?.signals?.rain_3h_mm ?? aiResult?.weather?.current?.rain?.['1h'] ?? '—');
    r24.textContent = String(riskResult?.signals?.rain_24h_mm ?? aiResult?.weather?.current?.rain?.['24h'] ?? '—');
    alertsCount.textContent = String((riskResult?.alerts?.length || 0) + (aiResult?.status && aiResult.status.includes('WARNING') ? 1 : 0));

    adviceList.innerHTML = '';
    if (aiResult?.checklist) {
      const li = document.createElement('li'); li.textContent = aiResult.checklist; adviceList.appendChild(li);
    }
    if (riskResult?.alerts && riskResult.alerts.length) {
      riskResult.alerts.forEach(a => { const li = document.createElement('li'); li.textContent = a; adviceList.appendChild(li); });
    }
    if (!adviceList.childElementCount) {
      const li = document.createElement('li'); li.textContent = 'Follow local advisories.'; adviceList.appendChild(li);
    }

    // map marker
    if (geo?.lat && geo?.lon) {
      setMapMarker(Number(geo.lat), Number(geo.lon), `<strong>${escapeHtml(geo.name)}</strong><br/>${escapeHtml(label)}<br/>${escapeHtml(scoreEl.textContent||'')}`);
    } else {
      console.warn("Geo coords missing; map marker not set");
    }
  }

  // Handler
  async function handleCheck() {
    const city = (cityInput.value || '').trim();
    if (!city) { showBanner("Please enter a city name", true); return; }
    checkBtn.disabled = true; checkBtn.textContent = 'Checking...';
    console.info("Checking city:", city);
    try {
      const geo = await callGeocode(city).catch(e => { throw new Error("Geocode failed: " + (e.message || e)); });
      const [riskResult, aiResult] = await Promise.all([
        callRisk(geo.lat, geo.lon).catch(err => { console.warn("Risk failed:", err); return null; }),
        callPredictFlood(city).catch(err => { console.warn("AI predict failed:", err); return null; })
      ]);
      if (!riskResult && !aiResult) {
        throw new Error("Both risk and AI prediction failed. Check backend logs and API keys.");
      }
      showCombinedResult(geo, riskResult || {}, aiResult || {});
      console.info("Showed result for:", city);
    } catch (err) {
      console.error("Check error:", err);
      showBanner("Error: " + (err.message || err), true);
    } finally {
      checkBtn.disabled = false; checkBtn.textContent = 'Check Risk';
    }
  }

  function handleReset() {
    cityInput.value = '';
    if (emptyState) emptyState.style.display = 'block';
    if (resultState) resultState.style.display = 'none';
  }

  // init
  function init() {
    ensureMap();
    if (checkBtn) checkBtn.addEventListener('click', handleCheck);
    if (resetBtn) resetBtn.addEventListener('click', handleReset);

    window.addEventListener('error', (e) => {
      console.error("Window error:", e.error || e.message);
      showBanner("Unhandled error: " + (e.error?.message || e.message || e.toString()), true);
    });
    console.log("pro.js initialized (debug mode)");
    showBanner("Frontend loaded — open Console for detailed logs", false);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

})();
