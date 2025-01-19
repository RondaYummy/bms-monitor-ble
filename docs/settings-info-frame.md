| Position (Bytes)   | Length | Description                                 | Format   | Coefficient | Unit | Notes                                |
|---------------------|--------|---------------------------------------------|----------|-------------|------|--------------------------------------|
| 0-3                | 4      | Header                                      | HEX      | -           | -    | 0x55 0xAA 0xEB 0x90                 |
| 4                  | 1      | Frame type                                  | HEX      | -           | -    | 0x01                                |
| 5                  | 1      | Frame counter                               | HEX      | -           | -    | 0x4F                                |
| 6-9                | 4      | Smart sleep voltage                         | uint32   | 0.001       | V    | -                                   |
| 10-13              | 4      | Cell UVP (undervoltage protection)          | uint32   | 0.001       | V    | -                                   |
| 14-17              | 4      | Cell UVPR (undervoltage protection recovery)| uint32   | 0.001       | V    | -                                   |
| 18-21              | 4      | Cell OVP (overvoltage protection)           | uint32   | 0.001       | V    | -                                   |
| 22-25              | 4      | Cell OVPR (overvoltage protection recovery) | uint32   | 0.001       | V    | -                                   |
| 26-29              | 4      | Balance trigger voltage                     | uint32   | 0.001       | V    | -                                   |
| 30-33              | 4      | SOC 100% voltage                            | uint32   | 0.001       | V    | -                                   |
| 34-37              | 4      | SOC 0% voltage                              | uint32   | 0.001       | V    | -                                   |
| 38-41              | 4      | Cell request charge voltage (RCV)           | uint32   | 0.001       | V    | -                                   |
| 42-45              | 4      | Cell request float voltage (RFV)            | uint32   | 0.001       | V    | -                                   |
| 46-49              | 4      | Power off voltage                           | uint32   | 0.001       | V    | -                                   |
| 50-53              | 4      | Max charge current                          | uint32   | 0.001       | A    | -                                   |
| 54-57              | 4      | Charge OCP delay                            | uint32   | 1.0         | s    | -                                   |
| 58-61              | 4      | Charge OCP recovery time                    | uint32   | 1.0         | s    | -                                   |
| 62-65              | 4      | Max discharge current                       | uint32   | 0.001       | A    | -                                   |
| 66-69              | 4      | Discharge OCP delay                         | uint32   | 1.0         | s    | -                                   |
| 70-73              | 4      | Discharge OCP recovery time                 | uint32   | 1.0         | s    | -                                   |
| 74-77              | 4      | Short circuit protection recovery time      | uint32   | 1.0         | s    | -                                   |
| 78-81              | 4      | Max balance current                         | uint32   | 0.001       | A    | -                                   |
| 82-85              | 4      | Charge OTP                                  | uint32   | 0.1         | °C   | -                                   |
| 86-89              | 4      | Charge OTP recovery                         | uint32   | 0.1         | °C   | -                                   |
| 90-93              | 4      | Discharge OTP                               | uint32   | 0.1         | °C   | -                                   |
| 94-97              | 4      | Discharge OTP recovery                      | uint32   | 0.1         | °C   | -                                   |
| 98-101             | 4      | Charge UTP                                  | int32    | 0.1         | °C   | -                                   |
| 102-105            | 4      | Charge UTP recovery                         | int32    | 0.1         | °C   | -                                   |
| 106-109            | 4      | MOS OTP                                     | int32    | 0.1         | °C   | -                                   |
| 110-113            | 4      | MOS OTP recovery                            | int32    | 0.1         | °C   | -                                   |
| 114-117            | 4      | Cell count                                  | uint8    | 1.0         | -    | Only first byte used                |
| 118-121            | 4      | Charge switch                               | bool     | -           | -    | Only first byte used                |
| 122-125            | 4      | Discharge switch                            | bool     | -           | -    | Only first byte used                |
| 126-129            | 4      | Balancer switch                             | bool     | -           | -    | Only first byte used                |
| 130-133            | 4      | Nominal battery capacity                    | uint32   | 0.001       | Ah   | -                                   |
| 134-137            | 4      | Short circuit protection delay              | uint32   | 1.0         | μs   | -                                   |
| 138-141            | 4      | Start balance voltage                       | uint32   | 0.001       | V    | -                                   |
| 142-269            | 128    | Connection wire resistance (1-32)           | uint32   | 0.001       | Ω    | 32 x 4-byte values                  |
| 270                | 1      | Device address                              | uint8    | -           | -    | -                                   |
| 274                | 1      | Precharge time                              | uint8    | -           | s    | -                                   |
| 282-283            | 2      | Controls bitmask                            | uint16   | -           | -    | See bitmask notes                   |
| 286                | 1      | Smart sleep                                 | uint8    | -           | h    | -                                   |
| 287                | 1      | Data field enable control 0                 | uint8    | -           | -    | -                                   |
| 299                | 1      | CRC                                         | uint8    | -           | -    | 0x40                                |


Bitmask notes for bytes 282-283:

bit0: Heating enabled (1)
bit1: Disable temperature sensors (2)
bit2: GPS Heartbeat (4)
bit3: Port switch (1: RS485, 0: CAN) (8)
bit4: Display always on (16)
bit5: Special charger (32)
bit6: Smart sleep (64)
bit7: Disable PCL module (128)
bit8: Timed stored data (256)
bit9: Charging float mode (512)
bit10-15: Reserved
