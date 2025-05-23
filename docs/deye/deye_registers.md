# 📘 Deye Inverter Modbus Register Map

Документація для зчитування основних параметрів інвертора Deye через Modbus TCP за допомогою бібліотеки `pysolarmanv5`.

## 🔧 Параметри підключення

| Параметр     | Значення               |
|--------------|------------------------|
| Порт         | `8899`                 |
| Slave ID     | `1` (або `0x01`)       |
| Протокол     | Modbus TCP             |
| Бібліотека   | `pysolarmanv5`         |

---

## 📊 Основні Holding Registers

| Адреса | Назва              | Опис                                      | Формат      | Одиниці виміру      | Коментар                                |
|--------|--------------------|-------------------------------------------|-------------|----------------------|------------------------------------------|
| `173`  | Grid Power         | Потужність в мережу (експорт або імпорт)  | `int16`     | W                    | Від'ємне = імпорт, додатнє = експорт     |
| `178`  | Load Power         | Споживання будинком                       | `int16`     | W                    | Потужність навантаження                 |
| `183`  | Battery Voltage    | Напруга батареї                           | `uint16`    | V × 0.01             | Потрібно ділити на 100                  |
| `184`  | Battery SOC        | State of Charge (заряд батареї)           | `uint16`    | %                    |                                          |
| `186`  | PV1 Power          | Потужність з PV1                          | `uint16`    | W                    |                                          |
| `187`  | PV2 Power          | Потужність з PV2                          | `uint16`    | W                    |                                          |
| `190`  | Battery Power      | Потужність батареї                        | `int16`     | W                    | Від'ємне = заряд, додатнє = розряд      |

---

## 🔁 Типові обчислення

```python
# Grid direction
grid_power = to_signed(modbus.read_holding_registers(172, 1)[0])

# Total PV generation
pv1 = modbus.read_holding_registers(186, 1)[0]
pv2 = modbus.read_holding_registers(187, 1)[0]
total_pv = pv1 + pv2

# Load power (house consumption)
load_power = to_signed(modbus.read_holding_registers(178, 1)[0])

# Battery
battery_power = to_signed(modbus.read_holding_registers(190, 1)[0])
battery_voltage = modbus.read_holding_registers(183, 1)[0] * 0.01
battery_soc = modbus.read_holding_registers(184, 1)[0]

# Net balance formula
net_balance = total_pv + grid_power - load_power - battery_power
