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


def calculate_required_humidity(target_leaf_vpd, air_temp, leaf_temp):
    """
    Calculate the required humidity to achieve the target Leaf VPD.

    Parameters:
    - target_leaf_vpd (float): Desired Leaf VPD in kPa.
    - air_temp (float): Air temperature in °C.
    - leaf_temp (float): Leaf temperature in °C.

    Returns:
    - float: Required humidity percentage (%).
    """

    # Saturation Vapor Pressure (SVP) Formula:
    # SVP = 610.78 * e^((T / (T + 237.3)) * 17.2694)  [Result in Pascals, divide by 1000 to get kPa]
    
    asvp = (610.78 * math.exp((air_temp / (air_temp + 237.3)) * 17.2694)) / 1000  # Air SVP in kPa
    lsvp = (610.78 * math.exp((leaf_temp / (leaf_temp + 237.3)) * 17.2694)) / 1000  # Leaf SVP in kPa

    # Rearranging the Leaf VPD formula to solve for humidity:
    # Leaf VPD = LSVP - (ASVP * Humidity / 100)
    # => Humidity = (LSVP - Leaf VPD) / ASVP * 100
    if asvp == 0:
        print("⚠️ Warning: ASVP is zero, cannot compute required humidity.")
        return 50.0  # Default humidity value

    required_humidity = ((lsvp - target_leaf_vpd) / asvp) * 100

    # Ensure humidity is within a safe range (0-100%)
    required_humidity = max(0, min(100, required_humidity))
    
    return round(required_humidity, 1)

