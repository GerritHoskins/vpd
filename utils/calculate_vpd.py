import math

def calculate_vpd(air_temp, leaf_temp, humidity):
    """
    Calculate both Air VPD and Leaf VPD. Ensures values are never None.
    """
    if air_temp is None or leaf_temp is None or humidity is None:
        print("⚠️ Warning: Sensor data missing, returning default VPD values.")
        return 0.0, 0.0  # Default VPD values instead of None

    # Saturation Vapor Pressure (SVP) Formula
    asvp = (610.78 * math.exp((air_temp / (air_temp + 237.3)) * 17.2694)) / 1000  # kPa
    lsvp = (610.78 * math.exp((leaf_temp / (leaf_temp + 237.3)) * 17.2694)) / 1000  # kPa

    # Air VPD and Leaf VPD calculations
    air_vpd = asvp * (1 - humidity / 100)
    leaf_vpd = lsvp - (asvp * (humidity / 100))

    return round(air_vpd, 2), round(leaf_vpd, 2)


