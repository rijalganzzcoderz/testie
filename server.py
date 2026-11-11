import os
import json
import html
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, quote

HOST = "127.0.0.1"
PORT = 8080
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
MAX_SIZE = 15 * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)

HTML = r"""
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RIJALGANZZ SYSTEM</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #050807;
    color: #00ff88;
    font-family: monospace;
}

header {
    padding: 22px;
    background: #08130e;
    border-bottom: 1px solid #00ff88;
}

header h1 {
    margin: 0;
    font-size: 22px;
}

header p {
    color: #75b99a;
    font-size: 12px;
}

.container {
    max-width: 900px;
    padding: 15px;
    margin: auto;
}

.card {
    background: #09120e;
    border: 1px solid #145b38;
    padding: 17px;
    border-radius: 9px;
    margin-bottom: 15px;
}

h2 {
    font-size: 16px;
    margin-top: 0;
}

button, .download {
    background: #00ff88;
    border: none;
    color: #001b0d;
    padding: 10px 14px;
    font-weight: bold;
    border-radius: 5px;
    cursor: pointer;
    margin: 4px 0;
    text-decoration: none;
    display: inline-block;
}

button:hover, .download:hover {
    background: #00c96b;
}

input[type=file] {
    width: 100%;
    margin: 12px 0;
    color: #fff;
}

#terminal {
    height: 180px;
    overflow-y: auto;
    background: #020503;
    padding: 12px;
    border: 1px solid #145b38;
    font-size: 12px;
    white-space: pre-wrap;
}

.file {
    padding: 12px;
    border-bottom: 1px solid #17452d;
    overflow-wrap: anywhere;
}

.file small {
    display: block;
    color: #91b6a0;
    margin: 5px 0;
}

.status {
    color: #8affb9;
    font-size: 12px;
}

.danger {
    background: #ff5555;
    color: white;
}

footer {
    text-align: center;
    padding: 20px;
    color: #527b62;
    font-size: 11px;
}
</style>
</head>

<body>

<header>
    <h1>RIJALGANZZ SYSTEM</h1>
    <p>LOCALHOST CONTROL PANEL // TERMUX EDITION</p>
</header>

<div class="container">

    <div class="card">
        <h2> SYSTEM INFORMATION</h2>
        <div id="systemInfo" class="status">
            Loading system information...
        </div>
    </div>

    <div class="card">
        <h2> FILE UPLOAD</h2>
        <p class="status">
            Pilih file yang ingin disimpan ke Termux.
            Maksimal 15 MB per file.
        </p>

        <input type="file" id="fileInput" multiple>

        <button onclick="uploadFiles()">UPLOAD FILE</button>
    </div>

    <div class="card">
        <h2> FILE MANAGER</h2>

        <button onclick="loadFiles()">REFRESH FILES</button>

        <div id="fileList" class="status">
            Loading files...
        </div>
    </div>

    <div class="card">
        <h2> TERMINAL</h2>

        <div id="terminal"></div>

        <button onclick="clearTerminal()">CLEAR TERMINAL</button>
    </div>

</div>

<footer>
    RIJALGANZZ SYSTEM // LOCALHOST VERSION
</footer>

<script>
const terminal = document.getElementById("terminal");

function log(message) {
    const time = new Date().toLocaleTimeString("id-ID");

    terminal.innerHTML +=
        "[" + time + "] " + message + "\n";

    terminal.scrollTop = terminal.scrollHeight;
}

function clearTerminal() {
    terminal.innerHTML = "";
}

function getSystemInfo() {
    const info = {
        Browser: navigator.userAgent,
        Platform: navigator.platform,
        Language: navigator.language,
        Online: navigator.onLine,
        Screen: screen.width + " x " + screen.height,
        CPU: navigator.hardwareConcurrency || "Unknown",
        Timezone: Intl.DateTimeFormat()
            .resolvedOptions().timeZone
    };

    document.getElementById("systemInfo").innerHTML =
        Object.entries(info)
        .map(([key, value]) =>
            "<p><b>" + key + ":</b> " +
            String(value).replace(/</g, "&lt;") +
            "</p>"
        ).join("");

    log("System information loaded.");
}

async function uploadFiles() {
    const input = document.getElementById("fileInput");
    const files = input.files;

    if (!files.length) {
        log("Pilih file terlebih dahulu.");
        return;
    }

    for (const file of files) {
        if (file.size > 15 * 1024 * 1024) {
            log("File terlalu besar: " + file.name);
            continue;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
            log("Uploading: " + file.name);

            const response = await fetch("/upload", {
                method: "POST",
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Upload gagal");
            }

            log("Upload berhasil: " + result.filename);

        } catch (error) {
            log("Upload gagal: " + error.message);
        }
    }

    input.value = "";
    loadFiles();
}

async function loadFiles() {
    const list = document.getElementById("fileList");

    try {
        const response = await fetch("/files");
        const result = await response.json();

        if (!response.ok) {
            throw new Error("Gagal mengambil daftar file");
        }

        if (!result.files.length) {
            list.innerHTML = "Belum ada file.";
            return;
        }

        list.innerHTML = result.files.map(file => `
            <div class="file">
                <b>${escapeHTML(file.name)}</b>
                <small>${formatSize(file.size)}</small>

                <a class="download"
                   href="/download/${encodeURIComponent(file.name)}">
                   DOWNLOAD
                </a>

                <button class="danger"
                    onclick="deleteFile('${encodeURIComponent(file.name)}')">
                    DELETE
                </button>
            </div>
        `).join("");

        log("File list updated.");

    } catch (error) {
        list.textContent = error.message;
        log(error.message);
    }
}

async function deleteFile(name) {
    const filename = decodeURIComponent(name);

    if (!confirm("Hapus " + filename + "?")) return;

    try {
        const response = await fetch("/delete/" + name, {
            method: "DELETE"
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Gagal menghapus file");
        }

        log("File deleted: " + filename);
        loadFiles();

    } catch (error) {
        log("Delete error: " + error.message);
    }
}

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576)
        return (bytes / 1024).toFixed(2) + " KB";

    return (bytes / 1048576).toFixed(2) + " MB";
}

getSystemInfo();
loadFiles();

log("RIJALGANZZ SYSTEM initialized.");
log("Connected to local Termux server.");
</script>

</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):

        if self.path == "/":
            body = HTML.encode()

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/files":
            files = []

            for name in os.listdir(UPLOAD_DIR):
                path = os.path.join(UPLOAD_DIR, name)

                if os.path.isfile(path):
                    files.append({
                        "name": name,
                        "size": os.path.getsize(path)
                    })

            return self.send_json({"files": files})

        if self.path.startswith("/download/"):
            name = unquote(self.path[len("/download/"):])

            if not name or os.path.basename(name) != name:
                return self.send_json(
                    {"error": "Invalid filename"}, 400
                )

            path = os.path.join(UPLOAD_DIR, name)

            if not os.path.isfile(path):
                return self.send_json(
                    {"error": "File not found"}, 404
                )

            size = os.path.getsize(path)
            mime = mimetypes.guess_type(name)[0]
            mime = mime or "application/octet-stream"

            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header(
                "Content-Disposition",
                "attachment; filename*=UTF-8''" + quote(name)
            )
            self.send_header("Content-Length", str(size))
            self.end_headers()

            with open(path, "rb") as file:
                while True:
                    chunk = file.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

            return

        self.send_error(404)

    def do_POST(self):

        if self.path != "/upload":
            return self.send_json(
                {"error": "Not found"}, 404
            )

        try:
            length = int(self.headers.get("Content-Length", 0))

            if length <= 0 or length > MAX_SIZE + 1024 * 1024:
                return self.send_json(
                    {"error": "Invalid upload size"}, 413
                )

            content_type = self.headers.get("Content-Type", "")

            if "multipart/form-data" not in content_type:
                return self.send_json(
                    {"error": "Invalid content type"}, 400
                )

            import cgi

            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": content_type,
                    "CONTENT_LENGTH": str(length)
                }
            )

            if "file" not in form:
                return self.send_json(
                    {"error": "No file selected"}, 400
                )

            item = form["file"]

            if isinstance(item, list):
                return self.send_json(
                    {"error": "Upload satu file per request"}, 400
                )

            filename = os.path.basename(
                os.path.basename(item.filename or "upload.bin")
            )

            if not filename:
                filename = "upload.bin"

            data = item.file.read(MAX_SIZE + 1)

            if len(data) > MAX_SIZE:
                return self.send_json(
                    {"error": "File exceeds 15 MB"}, 413
                )

            path = os.path.join(UPLOAD_DIR, filename)

            base, ext = os.path.splitext(filename)
            counter = 1

            while os.path.exists(path):
                filename = f"{base}_{counter}{ext}"
                path = os.path.join(UPLOAD_DIR, filename)
                counter += 1

            with open(path, "wb") as file:
                file.write(data)

            return self.send_json({
                "success": True,
                "filename": filename,
                "size": len(data)
            })

        except Exception as error:
            return self.send_json({
                "error": str(error)
            }, 500)

    def do_DELETE(self):

        if not self.path.startswith("/delete/"):
            return self.send_json(
                {"error": "Not found"}, 404
            )

        name = unquote(self.path[len("/delete/"):])

        if not name or os.path.basename(name) != name:
            return self.send_json(
                {"error": "Invalid filename"}, 400
            )

        path = os.path.join(UPLOAD_DIR, name)

        if not os.path.isfile(path):
            return self.send_json(
                {"error": "File not found"}, 404
            )

        os.remove(path)

        return self.send_json({
            "success": True,
            "message": "File deleted"
        })

    def log_message(self, format, *args):
        print("[SERVER]", format % args)


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)

    print("=" * 40)
    print(" RIJALGANZZ SYSTEM")
    print("=" * 40)
    print(f" Server: http://{HOST}:{PORT}")
    print(f" Upload: {UPLOAD_DIR}")
    print(" Press CTRL+C to stop")
    print("=" * 40)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()