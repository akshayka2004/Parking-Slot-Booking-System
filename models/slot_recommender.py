"""
Slot Recommender Module
Ranks available parking slots based on proximity to entry point
"""

import math
from typing import List, Dict, Tuple


class SlotRecommender:
    """
    Recommends parking slots based on distance from entry point.
    Uses Euclidean distance for proximity calculation.
    """
    
    # Entry point coordinates (simulated)
    ENTRY_POINT = (0, 0)
    
    # Pre-defined slot coordinates (row, column layout)
    SLOT_COORDINATES = {
        'slot_1': (1, 1),   'slot_2': (1, 2),   'slot_3': (1, 3),   'slot_4': (1, 4),
        'slot_5': (2, 1),   'slot_6': (2, 2),   'slot_7': (2, 3),   'slot_8': (2, 4),
        'slot_9': (3, 1),   'slot_10': (3, 2),  'slot_11': (3, 3),  'slot_12': (3, 4),
        'slot_13': (4, 1),  'slot_14': (4, 2),  'slot_15': (4, 3),  'slot_16': (4, 4),
        'slot_17': (5, 1),  'slot_18': (5, 2),  'slot_19': (5, 3),  'slot_20': (5, 4),
    }
    
    def __init__(self, entry_point: Tuple[float, float] = None):
        """
        Initialize the recommender.
        
        Args:
            entry_point: Custom entry point coordinates (x, y)
        """
        self.entry_point = entry_point or self.ENTRY_POINT
    
    def _calculate_distance(self, slot_coords: Tuple[float, float]) -> float:
        """
        Calculate Euclidean distance from entry point to slot.
        
        Args:
            slot_coords: (x, y) coordinates of the slot
        
        Returns:
            Distance from entry point
        """
        dx = slot_coords[0] - self.entry_point[0]
        dy = slot_coords[1] - self.entry_point[1]
        return math.sqrt(dx**2 + dy**2)
    
    def get_slot_distance(self, slot_id: str) -> float:
        """
        Get distance from entry point to a specific slot.
        
        Args:
            slot_id: Slot identifier
        
        Returns:
            Distance to the slot
        """
        if slot_id not in self.SLOT_COORDINATES:
            raise ValueError(f"Unknown slot: {slot_id}")
        
        return self._calculate_distance(self.SLOT_COORDINATES[slot_id])
    
    def recommend(self, available_slots: List[str], top_n: int = 5) -> List[Dict]:
        """
        Recommend best available slots based on proximity to entry.
        
        Args:
            available_slots: List of available slot IDs
            top_n: Number of recommendations to return
        
        Returns:
            List of dicts with slot_id, distance, and coordinates
        """
        recommendations = []
        
        for slot_id in available_slots:
            if slot_id in self.SLOT_COORDINATES:
                coords = self.SLOT_COORDINATES[slot_id]
                distance = self._calculate_distance(coords)
                recommendations.append({
                    'slot_id': slot_id,
                    'distance': round(distance, 2),
                    'coordinates': coords,
                    'row': coords[0],
                    'column': coords[1]
                })
        
        # Sort by distance (closest first)
        recommendations.sort(key=lambda x: x['distance'])
        
        return recommendations[:top_n]
    
    def get_all_slots_ranked(self) -> List[Dict]:
        """
        Get all slots ranked by distance from entry point.
        
        Returns:
            List of all slots with distances
        """
        return self.recommend(list(self.SLOT_COORDINATES.keys()), 
                             top_n=len(self.SLOT_COORDINATES))
    
    def get_slot_info(self, slot_id: str) -> Dict:
        """
        Get detailed information about a specific slot.
        
        Args:
            slot_id: Slot identifier
        
        Returns:
            Dict with slot details
        """
        if slot_id not in self.SLOT_COORDINATES:
            return None
        
        coords = self.SLOT_COORDINATES[slot_id]
        return {
            'slot_id': slot_id,
            'coordinates': coords,
            'row': coords[0],
            'column': coords[1],
            'distance_from_entry': round(self._calculate_distance(coords), 2)
        }


if __name__ == "__main__":
    # Test the recommender
    recommender = SlotRecommender()
    
    print("Slot Recommender Test")
    print("=" * 40)
    
    # Get all slots ranked
    print("\nAll slots ranked by distance from entry:")
    for slot in recommender.get_all_slots_ranked()[:5]:
        print(f"  {slot['slot_id']}: distance = {slot['distance']:.2f}")
    
    # Test with available slots
    available = ['slot_5', 'slot_12', 'slot_3', 'slot_18']
    print(f"\nRecommendations from available slots {available}:")
    for rec in recommender.recommend(available):
        print(f"  {rec['slot_id']}: distance = {rec['distance']:.2f}")
