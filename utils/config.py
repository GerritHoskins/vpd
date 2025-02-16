import os

def get_target_vpd():
    """Retrieve the target Leaf VPD from an environment variable, with a default fallback."""
    try:
        target_vpd = float(os.getenv("TARGET_LEAF_VPD", 1.2))  # Default to 1.2 if not set
        if 0.1 <= target_vpd <= 3.0:  # Ensure it's within a valid range
            return target_vpd
        else:
            print("❌ Invalid TARGET_LEAF_VPD. Using default value of 1.2 kPa.")
            return 1.2
    except ValueError:
        print("❌ Error: TARGET_LEAF_VPD is not a valid number. Using default value of 1.2 kPa.")
        return 1.2
