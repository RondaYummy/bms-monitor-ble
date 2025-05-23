## JK02_32S Device Info Frame Field Table

| **Position (Bytes)** | **Length** | **Description**               | **Format**    | **Coefficient** | **Unit**  | **Notes**                             |
|-----------------------|------------|-------------------------------|---------------|-----------------|-----------|---------------------------------------|
| 0-3                  | 4          | Frame header                 | hex           | -               | -         | Fixed value: 0x55 0xAA 0xEB 0x90     |
| 4                    | 1          | Frame type                   | uint8         | -               | -         | Fixed value: 0x03                    |
| 5                    | 1          | Frame counter                | uint8         | -               | -         | Increments with each frame            |
| 6-21                 | 16         | Vendor ID                    | string        | -               | -         | Null-terminated string                |
| 22-29                | 8          | Hardware version             | string        | -               | -         | Null-terminated string                |
| 30-37                | 8          | Software version             | string        | -               | -         | Null-terminated string                |
| 38-41                | 4          | Device uptime                | uint32        | 1               | seconds   | Little-endian                         |
| 42-45                | 4          | Power on count               | uint32        | 1               | count     | Little-endian                         |
| 46-61                | 16         | Device name                  | string        | -               | -         | Null-terminated string                |
| 62-77                | 16         | Device passcode              | string        | -               | -         | Null-terminated string                |
| 78-85                | 8          | Manufacturing date           | string        | -               | -         | Null-terminated string                |
| 86-96                | 11         | Serial number                | string        | -               | -         | Null-terminated string                |
| 97-101               | 5          | Passcode                     | string        | -               | -         | Null-terminated string                |
| 102-117              | 16         | User data                    | string        | -               | -         | Null-terminated string                |
| 118-133              | 16         | Setup passcode               | string        | -               | -         | Null-terminated string                |
| 184                  | 1          | UART1M Protocol number       | uint8         | -               | -         | Protocol version                      |
| 185                  | 1          | CAN Protocol number          | uint8         | -               | -         | Protocol version                      |
| 218                  | 1          | UART2M Protocol number       | uint8         | -               | -         | Protocol version                      |
| 219                  | 1          | UART2M Protocol enable       | uint8         | -               | -         | Enable flag                           |
| 234                  | 1          | LCD buzzer trigger           | uint8         | -               | -         | Trigger setting                       |
| 235                  | 1          | DRY1 Trigger                 | uint8         | -               | -         | Trigger setting                       |
| 236                  | 1          | DRY2 Trigger                 | uint8         | -               | -         | Trigger setting                       |
| 237                  | 1          | UART protocol library version| uint8         | -               | -         | Protocol version                      |
| 238-241              | 4          | LCD Buzzer Trigger Value     | uint32        | -               | -         | Little-endian                         |
| 242-245              | 4          | LCD Buzzer Release Value     | uint32        | -               | -         | Little-endian                         |
| 246-249              | 4          | DRY1 Trigger Value           | uint32        | -               | -         | Little-endian                         |
| 250-253              | 4          | DRY1 Release Value           | uint32        | -               | -         | Little-endian                         |
| 254-257              | 4          | DRY2 Trigger Value           | uint32        | -               | -         | Little-endian                         |
| 258-261              | 4          | DRY2 Release Value           | uint32        | -               | -         | Little-endian                         |
| 262-265              | 4          | Data Stored Period           | uint32        | -               | -         | Little-endian                         |
| 266                  | 1          | RCV Time                     | uint8         | 0.1             | hours     | Request Charge Voltage Time           |
| 267                  | 1          | RFV Time                     | uint8         | 0.1             | hours     | Request Float Voltage Time            |
| 268                  | 1          | CAN protocol library version | uint8         | -               | -         | Protocol version                      |
| 299                  | 1          | CRC                          | uint8         | -               | -         | Frame checksum                        |
