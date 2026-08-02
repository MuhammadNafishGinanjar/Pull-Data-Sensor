# PZEM-014/016 to MongoDB

Program ini membaca 10 Input Register PZEM melalui Modbus RTU Function 04,
mengubah nilai mentah menjadi satuan teknik, kemudian menyimpan satu dokumen
per pembacaan ke MongoDB.

## Persiapan

1. Tutup Modbus Poll agar COM port tidak sedang dipakai program lain.
2. Ubah `port`, `slave_id`, dan identitas mesin di `config.json`.
3. Buat virtual environment dan pasang dependensi:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

4. Isi URI MongoDB pada sesi PowerShell yang sama:

```powershell
$env:MONGO_URI="mongodb+srv://USERNAME:PASSWORD@HOST/?retryWrites=true&w=majority"
```

5. Jalankan collector:

```powershell
python main.py
```

Data disimpan ke database `cmms`, collection `power_sensor_reading`. Nama
database dan collection dapat diubah melalui `config.json`.

## Pengujian tanpa sensor

Pengujian parser memakai contoh respons yang tercantum pada datasheet:

```powershell
python -m unittest -v test_parser.py
```
