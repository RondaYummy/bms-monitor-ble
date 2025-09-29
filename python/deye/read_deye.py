import asyncio
import time
from datetime import datetime
from pysolarmanv5 import PySolarmanV5, V5FrameError
from python.data_store import data_store
import python.db as db

# This is the local IP address of the WiFi stick connected to the Deye (or Solarman) inverter.
# This stick works as a TCP server that listens to port 8899 and transmits data via the Modbus protocol.
# INVERTER_IP = "192.168.31.40"

# This is the serial number of the Wi-Fi stick itself (data logger), not the inverter.
# It is unique for each stick and is usually indicated
# in the local web interface of the Wi-Fi stick (e.g. http://192.168.31.40) or on the sticker of the stick
# LOGGER_SN = 2993578387

# This is the Modbus Slave ID, i.e. the internal identifier of the device in the Modbus network.
# For Deye inverters via WiFi stick, it is always 1 (unless you connect directly via RS485 with a different ID).
# SLAVE_ID = 1

def safe_read_scaled(modbus, register: int, scale: float, name: str = ""):
    try:
        raw = modbus.read_holding_registers(register, 1)[0]
        if raw in (0, 65535): # frequent “no data” marker
            print(f"⚠️ {name} = {raw} (possibly invalid)")
            return None
        return round(raw * scale, 2)
    except Exception as e:
        print(f"❌ Failed to read {name} (reg {register}): {e}")
        return None
        
def to_signed(val):
    return val - 0x10000 if val >= 0x8000 else val

def to_signed_32bit(hi: int, lo: int) -> int:
    value = (hi << 16) + lo
    return value if value < 0x80000000 else value - 0x100000000

def test_registers(modbus):
    topics = {
        "186": "dc/pv1/power",
        "187": "dc/pv2/power",
        "109": "dc/pv1/voltage",
        "111": "dc/pv2/voltage",
        "110": "dc/pv1/current",
        "112": "dc/pv2/current",
        "108": "day_energy",
        "96": "total_energy",
        "166": "micro_inverter_power",
        "70": "battery/daily_charge",
        "71": "battery/daily_discharge",
        "72": "battery/total_charge",
        "74": "battery/total_discharge",
        "189": "battery/status",
        "190": "battery/power",
        "183": "battery/voltage",
        "184": "battery/soc",
        "191": "battery/current",
        "182": "battery/temperature",
        "169": "ac/total_grid_power",
        "175": "ac/total_power",
        "150": "ac/l1/voltage",
        "151": "ac/l2/voltage",
        "164": "ac/l1/current",
        "165": "ac/l2/current",
        "173": "ac/l1/power",
        "174": "ac/l2/power",
        "76": "ac/daily_energy_bought",
        "77": "ac/daily_energy_sold",
        "78": "ac/total_energy_bought",
        "81": "ac/total_energy_sold",
        "192": "ac/frequency",
        "90": "radiator_temp",
        "91": "ac/temperature",
        "170": "ac/l1/ct/external",
        "167": "ac/l1/ct/internal",
        "171": "ac/l2/ct/external",
        "168": "ac/l2/ct/internal",
        "248": "timeofuse/enabled",
        "250": "timeofuse/time/1",
        "251": "timeofuse/time/2",
        "252": "timeofuse/time/3",
        "253": "timeofuse/time/4",
        "254": "timeofuse/time/5",
        "255": "timeofuse/time/6",
        "256": "timeofuse/power/1",
        "257": "timeofuse/power/2",
        "258": "timeofuse/power/3",
        "259": "timeofuse/power/4",
        "260": "timeofuse/power/5",
        "261": "timeofuse/power/6",
        "262": "timeofuse/voltage/1",
        "263": "timeofuse/voltage/2",
        "264": "timeofuse/voltage/3",
        "265": "timeofuse/voltage/4",
        "266": "timeofuse/voltage/5",
        "267": "timeofuse/voltage/6",
        "268": "timeofuse/soc/1",
        "269": "timeofuse/soc/2",
        "270": "timeofuse/soc/3",
        "271": "timeofuse/soc/4",
        "272": "timeofuse/soc/5",
        "273": "timeofuse/soc/6",
        "274": "timeofuse/enabled/1",
        "275": "timeofuse/enabled/2",
        "276": "timeofuse/enabled/3",
        "277": "timeofuse/enabled/4",
        "278": "timeofuse/enabled/5",
        "279": "timeofuse/enabled/6",
        "312": "bms/1/charging_voltage",
        "313": "bms/1/discharge_voltage",
        "314": "bms/1/charge_current_limit",
        "315": "bms/1/discharge_current_limit",
        "316": "bms/1/soc",
        "317": "bms/1/voltage",
        "318": "bms/1/current",
        "319": "bms/1/temp"
    }
    print("=== 🔍 Start register scan ===")
    for reg, name in topics.items():
        try:
            val = modbus.read_holding_registers(reg, 1)[0]
            # робимо signed для int16
            if val >= 0x8000:
                val -= 0x10000
            print(f"Reg {reg:3d} ({name}): {val}")
        except Exception as e:
            print(f"❌ Failed to read Reg {reg} ({name}): {e}")
    print("=== ✅ End register scan ===")

async def read_deye_for_device(ip: str, serial_number: int, slave_id: int = 1):
    print(f"📡 Connecting to Deye inverter at {ip}...")
    modbus = PySolarmanV5(ip, serial_number, port=8899, mb_slave_id=slave_id)

    try:
        pv1_power = modbus.read_holding_registers(186, 1)[0]
        pv2_power = modbus.read_holding_registers(187, 1)[0]
        total_pv = pv1_power + pv2_power
        load_power = to_signed(modbus.read_holding_registers(178, 1)[0])


        grid_power = to_signed(modbus.read_holding_registers(172, 1)[0])

        # TEST START
        print(f"TEST START")
        # # Регістр 170: миттєва потужність з/до мережі
        # reg_170 = modbus.read_holding_registers(170, 1)[0]
        # if reg_170 >= 0x8000:  # робимо signed
        #     reg_170 -= 0x10000

        # print("⚡ Grid Power (170):", reg_170, "Вт")
        # if reg_170 > 0:
        #     print("➡️ Імпорт з мережі:", reg_170, "Вт")
        # elif reg_170 < 0:
        #     print("⬅️ Експорт у мережу:", abs(reg_170), "Вт")
        # else:
        #     print("⏸️ Немає обміну з мережею")
        # # Регістр 170: миттєва потужність з/до мережі

        # try:
        #     reg_618 = modbus.read_holding_registers(618, 1)[0]  # Grid External Total Active Power (S16)
        #     reg_622 = modbus.read_holding_registers(622, 1)[0]  # Grid Side A-phase Power (S16)
        #     # Читаємо 32-бітне значення (625 і 626)
        #     regs_625_626 = modbus.read_holding_registers(625, 2)
        #     reg_625_626 = (regs_625_626[1] << 16) | regs_625_626[0]
        #     # Робимо його signed (32-біт)
        #     if reg_625_626 & 0x80000000:
        #         reg_625_626 -= 0x100000000

        #     # Робимо signed для 16-бітних регістрів
        #     if reg_618 >= 0x8000:
        #         reg_618 -= 0x10000
        #     if reg_622 >= 0x8000:
        #         reg_622 -= 0x10000

        #     print("🔌 Grid External Total Active Power (618):", reg_618, "Вт")
        #     print("🔌 Grid Side A-phase Power (622):", reg_622, "Вт")
        #     print("🔌 Grid Side Total Active Power (625+626):", reg_625_626, "Вт")
        # except Exception as e:
        #     print(f"Failed to read 3090: {e}")

        # try:
        #     regs_378_379 = modbus.read_holding_registers(378, 2)
        #     grid_import_wh = (regs_378_379[1] << 16) | regs_378_379[0]

        #     regs_380_381 = modbus.read_holding_registers(380, 2)
        #     grid_export_wh = (regs_380_381[1] << 16) | regs_380_381[0]

        #     print("📥 Grid Import Energy:", grid_import_wh / 1000.0, "kWh")
        #     print("📤 Grid Export Energy:", grid_export_wh / 1000.0, "kWh")
        # except Exception as e:
        #     print(f"❌ Failed to read Grid Energy Counters: {e}")
        # # НОВИЙ ТЕСТОВИЙ БЛОК: Фокусуємося на 16-бітних регістрах Grid Power
        # print(f"--- Modbus Test Registers Start ---")
        # try:
        #     reg_625_raw = modbus.read_holding_registers(625, 1)[0]
        #     grid_power_625 = to_signed(reg_625_raw)
        #     print("🔌 Grid Total Active Power (Reg 625, S16):", grid_power_625, "Вт")
        # except Exception as e:
        #     print(f"❌ Failed to read Reg 625 (16-bit): {e}")

        # try:
        #     reg_622_raw = modbus.read_holding_registers(622, 1)[0]
        #     grid_power_622 = to_signed(reg_622_raw)
        #     print("🔌 Grid Side A-phase Power (Reg 622, S16):", grid_power_622, "Вт")
        # except Exception as e:
        #     print(f"❌ Failed to read Reg 622 (16-bit): {e}")
                    
        # try:
        #     grid_power_172 = to_signed(modbus.read_holding_registers(172, 1)[0])
        #     print("🔌 Grid External Total Power (Reg 172, S16):", grid_power_172, "Вт")
        # except Exception as e:
        #     print(f"❌ Failed to read Reg 172 (16-bit): {e}")

        # print(f"--- Modbus Test Registers End ---")
        # # Оновлюємо змінну grid_power, яку ви використовуєте в data, на найімовірніше коректну
        # # Ми використовуємо 172 як стандартний, але якщо 625 покаже результат, ви можете змінити.
        # # Встановіть grid_power = grid_power_625, якщо цей регістр буде працювати.
        # # Наразі залишаємо 172, як було у вашій початковій логіці перед тестовим блоком.
        # # grid_power = grid_power_625 if 'grid_power_625' in locals() and grid_power_625 is not None else grid_power
        # print("=== DEYE MODBUS TEST BLOCK START ===")
        # # --- 1. Миттєва потужність ---
        # try:
        #     reg_170 = modbus.read_holding_registers(170, 1)[0]
        #     reg_170 = reg_170 - 0x10000 if reg_170 >= 0x8000 else reg_170
        #     print("⚡ Grid Power (170):", reg_170, "Вт")
        #     if reg_170 > 0:
        #         print("➡️ Імпорт з мережі:", reg_170, "Вт")
        #     elif reg_170 < 0:
        #         print("⬅️ Експорт у мережу:", abs(reg_170), "Вт")
        #     else:
        #         print("⏸️ Немає обміну з мережею")
        # except Exception as e:
        #     print("❌ Failed to read Reg 170:", e)

        # # --- 2. Grid Side та External Power ---
        # for reg, name in [(618, "Grid External Total Active Power"),
        #                 (622, "Grid Side A-phase Power"),
        #                 (625, "Grid Side Total Active Power (S16)"),
        #                 (626, "Grid Side Total Active Power High Word"),
        #                 (172, "Grid External Total Power")]:
        #     try:
        #         val = modbus.read_holding_registers(reg, 1)[0]
        #         val = val - 0x10000 if val >= 0x8000 else val
        #         print(f"🔌 {name} (Reg {reg}): {val} Вт")
        #     except Exception as e:
        #         print(f"❌ Failed to read Reg {reg} ({name}): {e}")

        # # --- 3. Лічильники енергії ---
        # for reg_start, label in [(378, "Grid Import Total (Wh)"),
        #                         (380, "Grid Export Total (Wh)"),
        #                         (182, "Grid Import Today (Wh)"),
        #                         (184, "Grid Export Today (Wh)")]:
        #     try:
        #         regs = modbus.read_holding_registers(reg_start, 2)
        #         val = (regs[1] << 16) | regs[0]
        #         print(f"📊 {label} (Reg {reg_start}+1): {val/1000:.3f} kWh")
        #     except Exception as e:
        #         print(f"❌ Failed to read Reg {reg_start} ({label}): {e}")

        # # --- 4. Напруга та струм мережі (для приблизного P=U*I) ---
        # for reg, label, scale in [(150, "Grid Voltage Phase A", 0.1),
        #                         (151, "Grid Voltage Phase B", 0.1),
        #                         (152, "Grid Voltage Phase C", 0.1),
        #                         (154, "Grid Current Phase A", 0.01),
        #                         (155, "Grid Current Phase B", 0.01),
        #                         (156, "Grid Current Phase C", 0.01)]:
        #     try:
        #         val = modbus.read_holding_registers(reg, 1)[0] * scale
        #         print(f"🔌 {label} (Reg {reg}): {val}")
        #     except Exception as e:
        #         print(f"❌ Failed to read Reg {reg} ({label}): {e}")

        # # --- 5. Додатково: Grid Power Phase (для перевірки) ---
        # for reg, label in [(158, "Grid Power Phase A"),
        #                 (159, "Grid Power Phase B"),
        #                 (160, "Grid Power Phase C")]:
        #     try:
        #         val = modbus.read_holding_registers(reg, 1)[0]
        #         val = val - 0x10000 if val >= 0x8000 else val
        #         print(f"🔌 {label} (Reg {reg}): {val} Вт")
        #     except Exception as e:
        #         print(f"❌ Failed to read Reg {reg} ({label}): {e}")

        # grid_power_real = 0
        # for ph, reg_power in [("A", 158), ("B", 159), ("C", 160)]:
        #     try:
        #         p = modbus.read_holding_registers(reg_power, 1)[0]
        #         grid_power_real += to_signed(p)
        #     except:
        #         pass
        # print("⚡ Real Grid Power:", grid_power_real, "Вт")
        # print("=== DEYE MODBUS TEST BLOCK END ===")
        # print("=== FINAL POWER TEST: REG 160/161 START ===")

        # # 1. Спроба: Регістри 160/161 (Total Grid Power, 32-біт)
        # try:
        #     regs_160_161 = modbus.read_holding_registers(160, 2)
        #     # Звичайний Deye порядок: regs[0]=HI, regs[1]=LO
        #     grid_power_32bit = to_signed_32bit(regs_160_161[0], regs_160_161[1])
        #     print(f"⚡ Grid Power (Reg 160/161, S32, H, L): {grid_power_32bit} Вт")
            
        #     if abs(grid_power_32bit) > 100:
        #         print(f"✅ ЗНАЙДЕНО! Використовуйте Reg 160/161 (H, L). Потужність: {grid_power_32bit} Вт")
        #         grid_power = grid_power_32bit # Оновлюємо основну змінну
            
        # except Exception as e:
        #     print(f"❌ Failed to read Reg 160/161 (H, L): {e}")

        # if 'grid_power' in locals() and grid_power == to_signed(modbus.read_holding_registers(172, 1)[0]): # Якщо ще не знайдено
        #     try:
        #         regs_160_161 = modbus.read_holding_registers(160, 2)
        #         grid_power_32bit_lh = to_signed_32bit(regs_160_161[1], regs_160_161[0])
        #         print(f"⚡ Grid Power (Reg 160/161, S32, L, H): {grid_power_32bit_lh} Вт")
                
        #         if abs(grid_power_32bit_lh) > 100:
        #             print(f"✅ ЗНАЙДЕНО! Використовуйте Reg 160/161 (L, H). Потужність: {grid_power_32bit_lh} Вт")
        #             grid_power = grid_power_32bit_lh # Оновлюємо основну змінну
                    
        #     except Exception as e:
        #         print(f"❌ Failed to read Reg 160/161 (L, H): {e}")
                
        # # 3. Підсумок фаз (як ви вже робили, але це менш надійно)
        # grid_power_sum = 0
        # for reg_power in [158, 159, 160]:
        #     try:
        #         p = modbus.read_holding_registers(reg_power, 1)[0]
        #         grid_power_sum += to_signed(p)
        #     except:
        #         pass
        # print(f"⚡ Сума фаз (Reg 158-160, S16): {grid_power_sum} Вт")

        # print("=== FINAL POWER TEST: REG 160/161 END ===")
            # 1. Пробуємо 32-бітне значення з 160/161
        test_registers(modbus)
        regs = modbus.read_holding_registers(160, 2)

        # варіант 1: [0]=HI, [1]=LO
        grid_power_hl = to_signed_32bit(regs[0], regs[1])
        # варіант 2: [0]=LO, [1]=HI
        grid_power_lh = to_signed_32bit(regs[1], regs[0])

        # вибираємо той, де значення виглядає адекватно (в межах ±20кВт)
        for val, label in [(grid_power_hl, "HI,LO"), (grid_power_lh, "LO,HI")]:
            print(f"✅ Grid Power (160/161 {label}): {val} Вт")

        # 2. Якщо обидва варіанти не ок — fallback: сума фаз
        total = 0
        for reg in [158, 159, 160]:
            try:
                raw = modbus.read_holding_registers(reg, 1)[0]
                total += to_signed(raw)
            except:
                pass
        print(f"⚡ Grid Power fallback (158+159+160): {total} Вт")

        # --- Grid Power (миттєва почтужність) ---
        try:
            reg_169_raw = modbus.read_holding_registers(169, 1)[0]
            print(f"⚡ Grid Power (Reg 169 RAW): {reg_169_raw} W")
            grid_power_169 = reg_169_raw - 0x10000 if reg_169_raw >= 0x8000 else reg_169_raw

            print(f"⚡ Grid Power (Reg 169): {grid_power_169} W")
            if grid_power_169 > 0:
                print(f"➡️ Імпорт з мережі: {grid_power_169} W")
            elif grid_power_169 < 0:
                print(f"⬅️ Експорт у мережу: {abs(grid_power_169)} W")
            else:
                print("⏸️ Немає обміну з мережею")

        except Exception as e:
            print(f"❌ Failed to read Grid Power (Reg 169): {e}")


        # --- Grid Energy Counters ---
        for reg, label in [
            (76, "Grid Import Today (Reg 76)"),
            (77, "Grid Export Today (Reg 77)"),
            (78, "Grid Import Total (Reg 78)"),
            (81, "Grid Export Total (Reg 81)")
        ]:
            try:
                val = modbus.read_holding_registers(reg, 1)[0]
                print(f"📊 {label}: {val} kWh")
            except Exception as e:
                print(f"❌ Failed to read {label}: {e}")
        # TEST END


        bat_power = to_signed(modbus.read_holding_registers(190, 1)[0])
        bat_voltage = modbus.read_holding_registers(183, 1)[0] * 0.01
        bat_soc = modbus.read_holding_registers(184, 1)[0]
        net_balance = total_pv + grid_power - load_power - bat_power

        # Additional data
        pv1_voltage = modbus.read_holding_registers(279, 1)[0] * 0.1
        pv2_voltage = modbus.read_holding_registers(280, 1)[0] * 0.1
        # pv1_voltage = safe_read_scaled(modbus, 279, 0.1, "pv1_voltage")
        # pv2_voltage = safe_read_scaled(modbus, 280, 0.1, "pv2_voltage")
        pv1_current = modbus.read_holding_registers(281, 1)[0] * 0.01
        pv2_current = modbus.read_holding_registers(282, 1)[0] * 0.01
        load_voltage = modbus.read_holding_registers(258, 1)[0] * 0.1
        load_frequency = modbus.read_holding_registers(259, 1)[0] * 0.01
        bat_current = modbus.read_holding_registers(191, 1)[0] * 0.01
        grid_voltage = modbus.read_holding_registers(173, 1)[0] * 0.1
        grid_frequency = modbus.read_holding_registers(174, 1)[0] * 0.01

        # total_generated_kwh = ((modbus.read_holding_registers(5001, 2)[0] << 16) + modbus.read_holding_registers(5001, 2)[1]) / 10
        # total_load_kwh = ((modbus.read_holding_registers(5003, 2)[0] << 16) + modbus.read_holding_registers(5003, 2)[1]) / 10
        # total_bat_charge_kwh = ((modbus.read_holding_registers(5007, 2)[0] << 16) + modbus.read_holding_registers(5007, 2)[1]) / 10
        # total_bat_discharge_kwh = ((modbus.read_holding_registers(5009, 2)[0] << 16) + modbus.read_holding_registers(5009, 2)[1]) / 10
        additional = {
            "pv1_voltage": pv1_voltage,
            "pv2_voltage": pv2_voltage,
            "pv1_current": pv1_current,
            "pv2_current": pv2_current,
            "load_voltage": load_voltage,
            "load_frequency": load_frequency,
            "bat_current": bat_current,
            "grid_voltage": grid_voltage,
            "grid_frequency": grid_frequency,
            # "total_generated_kwh": total_generated_kwh,
            # "total_load_kwh": total_load_kwh,
            # "total_bat_charge_kwh": total_bat_charge_kwh,
            # "total_bat_discharge_kwh": total_bat_discharge_kwh
        }
        print("📊 Additional metrics:")
        for key, value in additional.items():
            print(f"  {key:<28} = {value}")


        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "pv1_power": pv1_power,
            "pv2_power": pv2_power,
            "total_pv": total_pv,
            "load_power": load_power,
            "grid_power": grid_power,
            "battery_power": bat_power,
            "battery_voltage": bat_voltage,
            "battery_soc": bat_soc,
            "net_balance": net_balance
        }

        db.update_deye_device_data(ip, data)

    except V5FrameError as err:
        print(f"❌ Modbus error on {ip}: {err}")
    except Exception as err:
        print(f"❌ General error on {ip}: {err}")
    finally:
        modbus.disconnect()

async def run_deye_loop():
    while True:
        try:
            devices = db.get_all_deye_devices()
            tasks = [
                read_deye_for_device(
                    device["ip"],
                    int(device["serial_number"]),
                    int(device.get("slave_id", 1))
                )
                for device in devices if device.get("device_on", 1)
            ]
            await asyncio.gather(*tasks)
        except Exception as e:
            print(f"❌ Error in Deye loop: {e}")
        await asyncio.sleep(3)