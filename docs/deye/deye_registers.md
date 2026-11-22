# 📘 Deye Inverter Modbus Register Map

Документація для зчитування основних параметрів інвертора Deye через Modbus TCP за допомогою бібліотеки `pysolarmanv5`.

## 🔧 Параметри підключення

| Параметр     | Значення         |
|--------------|------------------|
| Порт         | `8899`           |
| Slave ID     | `1` (або `0x01`) |
| Протокол     | Modbus TCP       |
| Бібліотека   | `pysolarmanv5`   |

---

## 📊 Основні Holding Registers

| Адреса | Назва                   | Опис                                         | Тип       | Одиниці           | Примітки                               |
|--------|-------------------------|----------------------------------------------|-----------|--------------------|----------------------------------------|
| `172`  | Grid Power              | Потужність з/до мережі                       | `int16`   | Ват (W)            | Від'ємне = імпорт, додатнє = експорт   |
| `150`  | Grid Voltage L1         | Напруга мережі (фаза L1)                     | `uint16`  | В × 0.1            | ~0 В, коли мережі немає                |
| `173`  | Inverter L1 Power       | Потужність інвертора (фаза L1)               | `int16`   | Ват (W)            | ⚠️ це НЕ напруга мережі                |
| `79`   | Grid Frequency          | Частота мережі                               | `uint16`  | Гц × 0.01          | (174 — потужність інвертора L2)         |
| `178`  | Load Power              | Споживання будинком                          | `int16`   | Ват (W)            |                                        |
| `183`  | Battery Voltage         | Напруга батареї                              | `uint16`  | В × 0.01           |                                        |
| `184`  | Battery SOC             | Рівень заряду батареї                        | `uint16`  | %                  |                                        |
| `186`  | PV1 Power               | Потужність з PV1                             | `uint16`  | Ват (W)            |                                        |
| `187`  | PV2 Power               | Потужність з PV2                             | `uint16`  | Ват (W)            |                                        |
| `190`  | Battery Power           | Заряд/розряд батареї                         | `int16`   | Ват (W)            | Від'ємне = заряд, додатнє = розряд     |
| `191`  | Battery Current         | Струм батареї                                | `uint16`  | А × 0.01           |                                        |
| `258`  | Load Voltage            | Напруга навантаження                         | `uint16`  | В × 0.1            |                                        |
| `259`  | Load Frequency          | Частота навантаження                         | `uint16`  | Гц × 0.01          |                                        |
| `279`  | PV1 Voltage             | Напруга PV1                                  | `uint16`  | В × 0.1            |                                        |
| `280`  | PV2 Voltage             | Напруга PV2                                  | `uint16`  | В × 0.1            |                                        |
| `281`  | PV1 Current             | Струм PV1                                    | `uint16`  | А × 0.01           |                                        |
| `282`  | PV2 Current             | Струм PV2                                    | `uint16`  | А × 0.01           |                                        |

---

## 🔁 Типові обчислення (Python)

```python
grid_power = to_signed(modbus.read_holding_registers(172, 1)[0])
pv1_power = modbus.read_holding_registers(186, 1)[0]
pv2_power = modbus.read_holding_registers(187, 1)[0]
total_pv = pv1_power + pv2_power

load_power = to_signed(modbus.read_holding_registers(178, 1)[0])
battery_power = to_signed(modbus.read_holding_registers(190, 1)[0])
battery_voltage = modbus.read_holding_registers(183, 1)[0] * 0.01
battery_soc = modbus.read_holding_registers(184, 1)[0]

net_balance = total_pv + grid_power - load_power - battery_power
