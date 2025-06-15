# kobo_viewer.py - Zero-Dependency Kobo Data Viewer
import os
import csv
import json
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Configuration
PORT = 8501
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Kobo Data Viewer</title>
    <style>
        * { box-sizing: border-box; font-family: Arial, sans-serif; }
        body { margin: 0; padding: 20px; background-color: #f0f2f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; position: sticky; top: 0; }
        tr:hover { background-color: #f5f7fa; }
        .controls { display: flex; gap: 10px; margin-bottom: 20px; }
        input, button { padding: 10px; font-size: 16px; border-radius: 5px; }
        input { flex: 1; border: 1px solid #ddd; }
        button { background: #4a86e8; color: white; border: none; cursor: pointer; }
        button:hover { background: #3a76d8; }
        .json-view { white-space: pre-wrap; font-family: monospace; background: #f8f8f8; padding: 15px; border-radius: 5px; overflow: auto; max-height: 500px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Kobo Data Viewer</h1>
            <p>Zero-dependency CSV viewer | Running on port {port}</p>
        </div>
        
        <div class="card">
            <div class="controls">
                <input type="file" id="csvFile" accept=".csv" style="display:none">
                <button onclick="document.getElementById('csvFile').click()">📁 Upload CSV</button>
                <input type="text" id="githubUrl" placeholder="https://raw.githubusercontent.com/.../data.csv">
                <button onclick="loadFromGitHub()">⬇️ Load from GitHub</button>
            </div>
            
            <div id="dataContainer">
                {content}
            </div>
        </div>
    </div>
    
    <script>
        // Handle file upload
        document.getElementById('csvFile').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    processCSV(event.target.result);
                };
                reader.readAsText(file);
            }
        });
        
        // Load from GitHub
        function loadFromGitHub() {
            const url = document.getElementById('githubUrl').value;
            if (url) {
                fetch(url)
                    .then(response => response.text())
                    .then(data => processCSV(data))
                    .catch(error => showError('Failed to load: ' + error));
            }
        }
        
        // Process CSV data
        function processCSV(csvData) {
            fetch('/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ csv: csvData })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                } else {
                    displayData(data);
                }
            })
            .catch(error => showError('Processing error: ' + error));
        }
        
        // Display data
        function displayData(data) {
            let content = '';
            
            if (data.mode === 'table') {
                // Table view
                content = `<h3>${data.rows.length} Records</h3>
                          <div style="overflow-x: auto; max-height: 70vh;">
                          <table>
                              <thead><tr>${data.headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>
                              <tbody>
                                  ${data.rows.map(row => 
                                      `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`
                                  ).join('')}
                              </tbody>
                          </table></div>`;
            } else {
                // JSON view
                content = `<h3>First 3 Records</h3>
                          <div class="json-view">${JSON.stringify(data.rows.slice(0, 3), null, 2)}</div>
                          <button onclick="downloadCSV()" style="margin-top:15px">💾 Download CSV</button>`;
            }
            
            document.getElementById('dataContainer').innerHTML = content;
        }
        
        // Download CSV
        function downloadCSV() {
            const csvContent = "data:text/csv;charset=utf-8," + 
                encodeURIComponent(document.getElementById('csvContent').textContent);
            const link = document.createElement("a");
            link.setAttribute("href", csvContent);
            link.setAttribute("download", "kobo_data.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
        
        // Show error
        function showError(message) {
            document.getElementById('dataContainer').innerHTML = 
                `<div style="color:red; padding:20px; background:#ffe6e6; border-radius:5px;">
                    <strong>Error:</strong> ${message}
                </div>`;
        }
    </script>
</body>
</html>
"""

class KoboRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.format(
                port=PORT,
                content="<p>Upload a CSV file or enter a GitHub URL to begin</p>"
            ).encode())
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/process':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            try:
                # Parse CSV
                reader = csv.reader(data['csv'].splitlines())
                headers = next(reader)
                rows = [row for row in reader]
                
                # Return data in appropriate format
                response = {
                    'headers': headers,
                    'rows': rows,
                    'mode': 'table' if len(rows) < 1000 else 'json'
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e)}).encode())

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, KoboRequestHandler)
    print(f"Server running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop")
    webbrowser.open(f"http://localhost:{PORT}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
