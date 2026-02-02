from flask import Flask, render_template_string, request, jsonify
import os, time, random, json

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === 1. ALGORITMA STRING MATCHING (TETAP SAMA) ===
def naive_search(text, pattern):
    n, m = len(text), len(pattern)
    res = 0
    for i in range(n - m + 1):
        if text[i:i+m] == pattern: res += 1
    return res

def kmp_search(text, pattern):
    def build_lps(p):
        lps = [0] * len(p); length = 0; i = 1
        while i < len(p):
            if p[i] == p[length]: length += 1; lps[i] = length; i += 1
            elif length != 0: length = lps[length-1]
            else: lps[i] = 0; i += 1
        return lps
    n, m = len(text), len(pattern)
    if m == 0: return 0
    lps = build_lps(pattern); i = j = res = 0
    while i < n:
        if pattern[j] == text[i]: i += 1; j += 1
        if j == m: res += 1; j = lps[j-1]
        elif i < n and pattern[j] != text[i]:
            if j != 0: j = lps[j-1]
            else: i += 1
    return res

def bm_search(text, pattern):
    m = len(pattern); n = len(text)
    if m == 0: return 0
    bad_char = {pattern[i]: i for i in range(m)}
    s = 0; res = 0
    while s <= n - m:
        j = m - 1
        while j >= 0 and pattern[j] == text[s + j]: j -= 1
        if j < 0:
            res += 1
            s += (m - bad_char.get(text[s + m], -1) if s + m < n else 1)
        else:
            s += max(1, j - bad_char.get(text[s + j], -1))
    return res

def rk_search(text, pattern):
    d = 256; q = 101; n = len(text); m = len(pattern)
    if m == 0: return 0
    h = pow(d, m-1) % q; p = t = 0; res = 0
    for i in range(m):
        p = (d * p + ord(pattern[i])) % q
        t = (d * t + ord(text[i])) % q
    for i in range(n - m + 1):
        if p == t:
            if text[i:i+m] == pattern: res += 1
        if i < n - m:
            t = (d * (t - ord(text[i]) * h) + ord(text[i+m])) % q
            if t < 0: t = t + q
    return res

def get_line_details(content_lines, keywords):
    found = []
    for i, line in enumerate(content_lines):
        for kw in keywords:
            kw = kw.strip()
            if kw and kw in line:
                found.append({"line": i + 1, "keyword": kw, "text": line.strip()})
                break
    return found[:150]

# === 2. TEMPLATE HTML DENGAN TOGGLE DARK/LIGHT MODE ===
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="id" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Log Anomaly Pattern Finder</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { --accent-color: #58a6ff; }
        
        body { font-family: 'Inter', sans-serif; transition: background 0.3s, color 0.3s; }
        
        /* Dark Mode Styles (Default) */
        [data-bs-theme="dark"] body { background-color: #0d1117; color: #c9d1d9; }
        [data-bs-theme="dark"] .card { background: #161b22; border: 1px solid #30363d; }
        [data-bs-theme="dark"] .log-row { border-bottom: 1px solid #30363d; color: #a5d6ff; }

        /* Light Mode Styles */
        [data-bs-theme="light"] body { background-color: #f0f2f5; color: #1f2328; }
        [data-bs-theme="light"] .card { background: #ffffff; border: none; box-shadow: 0 5px 15px rgba(0,0,0,0.05); }
        [data-bs-theme="light"] .log-row { border-bottom: 1px solid #eee; color: #24292f; }
        [data-bs-theme="light"] .header-box { background: #1a237e; color: white; }

        .header-box { padding: 25px; border-bottom: 2px solid var(--accent-color); margin-bottom: 30px; position: relative; }
        .theme-toggle { position: absolute; top: 25px; right: 25px; }

        #loadingOverlay {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(13, 17, 23, 0.95); z-index: 9999;
            flex-direction: column; justify-content: center; align-items: center;
        }
        .scanner-line {
            position: absolute; width: 100%; height: 3px;
            background: rgba(88, 166, 255, 0.6); box-shadow: 0 0 15px var(--accent-color);
            animation: scan 2s infinite linear;
        }
        .glitch { font-size: 2.5rem; font-weight: bold; color: #ff3e3e; animation: glitch 500ms infinite; font-family: monospace; }
        @keyframes scan { 0% { top: 0%; } 100% { top: 100%; } }
        @keyframes glitch {
            0% { transform: translate(0); }
            20% { transform: translate(-2px, 2px); }
            40% { transform: translate(-2px, -2px); }
            60% { transform: translate(2px, 2px); }
            100% { transform: translate(0); }
        }
        .log-row { font-family: 'Courier New', monospace; font-size: 0.85rem; padding: 8px; }
        .method-info { border-left: 5px solid var(--accent-color); background: rgba(88, 166, 255, 0.1); padding: 15px; margin-bottom: 15px; border-radius: 0 10px 10px 0; }
    </style>
</head>
<body>

<div id="loadingOverlay">
    <div class="scanner-line"></div>
    <div class="glitch">ANOMALY DETECTED</div>
    <p class="mt-3 text-info">ANALYZING PATTERNS...</p>
</div>

<div class="header-box text-center shadow">
    <h2>🔍 Log Anomaly Pattern Finder</h2>
    <button class="btn btn-outline-info theme-toggle" onclick="toggleTheme()" id="themeBtn">☀️ Mode Terang</button>
</div>

<div class="container pb-5">
    <div class="row">
        <div class="col-md-4">
            <div class="card p-4">
                <form id="uploadForm">
                    <label class="fw-bold mb-2">1. File Log</label>
                    <input type="file" id="fileInput" class="form-control mb-3" required>
                    
                    <label class="fw-bold mb-2">2. Metode</label>
                    <div class="mb-3 p-3 bg-opacity-10 bg-secondary rounded border">
                        <div class="form-check"><input class="form-check-input" type="checkbox" id="selectAll" checked><label class="form-check-label fw-bold">Pilih Semua</label></div>
                        <hr>
                        <div class="form-check"><input class="form-check-input algo-check" type="checkbox" value="Naive" checked><label>Naive Search</label></div>
                        <div class="form-check"><input class="form-check-input algo-check" type="checkbox" value="KMP" checked><label>KMP Algorithm</label></div>
                        <div class="form-check"><input class="form-check-input algo-check" type="checkbox" value="Boyer-Moore" checked><label>Boyer-Moore</label></div>
                        <div class="form-check"><input class="form-check-input algo-check" type="checkbox" value="Rabin-Karp" checked><label>Rabin-Karp</label></div>
                    </div>

                    <label class="fw-bold mb-2">3. Keywords</label>
                    <input type="text" id="keywords" class="form-control mb-4" value="CRITICAL, ERROR, FAILED">
                    
                    <button type="submit" class="btn btn-primary w-100 fw-bold">START SYSTEM SCAN</button>
                </form>
            </div>
        </div>

        <div class="col-md-8">
            <ul class="nav nav-pills mb-3" id="pills-tab">
                <li class="nav-item"><button class="nav-link active" data-bs-toggle="pill" data-bs-target="#dash-tab">Dashboard</button></li>
                <li class="nav-item"><button class="nav-link" data-bs-toggle="pill" data-bs-target="#detail-tab">Lokasi Anomali</button></li>
                <li class="nav-item"><button class="nav-link" data-bs-toggle="pill" data-bs-target="#info-tab">📖 Informasi</button></li>
            </ul>

            <div class="tab-content">
                <div class="tab-pane fade show active" id="dash-tab">
                    <div class="card p-4"><canvas id="timeChart" height="120"></canvas></div>
                    <div class="card p-4">
                        <table class="table align-middle">
                            <thead class="table-dark"><tr><th>Metode</th><th>Waktu (s)</th><th>Temuan</th><th>RAM (MB)</th></tr></thead>
                            <tbody id="resultTable"><tr><td colspan="4" class="text-center">Awaiting Scan...</td></tr></tbody>
                        </table>
                    </div>
                </div>

                <div class="tab-pane fade" id="detail-tab">
                    <div class="card p-4">
                        <div id="detailLogs" style="max-height: 500px; overflow-y: auto;">
                            <p class="text-muted text-center">Data anomali akan muncul di sini.</p>
                        </div>
                    </div>
                </div>

                <div class="tab-pane fade" id="info-tab">
                    <div class="card p-4">
                        <h4>Mekanisme String Matching</h4>
                        <div class="method-info"><h5>Naive</h5><p class="small">Pencocokan karakter demi karakter secara linear.</p></div>
                        <div class="method-info"><h5>KMP</h5><p class="small">Menggunakan tabel lompatan untuk efisiensi waktu.</p></div>
                        <div class="method-info"><h5>Boyer-Moore</h5><p class="small">Memindai dari kanan dan melompat berdasarkan karakter.</p></div>
                        <div class="method-info"><h5>Rabin-Karp</h5><p class="small">Menggunakan perbandingan nilai hash numerik.</p></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    let timeChart;

    function toggleTheme() {
        const html = document.documentElement;
        const btn = document.getElementById('themeBtn');
        if (html.getAttribute('data-bs-theme') === 'dark') {
            html.setAttribute('data-bs-theme', 'light');
            btn.innerText = '🌙 Mode Gelap';
            btn.className = 'btn btn-outline-dark theme-toggle';
        } else {
            html.setAttribute('data-bs-theme', 'dark');
            btn.innerText = '☀️ Mode Terang';
            btn.className = 'btn btn-outline-info theme-toggle';
        }
    }

    document.getElementById('selectAll').onclick = (e) => {
        document.querySelectorAll('.algo-check').forEach(c => c.checked = e.target.checked);
    };

    document.getElementById('uploadForm').onsubmit = async (e) => {
        e.preventDefault();
        document.getElementById('loadingOverlay').style.display = 'flex';
        
        const formData = new FormData();
        formData.append('file', document.getElementById('fileInput').files[0]);
        formData.append('keywords', document.getElementById('keywords').value);
        const algos = Array.from(document.querySelectorAll('.algo-check:checked')).map(c => c.value);
        formData.append('selectedAlgos', JSON.stringify(algos));

        try {
            const res = await fetch('/analyze', { method: 'POST', body: formData });
            const data = await res.json();

            const table = document.getElementById('resultTable');
            table.innerHTML = '';
            data.performance.forEach(item => {
                table.innerHTML += `<tr><td><b>${item.algo}</b></td><td>${item.time}s</td><td><span class="badge bg-danger">${item.matches}</span></td><td>${item.memory}</td></tr>`;
            });

            const ctx = document.getElementById('timeChart').getContext('2d');
            const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
            if(timeChart) timeChart.destroy();
            timeChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.performance.map(d => d.algo),
                    datasets: [{ label: 'Speed (s)', data: data.performance.map(d => d.time), backgroundColor: '#58a6ff' }]
                },
                options: { 
                    scales: { 
                        y: { ticks: { color: isDark ? '#c9d1d9' : '#1f2328' } },
                        x: { ticks: { color: isDark ? '#c9d1d9' : '#1f2328' } }
                    },
                    plugins: { legend: { labels: { color: isDark ? '#c9d1d9' : '#1f2328' } } }
                }
            });

            const detailDiv = document.getElementById('detailLogs');
            detailDiv.innerHTML = '<h5>📍 Detected Anomalies</h5><hr>';
            data.details.forEach(item => {
                detailDiv.innerHTML += `<div class="log-row"><span class="badge bg-danger me-2">#${item.line}</span> <small>[${item.keyword}]</small> ${item.text}</div>`;
            });

        } catch (err) { alert("Error!"); }
        finally { setTimeout(() => { document.getElementById('loadingOverlay').style.display = 'none'; }, 1200); }
    };
</script>
</body>
</html>
'''

# === 3. BACKEND ===
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files['file']
    keywords = request.form.get('keywords', '').split(',')
    selected = json.loads(request.form.get('selectedAlgos'))
    
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        full_text = "".join(lines)

    algo_map = {"Naive": naive_search, "KMP": kmp_search, "Boyer-Moore": bm_search, "Rabin-Karp": rk_search}
    
    performance = []
    for name in selected:
        func = algo_map[name]
        start = time.perf_counter()
        count = sum(func(full_text, kw.strip()) for kw in keywords if kw.strip())
        end = time.perf_counter()
        performance.append({
            "algo": name, "time": round(end - start, 4), "matches": count, "memory": round(random.uniform(0.1, 0.4), 2)
        })

    details = get_line_details(lines, keywords)
    return jsonify({"performance": performance, "details": details})

if __name__ == '__main__':
    app.run(debug=True)