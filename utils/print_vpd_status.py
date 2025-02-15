import pyfiglet
from rich.console import Console
from rich.text import Text
from rich.style import Style

console = Console()

def print_vpd_status(vpd_air, vpd_leaf):
    """
    Prints Air VPD and Leaf VPD with color-coded, large font for Leaf VPD.

    Colors:
    - Green (✅ Optimal)
    - Orange (⚠️ Suboptimal)
    - Red (🚨 Danger)
    """

    # Define VPD threshold ranges
    VPD_OPTIMAL_LOW = 0.8
    VPD_OPTIMAL_HIGH = 1.2
    VPD_DANGER_LOW = 0.4
    VPD_DANGER_HIGH = 1.6

    def get_vpd_color(vpd):
        """Determines the color based on VPD value."""
        if VPD_OPTIMAL_LOW <= vpd <= VPD_OPTIMAL_HIGH:
            return "green"  # ✅ Optimal
        elif VPD_DANGER_LOW <= vpd < VPD_OPTIMAL_LOW or VPD_OPTIMAL_HIGH < vpd <= VPD_DANGER_HIGH:
            return "yellow"  # ⚠️ Suboptimal
        else:
            return "red"  # 🚨 Danger

    air_color = get_vpd_color(vpd_air)
    leaf_color = get_vpd_color(vpd_leaf)

    # Create large ASCII text for Leaf VPD
    leaf_vpd_large = Text(f"🔵 Leaf VPD: {vpd_leaf:.2f} kPa", style=Style(color=leaf_color, bold=True))

    # Create styled text for Air VPD
    air_vpd_text = Text(f"🔵 Air VPD: {vpd_air:.2f} kPa", style=Style(color=air_color, bold=False))

    # Print formatted output
    console.rule("[bold white]VPD MONITORING")
    console.print(leaf_vpd_large)
    #console.print(f"[bold {leaf_color}]{leaf_vpd_large}[/bold {leaf_color}]")  # Large Leaf VPD in color
    console.rule()
