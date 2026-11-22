"""JK-BMS BLE (JK02) protocol constants and command frames. No I/O here."""

MIN_FRAME_SIZE = 300
MAX_FRAME_SIZE = 320
SERVICE_UUID = "0000FFE0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000FFE1-0000-1000-8000-00805f9b34fb"
CMD_HEADER = bytes([0xAA, 0x55, 0x90, 0xEB])
CMD_TYPE_DEVICE_INFO = 0x97 # 0x03: Device Info Frame
CMD_TYPE_CELL_INFO = 0x96 # 0x02: Cell Info Frame
CMD_TYPE_SETTINGS = 0x95 # 0x01: Settings
JK_BMS_OUI = {"c8:47:80"} # Separated by a comma, you can add all the beginnings of the JK-BMS devices

# JK-BMS (JK02 protocol) write registers: register = (offset in the settings frame - 6) / 4 + 1
BMS_SWITCH_REGISTERS = {
    "charge": (0x1D, "charge_switch"),      # settings frame bytes 118-121
    "discharge": (0x1E, "discharge_switch"),  # bytes 122-125
    "balance": (0x1F, "balancer_switch"),     # bytes 126-129
}

FRAME_HEADER = b'\x55\xAA\xEB\x90'

def calculate_crc(data):
    return sum(data) % 256

def create_command(command_type, value: int = 0, length: int = 0):
    """20-byte JK02 command: header, command/register, length, 32-bit LE value, padding, CRC."""
    frame = bytearray(20)
    frame[:4] = CMD_HEADER
    frame[4] = command_type
    frame[5] = length
    frame[6:10] = int(value).to_bytes(4, byteorder='little', signed=False)
    frame[19] = calculate_crc(frame[:19])
    return frame
