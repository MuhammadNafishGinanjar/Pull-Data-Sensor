import time

import device_model

"""
    WTVB02-485 example
"""

# region Common register address reference
"""

hex    dec      describe

0x00    0       Save/Restart/Restore
0x04    4       Serial baud rate

0x1A    26      Device address

0x34    52      Vibration acceleration x
0x35    53      Vibration acceleration y
0x36    54      Vibration acceleration z

0x3A    58      Vibration velocity x
0x3B    59      Vibration velocity y
0x3C    60      Vibration velocity z

# 0x3D    61      Vibration angle x
# 0x3E    62      Vibration angle y
# 0x3F    63      Vibration angle z

0x40    64      Temperature

0x41    65      Vibration displacement x
0x42    66      Vibration displacement y
0x43    67      Vibration displacement z

0x44    68      Vibration frequency x
0x45    69      Vibration frequency y
0x46    70      Vibration frequency z

0x63    99      Cutoff frequency
0x64    100     Cutoff frequency
0x65    101     Detection period

"""
# endregion

# Get device model
device = device_model.DeviceModel("测试设备", "COM4", 9600, 0x50)
# Open device
device.openDevice()

try:
    # Start polling
    device.startLoopRead()
    time.sleep(0.5)

    # Data display
    while True:
        # a: acceleration  v: velocity  t: temperature  s: displacement  f: frequency
        print("ax:{:.4f} ay:{:.4f} az:{:.4f} vx:{:.2f} vy:{:.2f} vz:{:.2f} t:{} sx:{} sy:{} sz:{} fx:{:.1f} fy:{:.1f} fz:{:.1f}".format(device.get("52"),device.get("53"),device.get("54"),device.get("58"),device.get("59"),device.get("60"),device.get("64"),device.get("65"),device.get("66"),device.get("67"),device.get("68"),device.get("69"),device.get("70")))
        time.sleep(0.2)
        
except KeyboardInterrupt:
    print("\nMenghentikan pembacaan...")
    device.stopLoopRead()
    device.closeDevice()
    print("Selesai.")

# Read register: read 1 register from 0x3a
# device.readReg(0x3a, 1)
# Get read result
# device.get(str(0x3a))

# Write register: write 50 to 0x65 to set detection period to 50Hz
# device.writeReg(0x65, 50)
