def check_vpd_alert(vpd):
    """
    Check the VPD range and return an alert message.

    Parameters:
    - vpd (float): Vapor Pressure Deficit in kPa.

    Returns:
    - str: Alert message based on the VPD range.
    """
    if 0.4 <= vpd < 0.8:
        return "🟢 Low Transpiration: Suitable for Propagation / Early Vegetative Growth"
    elif 0.8 <= vpd < 1.2:
        return "✅ Healthy Transpiration: Ideal for Late Veg / Early Flower"
    elif 1.2 <= vpd < 1.6:
        return "🟠 High Transpiration: Suitable for Mid / Late Flower"
    else:
        return "🚨 Danger Zone! VPD is too high or too low, risking Over/Under Transpiration!"

