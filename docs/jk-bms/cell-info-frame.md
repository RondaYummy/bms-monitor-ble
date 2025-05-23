## JK-BMS Cell Info Frame Specification (JK02-32S)

| **Position (Bytes)** | **Length** | **Description** | **Format** | **Coefficient** | **Unit** | Notes |
|----------------------|------------|-----------------|------------|-----------------|----------|-------|
| 0-3              | 4      | Header                           | Raw            | -           | -    | Fixed value: 0x55 0xAA 0xEB 0x90       |
| 4                | 1      | Record type                      | Raw            | -           | -    | Fixed value: 0x02                      |
| 5                | 1      | Frame counter                    | Raw            | -           | -    | -                                       |
| 6-69             | 64     | Cell voltages 1-32               | 16-bit         | 0.001       | V    | 2 bytes per cell                        |
| 54-57            | 4      | Enabled cells bitmask            | Raw            | -           | -    | 0xFF 0xFF 0xFF 0xFF = 32 cells         |
| 64-127           | 64     | Cell resistances 1-32            | 16-bit         | 0.001       | Ohm  | 2 bytes per cell                        |
| 112-113          | 2      | Power tube temperature           | 16-bit signed  | 0.1         | °C   | -                                       |
| 114-117          | 4      | Wire resistance warning bitmask  | Raw            | -           | -    | 1 bit per cell/wire                     |
| 118-121          | 4      | Battery voltage                  | 32-bit         | 0.001       | V    | -                                       |
| 122-125          | 4      | Battery power                    | 32-bit         | 0.001       | W    | -                                       |
| 126-129          | 4      | Charge current                   | 32-bit signed  | 0.001       | A    | -                                       |
| 130-131          | 2      | Temperature Sensor 1             | 16-bit signed  | 0.1         | °C   | -                                       |
| 132-133          | 2      | Temperature Sensor 2             | 16-bit signed  | 0.1         | °C   | -                                       |
| 134-135          | 2      | Errors bitmask                   | 16-bit         | -           | -    | System error flags                      |
| 138-139          | 2      | Balance current                  | 16-bit signed  | 0.001       | A    | -                                       |
| 140              | 1      | Balancing action                 | Raw            | -           | -    | 0=Off, 1=Charging, 2=Discharging        |
| 141              | 1      | State of charge                  | 8-bit          | 1           | %    | -                                       |
| 142-145          | 4      | Remaining capacity               | 32-bit         | 0.001       | Ah   | -                                       |
| 146-149          | 4      | Nominal capacity                 | 32-bit         | 0.001       | Ah   | -                                       |
| 150-153          | 4      | Cycle count                      | 32-bit         | 1           | -    | -                                       |
| 154-157          | 4      | Total cycle capacity             | 32-bit         | 0.001       | Ah   | -                                       |
| 158              | 1      | State of Health (SOH)            | 8-bit          | 1           | %    | -                                       |
| 159              | 1      | Precharge status                 | Raw            | -           | -    | 0=Off, 1=On                             |
| 162-165          | 4      | Total runtime                    | 32-bit         | 1           | s    | -                                       |
| 166              | 1      | Charging MOSFET status           | Raw            | -           | -    | 0=Off, 1=On                             |
| 167              | 1      | Discharging MOSFET status        | Raw            | -           | -    | 0=Off, 1=On                             |
| 168              | 1      | Precharging status               | Raw            | -           | -    | 0=Off, 1=On                             |
| 222-223          | 2      | Temperature Sensor 5             | 16-bit signed  | 0.1         | °C   | -                                       |
| 224-225          | 2      | Temperature Sensor 4             | 16-bit signed  | 0.1         | °C   | -                                       |
| 226-227          | 2      | Temperature Sensor 3             | 16-bit signed  | 0.1         | °C   | -                                       |
| 186-187          | 2      | Emergency time countdown         | 16-bit         | 1           | s    | >0 = Emergency active                   |
| 299              | 1      | CRC checksum                     | Raw            | -           | -    | -                                       |
