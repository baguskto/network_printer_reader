# 🖨️ Network Printer Model Detector

Aplikasi Flask sederhana untuk mendeteksi model printer network menggunakan SNMP protocol.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Atau install manual:
```bash
pip install flask pysnmp
```

### 2. Jalankan Server

```bash
python printer_model_api.py
```

### 3. Buka Browser

Server akan berjalan di: **http://localhost:8000**

## 📖 Cara Penggunaan

### 🌐 Web Interface
Buka `http://localhost:8000` untuk interface web dengan form test.

### 🔧 API Endpoint

**GET** `/get-printer?ip=IP_ADDRESS`

#### ✅ Contoh Request:
```
http://localhost:8000/get-printer?ip=192.168.1.100
```

#### ✅ Response Sukses:
```json
{
  "success": true,
  "ip": "192.168.1.100",
  "model": "EPSON TM-T82X Receipt",
  "detected_at": "SNMP Query Success"
}
```

#### ❌ Response Gagal:
```json
{
  "error": "Cannot reach printer at this IP",
  "ip": "192.168.1.100",
  "hint": "Make sure printer is powered on and in the same network"
}
```

## 🎯 Fitur

- ✅ **Multi-OID Support**: Mencoba beberapa OID untuk kompatibilitas maksimal
- ✅ **IP Validation**: Validasi format IP address
- ✅ **Connectivity Test**: Test koneksi ke port SNMP (161) sebelum query
- ✅ **Clean Output**: Pembersihan otomatis response untuk format yang rapi
- ✅ **Web Interface**: Interface web dengan form untuk testing
- ✅ **Error Handling**: Pesan error yang informatif
- ✅ **Health Check**: Endpoint `/health` untuk monitoring

## 🔧 OID yang Didukung

| OID | Deskripsi |
|-----|-----------|
| `1.3.6.1.2.1.25.3.2.1.3.1` | hrDeviceDescr (Standard) |
| `1.3.6.1.2.1.1.1.0` | sysDescr (System Description) |
| `1.3.6.1.4.1.1248.1.2.2.1.1.1.1` | Epson Specific OID |
| `1.3.6.1.2.1.25.3.2.1.3.2` | Alternative hrDeviceDescr |

## 📋 Persyaratan

- Python 3.6+
- Printer harus dalam jaringan yang sama
- Printer harus mendukung SNMP v1/v2c
- Community string: `public` (default)

## 🛠️ Troubleshooting

### ❌ "Cannot reach printer at this IP"
- Pastikan printer menyala dan terkoneksi ke jaringan
- Cek apakah IP address benar
- Pastikan tidak ada firewall yang memblokir port 161

### ❌ "Could not detect printer model" 
- Printer mungkin tidak mendukung SNMP
- Community string mungkin bukan `public`
- Coba restart printer dan coba lagi

### ❌ "Invalid IP address format"
- Pastikan format IP benar (contoh: 192.168.1.100)

## 🎨 Contoh Brand yang Didukung

- ✅ EPSON (TM-T82X, TM-U220, dll)
- ✅ Canon
- ✅ HP
- ✅ Brother
- ✅ Zebra
- ✅ Dan printer lain yang support SNMP

## 📝 API Endpoints

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/` | GET | Home page dengan interface web |
| `/get-printer?ip=IP` | GET | Deteksi model printer |
| `/health` | GET | Health check |

---

**Happy Printing! 🖨️✨** 