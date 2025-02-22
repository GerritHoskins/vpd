import datetime

# Define different VPD target ranges for plant growth stages
VPD_TARGET = {"min": None, "max": None}
VPD_MODES = {
    "propagation": (0.4, 0.8),
    "vegetative": (0.8, 1.2),
    "flowering": (1.2, 1.6),
}

# Day and Night VPD ranges
VPD_NIGHT_TARGET = 1.2
VPD_NIGHT_RANGE = 0.2
VPD_NIGHT_MIN = VPD_NIGHT_TARGET - VPD_NIGHT_RANGE
VPD_NIGHT_MAX = VPD_NIGHT_TARGET + VPD_NIGHT_RANGE

DAY_START = 16  # 4 PM
NIGHT_START = 10  # 10 AM

action_map = {
    0: "exhaust_on", 1: "exhaust_off",
    2: "humidifier_on", 3: "humidifier_off",
    4: "dehumidifier_on", 5: "dehumidifier_off"
}

def is_daytime():
    """Check if it's currently daytime based on the schedule."""
    current_hour = datetime.datetime.now().hour
    return DAY_START <= current_hour or current_hour < NIGHT_START

def get_target_vpd():
    """Prompt user to select plant growth stage and return the correct VPD target."""
    while True:
        print("🌱 Select Plant Growth Stage:")
        print("1) Propagation (0.4 - 0.8 kPa)")
        print("2) Vegetative (0.8 - 1.2 kPa)")
        print("3) Flowering (1.2 - 1.6 kPa)")

        choice = input("Enter 1, 2, or 3: ").strip()
        if choice in ["1", "2", "3"]:
            stages = ["propagation", "vegetative", "flowering"]
            selected_stage = stages[int(choice) - 1]
            min_vpd, max_vpd = VPD_MODES[selected_stage]
            print(f"✅ {selected_stage.capitalize()} mode selected. VPD range: {min_vpd} - {max_vpd} kPa.")
            return min_vpd, max_vpd
        else:
            print("❌ Invalid choice! Please enter 1, 2, or 3.")
