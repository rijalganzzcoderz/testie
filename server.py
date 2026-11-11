from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from datetime import datetime
import json
import mimetypes
import os
import re

HOST = "127.0.0.1"
PORT = 8080
MAX_SIZE = 20 * 1024 * 1024

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

HTML = r"""
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RIJALGANZZ SYSTEM</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:18px;background:#050a08;color:#00ff88;font-family:monospace}
.container{max-width:650px;margin:auto}
h1{text-align:center;text-shadow:0 0 12px #00ff88}
.box{border:1px solid #087c48;padding:15px;margin:14px 0;border-radius:8px;background:#08130e}
button{background:#062d1b;color:#00ff88;border:1px solid #00ff88;padding:12px;margin:5px 0;width:100%;border-radius:5px;font-weight:bold}
button:active{background:#00ff88;color:black}
video,img,audio{width:100%;margin-top:10px;border-radius:8px}
video{background:#000}
#status{color:white;white-space:pre-wrap;overflow-wrap:anywhere}
.item{border:1px solid #176b43;padding:10px;margin:10px 0;border-radius:6px}
.item img{max-height:250px;object-fit:contain}
.item audio{width:100%}
small{color:#8ba99a}
input{max-width:100%;margin:10px 0}
</style>
</head>
<body>
<div class="container">
<h1>RIJALGANZZ SYSTEM</h1>
<p style="text-align:center">LOCAL DEVICE DASHBOARD</p>

<div class="box">
<h3>CAMERA</h3>
<video id="video" autoplay playsinline></video>
<button onclick="startCamera()">AKTIFKAN KAMERA</button>
<button onclick="takePhoto()">AMBIL FOTO</button>
<button onclick="stopCamera()">MATIKAN KAMERA</button>
</div>

<div class="box">
<h3>VOICE RECORDING</h3>
<p><small>Rekam suara maksimal 10 detik.</small></p>
<button onclick="recordMic()">MULAI REKAM VN</button>
<audio id="preview" controls></audio>
</div>

<div class="box">
<h3>LOCATION</h3>
<button onclick="getLocation()">AMBIL LOKASI</button>
</div>

<div class="box">
<h3>CONTACTS</h3>
<button onclick="getContacts()">PILIH KONTAK</button>
<small>Kontak dipilih secara manual. Browser harus mendukung Contact Picker.</small>
</div>

<div class="box">
<h3>FILE UPLOAD</h3>
<input type="file" id="files" multiple>
<button onclick="sendFiles()">KIRIM FILE TERPILIH</button>
</div>

<div class="box">
<h3>MEDIA GALLERY</h3>
<button onclick="loadMedia()">REFRESH GALERI</button>
<div id="gallery"></div>
</div>

<div class="box">
<h3>STATUS</h3>
<div id="status">System ready...</div>
</div>
</div>

<script>
const statusBox = document.getElementById("status");
const video = document.getElementById("video");
const preview = document.getElementById("preview");
const gallery = document.getElementById("gallery");

let cameraStream = null;
let recording = false;

function status(message){
    statusBox.textContent += "\\n> " + message;
}

async function sendData(type,data){
    try{
        const response = await fetch("/api/data",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({type,data})
        });
        if(!response.ok) throw new Error("Server error");
        status(type + " berhasil dikirim");
    }catch(e){
        status("Gagal mengirim: " + e.message);
    }
}

async function uploadBlob(type,blob,filename){
    const form = new FormData();
    form.append("type",type);
    form.append("file",blob,filename);

    try{
        const response = await fetch("/api/upload",{
            method:"POST",
            body:form
        });

        const result = await response.json();
        if(!response.ok) throw new Error(result.error || "Upload gagal");

        status("Berhasil disimpan: " + result.filename);

        if(type === "camera" || type === "microphone"){
            loadMedia();
        }
    }catch(e){
        status(e.message);
    }
}

async function startCamera(){
    try{
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video:true,
            audio:false
        });

        video.srcObject = cameraStream;
        status("Kamera aktif");
    }catch(e){
        status("Kamera gagal: " + e.message);
    }
}

function stopCamera(){
    if(cameraStream){
        cameraStream.getTracks().forEach(t => t.stop());
        cameraStream = null;
        video.srcObject = null;
        status("Kamera dimatikan");
    }
}

function takePhoto(){
    if(!cameraStream){
        status("Aktifkan kamera terlebih dahulu");
        return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    canvas.getContext("2d").drawImage(video,0,0);

    canvas.toBlob(blob=>{
        if(blob){
            const filename = "photo_" + Date.now() + ".jpg";
            uploadBlob("camera",blob,filename);
        }
    },"image/jpeg",0.9);
}

async function recordMic(){
    if(recording) return;

    try{
        const stream = await navigator.mediaDevices.getUserMedia({
            audio:true
        });

        const mime = MediaRecorder.isTypeSupported("audio/webm")
            ? "audio/webm"
            : "";

        const recorder = new MediaRecorder(
            stream,
            mime ? {mimeType:mime} : undefined
        );

        const chunks = [];
        recording = true;

        recorder.ondataavailable = e=>{
            if(e.data.size) chunks.push(e.data);
        };

        recorder.onstop = ()=>{
            recording = false;
            stream.getTracks().forEach(t=>t.stop());

            const blob = new Blob(chunks,{
                type:recorder.mimeType || "audio/webm"
            });

            preview.src = URL.createObjectURL(blob);

            const filename = "vn_" + Date.now() + ".webm";
            uploadBlob("microphone",blob,filename);
            status("Rekaman selesai");
        };

        recorder.start();
        status("VN sedang direkam...");

        setTimeout(()=>{
            if(recorder.state === "recording"){
                recorder.stop();
            }
        },10000);

    }catch(e){
        recording = false;
        status("Mikrofon gagal: " + e.message);
    }
}

function getLocation(){
    if(!navigator.geolocation){
        status("Lokasi tidak didukung browser");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        position=>{
            const data = {
                latitude:position.coords.latitude,
                longitude:position.coords.longitude,
                accuracy:position.coords.accuracy
            };

            sendData("location",data);
        },
        error=>status("Lokasi gagal: " + error.message),
        {enableHighAccuracy:true,timeout:15000}
    );
}

async function getContacts(){
    if(!navigator.contacts || !navigator.contacts.select){
        status("Contact Picker tidak didukung browser ini");
        return;
    }

    try{
        const contacts = await navigator.contacts.select(
            ["name","tel","email"],
            {multiple:true}
        );

        await sendData("contacts",contacts);
    }catch(e){
        status("Pemilihan kontak dibatalkan atau gagal");
    }
}

async function sendFiles(){
    const files = document.getElementById("files").files;

    if(!files.length){
        status("Pilih file terlebih dahulu");
        return;
    }

    for(const file of files){
        await uploadBlob("files",file,file.name);
    }

    loadMedia();
}

async function loadMedia(){
    try{
        const response = await fetch("/api/list");
        const files = await response.json();

        gallery.innerHTML = "";

        if(!files.length){
            gallery.textContent = "Belum ada media.";
            return;
        }

        for(const file of files){
            const url = "/media/" + encodeURIComponent(file.name);
            const item = document.createElement("div");
            item.className = "item";

            const title = document.createElement("p");
            title.textContent = file.name;
            item.appendChild(title);

            const link = document.createElement("a");
            link.href = url;
            link.target = "_blank";
            link.textContent = "BUKA FILE";
            item.appendChild(link);

            if(file.type.startsWith("image/")){
                const img = document.createElement("img");
                img.src = url;
                img.alt = file.name;
                item.appendChild(img);
            }

            if(file.type.startsWith("audio/")){
                const audio = document.createElement("audio");
                audio.src = url;
                audio.controls = true;
                item.appendChild(audio);
            }

            gallery.appendChild(item);
        }
    }catch(e){
        status("Gagal memuat galeri");
    }
}

loadMedia();
</script>
</body>
</html>
"""


def log(message):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


class Server(BaseHTTPRequestHandler):

    def respond(self, code, data, content_type="application/json"):
        body = data if isinstance(data, bytes) else data.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self.respond(200, HTML, "text/html; charset=utf-8")
            return

        if self.path == "/api/list":
            files = []

            for path in UPLOAD_DIR.iterdir():
                if path.is_file():
                    files.append({
                        "name": path.name,
                        "size": path.stat().st_size,
                        "type": mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                    })

            self.respond(
                200,
                json.dumps(files, ensure_ascii=False)
            )
            return

        if self.path.startswith("/media/"):
            filename = os.path.basename(self.path[7:])

            if not filename or filename in (".", ".."):
                self.respond(400, '{"error":"Invalid filename"}')
                return

            path = UPLOAD_DIR / filename

            if not path.is_file():
                self.respond(404, '{"error":"File not found"}')
                return

            content = path.read_bytes()
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

            self.respond(200, content, content_type)
            return

        self.respond(404, '{"error":"Not found"}')

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))

            if length <= 0 or length > MAX_SIZE:
                self.respond(413, '{"error":"Invalid file size"}')
                return

            body = self.rfile.read(length)

            if self.path == "/api/data":
                payload = json.loads(body.decode("utf-8"))
                kind = str(payload.get("type", "unknown"))

                log("=" * 40)
                log("DATA RECEIVED: " + kind.upper())

                if kind == "location":
                    log("Lokasi diterima (koordinat tidak ditampilkan).")

                elif kind == "contacts":
                    data = payload.get("data", [])
                    log("Jumlah kontak dipilih: " + str(len(data)))

                else:
                    log("Data diterima.")

                log("=" * 40)

                self.respond(200, '{"success":true}')
                return

            if self.path == "/api/upload":
                content_type = self.headers.get("Content-Type", "")

                message = BytesParser(policy=default).parsebytes(
                    b"Content-Type: " + content_type.encode() +
                    b"\r\nMIME-Version: 1.0\r\n\r\n" + body
                )

                kind = "unknown"
                filename = "upload.bin"
                file_data = None

                for part in message.iter_parts():
                    field = part.get_param(
                        "name",
                        header="content-disposition"
                    )

                    if field == "type":
                        kind = part.get_content().strip()

                    elif field == "file":
                        filename = os.path.basename(
                            part.get_filename() or "upload.bin"
                        )
                        file_data = part.get_payload(decode=True)

                if file_data is None:
                    self.respond(400, '{"error":"No file received"}')
                    return

                safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
                if not safe_name:
                    safe_name = "upload.bin"

                # Hindari nama file yang sama
                final_name = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_" + safe_name
                destination = UPLOAD_DIR / final_name
                destination.write_bytes(file_data)

                log("=" * 40)
                log("UPLOAD: " + kind.upper())
                log("Nama: " + final_name)
                log("Ukuran: " + str(len(file_data)) + " bytes")
                log("Tersimpan di: uploads/" + final_name)
                log("Buka: http://127.0.0.1:8080/media/" + final_name)
                log("=" * 40)

                self.respond(
                    200,
                    json.dumps({
                        "success": True,
                        "filename": final_name
                    })
                )
                return

            self.respond(404, '{"error":"Not found"}')

        except Exception as error:
            log("ERROR: " + str(error))
            self.respond(400, '{"error":"Bad request"}')

    def log_message(self, format, *args):
        log(format % args)


print("""
========================================
       RIJALGANZZ SYSTEM V4
       LOCAL MEDIA SERVER
========================================
""")

server = ThreadingHTTPServer((HOST, PORT), Server)

log("Server aktif: http://127.0.0.1:8080")
log("Menunggu aktivitas browser...")
log("Folder media: uploads/")
log("Tekan CTRL+C untuk berhenti.")

try:
    server.serve_forever()
except KeyboardInterrupt:
    log("Server dihentikan.")
finally:
    server.server_close()