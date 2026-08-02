# PZEM-014/016 Modbus Driver

`pzem_sensor.py` membaca 10 Input Register PZEM melalui Modbus RTU Function 04
dan mengubah nilai mentah menjadi satuan teknik (`PZEMSensor.read_measurements()`).

Folder ini hanya bertugas mengambil data mentah dari sensor PZEM. Proses
penggabungan dengan pembacaan suhu PLC, penyimpanan ke MongoDB, dan
pengiriman ke API dilakukan terpusat di `main.py` pada root project, yang
meng-import `PZEMSensor` dari folder ini. Konfigurasi port/baudrate/slave ID
PZEM diatur lewat konstanta `PZEM_*` di `pzem_sensor.py`.

## Pengujian parser (tanpa sensor fisik)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r ../requirements.txt
python -m unittest -v test_pzem_sensor.py
```
