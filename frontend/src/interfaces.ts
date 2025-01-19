export interface Device {
  average_voltage?: number;
  remaining_capacity?: number;
  [key: string]: any; // Для інших властивостей, підніше треба забрати і додати решта всіх
}
