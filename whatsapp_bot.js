const { makeWASocket, DisconnectReason } = require("@whiskeysockets/baileys");
const { default: axios } = require("axios");
const { useMultiFileAuthState } = require('@whiskeysockets/baileys');
const path = require('path');
const qrcode = require('qrcode-terminal'); // You'll need to install this: npm install qrcode-terminal
const express = require('express');
const QRCode = require('qrcode');
const fs = require('fs');

const app = express();
let qrCodeDataURL = null;
let connectionStatus = 'connecting';

async function startBot() {
    const authPath = path.resolve(__dirname, 'auth');
    const { state, saveCreds } = await useMultiFileAuthState(authPath);

    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: false,
        browser: ['WhatsApp', 'Chrome', '1.0'],
    });

    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("connection.update", (update) => {
        const { connection, lastDisconnect, qr } = update;
        if (connection === "connecting") {
            connectionStatus = 'connecting';
        }
        if (qr) {
            console.log("QR received for scanning");
            QRCode.toDataURL(qr, (err, url) => {
                if (!err) qrCodeDataURL = url;
            });
            connectionStatus = 'qr';
        }
        if (connection === "close") {
            const shouldReconnect = (lastDisconnect.error?.output?.statusCode !== DisconnectReason.loggedOut);
            console.log("Conexión cerrada debido a ", lastDisconnect.error, ", reconectando ", shouldReconnect);
            if (shouldReconnect) {
                connectionStatus = 'connecting';
                startBot();
            } else {
                connectionStatus = 'error';
            }
        } else if (connection === "open") {
            connectionStatus = 'connected';
            console.log("¡Conexión abierta!");
        }
    });

    sock.ev.on("messages.upsert", async ({ messages, type }) => {
        if (type === "notify") {
            const msg = messages[0];
            if (!msg.message || msg.key.fromMe || msg.key.remoteJid === 'status@broadcast') return;

            const senderJid = msg.key.remoteJid;
            const userText = msg.message.conversation || msg.message.extendedTextMessage?.text || msg.message.imageMessage?.caption || msg.message.videoMessage?.caption;

            if (!userText) return;

            console.log(`Mensaje recibido de ${senderJid}: ${userText}`);

            try {
                const response = await axios.post("http://127.0.0.1:5000/ask", {
                    question: userText,
                    sender: senderJid
                });
                await sock.sendMessage(senderJid, { text: response.data.answer });
            } catch (error) {
                console.error("Error al comunicarse con el backend:", error.message);
                if (error.response) {
                    console.error("Datos de respuesta del backend:", error.response.data);
                    console.error("Estado de respuesta del backend:", error.response.status);
                }
                await sock.sendMessage(senderJid, { text: "Disculpa, estoy teniendo problemas para procesar tu solicitud en este momento. Por favor, inténtalo más tarde o contacta a un administrador." });
            }
        }
    });
}

app.get('/', (req, res) => {
    let content = '';
    if (connectionStatus === 'connecting') {
        content = '<div class="status"><p>Connecting to WhatsApp...</p></div>';
    } else if (connectionStatus === 'qr' && qrCodeDataURL) {
        content = '<div class="status"><p>To link your device:</p><div class="qr-code"><img src="' + qrCodeDataURL + '" alt="QR Code" /></div><div class="instructions">1. Open WhatsApp on your phone<br>2. Tap Menu or Settings and select Linked Devices<br>3. Tap on Link a Device<br>4. Point your phone at this screen to scan the code<br><br>Note: The QR code expires in about 60 seconds. If scanning fails, reset and try again.</div></div>';
    } else if (connectionStatus === 'connected') {
        content = '<div class="status"><p>Device linked successfully! The bot is now connected.</p></div>';
    } else if (connectionStatus === 'error') {
        content = '<div class="status"><p>Connection failed. Please reset and try again.</p><a href="/reset" class="reset-link">Reset Auth and Link Device</a></div>';
    }

    let html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Bot Device Linking</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f0f2f5;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            color: #333;
        }
        .container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 40px;
            text-align: center;
            max-width: 400px;
            width: 100%;
        }
        h1 {
            color: #25D366;
            margin-bottom: 20px;
        }
        .status {
            margin: 20px 0;
        }
        .qr-code {
            margin: 20px 0;
        }
        .qr-code img {
            max-width: 256px;
            width: 100%;
            height: auto;
        }
        .instructions {
            font-size: 14px;
            color: #666;
            margin: 20px 0;
            line-height: 1.5;
        }
        .reset-link {
            display: inline-block;
            background: #25D366;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 20px;
        }
        .reset-link:hover {
            background: #128C7E;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>WhatsApp Bot</h1>
        ${content}
    </div>
</body>
</html>`;
    res.send(html);
});

app.get('/reset', (req, res) => {
  const authPath = path.resolve(__dirname, 'auth');
  if (fs.existsSync(authPath)) {
    fs.rmSync(authPath, { recursive: true, force: true });
  }
  connectionStatus = 'connecting';
  qrCodeDataURL = null;
  res.send('<h1>Auth reset successfully!</h1><p>Restarting bot...</p>');
  setTimeout(() => process.exit(0), 1000);
});

app.listen(3000, '0.0.0.0', () => console.log('Web app running on http://0.0.0.0:3000'));

startBot();