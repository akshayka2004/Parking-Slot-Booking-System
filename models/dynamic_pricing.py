"""
Dynamic Pricing Module
Adjusts parking prices based on predicted occupancy
"""

from typing import Dict, Tuple


class DynamicPricing:
    """
    Dynamic pricing engine that adjusts rates based on demand.
    Uses occupancy predictions to calculate price multipliers.
    Supports configurable pricing with INR currency
    """
    
    # Default configuration (INR)
    BASE_PRICE = 50.0  # ₹50 per hour
    MIN_MULTIPLIER = 1.0
    MAX_MULTIPLIER = 2.0
    HIGH_DEMAND_THRESHOLD = 0.8  # 80% occupancy
    CURRENCY_SYMBOL = "₹"
    
    def __init__(self, base_price: float = None, 
                 min_multiplier: float = None,
                 max_multiplier: float = None):
        """
        Initialize pricing engine.
        
        Args:
            base_price: Base hourly rate (default: $10)
            min_multiplier: Minimum price multiplier (default: 1.0)
            max_multiplier: Maximum price multiplier (default: 2.0)
        """
        self.base_price = base_price or self.BASE_PRICE
        self.min_multiplier = min_multiplier or self.MIN_MULTIPLIER
        self.max_multiplier = max_multiplier or self.MAX_MULTIPLIER
    
    def calculate_multiplier(self, occupancy_rate: float) -> float:
        """
        Calculate price multiplier based on occupancy rate.
        
        Args:
            occupancy_rate: Current/predicted occupancy (0.0 to 1.0)
        
        Returns:
            Price multiplier (1.0 to 2.0)
        """
        if occupancy_rate <= self.HIGH_DEMAND_THRESHOLD:
            return self.min_multiplier
        
        # Linear interpolation between threshold and 100%
        excess = occupancy_rate - self.HIGH_DEMAND_THRESHOLD
        range_above = 1.0 - self.HIGH_DEMAND_THRESHOLD
        
        # Scale from min to max multiplier
        multiplier_range = self.max_multiplier - self.min_multiplier
        additional = (excess / range_above) * multiplier_range
        
        multiplier = self.min_multiplier + additional
        
        return round(min(self.max_multiplier, multiplier), 2)
    
    def get_price(self, occupancy_rate: float, hours: float = 1.0) -> Dict:
        """
        Get the dynamic price for parking.
        
        Args:
            occupancy_rate: Current/predicted occupancy (0.0 to 1.0)
            hours: Number of hours to park
        
        Returns:
            Dict with pricing details
        """
        multiplier = self.calculate_multiplier(occupancy_rate)
        hourly_rate = self.base_price * multiplier
        total_price = hourly_rate * hours
        
        return {
            'base_price': self.base_price,
            'multiplier': multiplier,
            'hourly_rate': round(hourly_rate, 2),
            'hours': hours,
            'total_price': round(total_price, 2),
            'occupancy_rate': round(occupancy_rate * 100, 1),
            'is_surge_pricing': multiplier > self.min_multiplier,
            'savings_vs_max': round((self.max_multiplier - multiplier) * self.base_price * hours, 2)
        }
    
    def get_price_tier(self, occupancy_rate: float) -> str:
        """
        Get a price tier label based on occupancy.
        
        Args:
            occupancy_rate: Current/predicted occupancy
        
        Returns:
            Tier label: 'Standard', 'Moderate', 'Peak', or 'Premium'
        """
        if occupancy_rate < 0.5:
            return 'Standard'
        elif occupancy_rate < 0.7:
            return 'Moderate'
        elif occupancy_rate < 0.85:
            return 'Peak'
        else:
            return 'Premium'
    
    def estimate_best_price_times(self, hourly_occupancy: Dict[int, float]) -> list:
        """
        Find the best times for lowest prices.
        
        Args:
            hourly_occupancy: Dict mapping hour -> occupancy_rate
        
        Returns:
            List of (hour, price_info) sorted by price
        """
        price_times = []
        
        for hour, occupancy in hourly_occupancy.items():
            price_info = self.get_price(occupancy)
            price_times.append((hour, price_info))
        
        # Sort by hourly rate (lowest first)
        price_times.sort(key=lambda x: x[1]['hourly_rate'])
        
        return price_times
    
    def get_surge_explanation(self, occupancy_rate: float) -> str:
        """
        Get a user-friendly explanation of pricing.
        
        Args:
            occupancy_rate: Current occupancy rate
        
        Returns:
            Human-readable pricing explanation
        """
        price_info = self.get_price(occupancy_rate)
        tier = self.get_price_tier(occupancy_rate)
        
        if not price_info['is_surge_pricing']:
            return f"Standard pricing at ${price_info['hourly_rate']:.2f}/hr. Occupancy is at {price_info['occupancy_rate']:.0f}%."
        else:
            return (
                f"{tier} pricing in effect. High demand ({price_info['occupancy_rate']:.0f}% occupancy) "
                f"has increased rates to ${price_info['hourly_rate']:.2f}/hr "
                f"({price_info['multiplier']}x base rate)."
            )


if __name__ == "__main__":
    # Test the pricing engine
    pricing = DynamicPricing()
    
    print("Dynamic Pricing Test")
    print("=" * 40)
    
    # Test various occupancy rates
    test_rates = [0.3, 0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
    
    for rate in test_rates:
        info = pricing.get_price(rate, hours=2)
        tier = pricing.get_price_tier(rate)
        print(f"Occupancy: {rate:.0%}")
        print(f"  Tier: {tier}")
        print(f"  Hourly Rate: ${info['hourly_rate']:.2f} ({info['multiplier']}x)")
        print(f"  2 Hours Total: ${info['total_price']:.2f}")
        print()
