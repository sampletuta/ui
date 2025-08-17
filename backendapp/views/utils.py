"""
Utility Functions and Helper Views
Contains helper functions, permission checks, and utility functions for views
"""

import folium
from math import radians, cos, sin, asin, sqrt
import logging

logger = logging.getLogger(__name__)

# Permission and role checking functions
def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and user.role == 'admin'

def is_case_manager(user):
    """Check if user is case manager"""
    return user.is_authenticated and user.role == 'case_manager'

def is_operator(user):
    """Check if user is operator"""
    return user.is_authenticated and user.role == 'operator'

def is_staff_or_admin(user):
    """Check if user is staff or admin"""
    return user.is_authenticated and (user.is_staff or user.role == 'admin')

# Geospatial utility functions
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth"""
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

# Folium Map Functions
def create_search_map():
    """Create a Folium map for search interface"""
    # Default to a central location (e.g., NYC)
    center_lat, center_lng = 40.7128, -74.0060
    
    map_obj = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Add a marker for the center point
    folium.Marker(
        [center_lat, center_lng],
        popup='Search Center',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(map_obj)
    
    return map_obj

def create_results_map(results, search_query):
    """Create a Folium map showing search results"""
    if not results:
        return create_search_map()
    
    # Calculate center point from results or use search query center
    if search_query.latitude and search_query.longitude:
        center_lat, center_lng = search_query.latitude, search_query.longitude
    else:
        # Calculate center from results
        lats = [r.latitude for r in results if r.latitude]
        lngs = [r.longitude for r in results if r.longitude]
        if lats and lngs:
            center_lat, center_lng = sum(lats)/len(lats), sum(lngs)/len(lngs)
        else:
            center_lat, center_lng = 40.7128, -74.0060
    
    map_obj = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=12,
        tiles='OpenStreetMap'
    )
    
    # Add search radius circle if specified
    if search_query.latitude and search_query.longitude and search_query.radius_km:
        folium.Circle(
            radius=search_query.radius_km * 1000,  # Convert km to meters
            location=[search_query.latitude, search_query.longitude],
            popup=f'Search Radius: {search_query.radius_km}km',
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.2
        ).add_to(map_obj)
    
    # Add markers for each result
    for result in results:
        if result.latitude and result.longitude:
            folium.Marker(
                [result.latitude, result.longitude],
                popup=f"""
                <b>{result.target.target_name}</b><br>
                Confidence: {result.confidence:.2f}<br>
                Time: {result.timestamp}s<br>
                Camera: {result.camera_name or 'Unknown'}
                """,
                icon=folium.Icon(color='blue', icon='user')
            ).add_to(map_obj)
    
    return map_obj

# Search Execution Functions
def execute_advanced_search(search_query):
    """Execute advanced search with all filters"""
    # This would integrate with your face detection service
    # For now, return mock results
    
    # Apply geospatial filter
    if search_query.latitude and search_query.longitude:
        # Filter by radius using haversine distance
        pass
    
    # Apply date filter
    if search_query.start_date or search_query.end_date:
        # Filter by date range
        pass
    
    # Apply confidence threshold
    # Filter by confidence
    
    # Apply target filters
    if search_query.target_filters:
        # Filter by selected targets
        pass
    
    # This would call your external face detection service
    # and return results in the SearchResult format
    
    return []

def execute_quick_search(search_type, query_text, confidence, start_date, end_date):
    """Execute quick search"""
    # Simple search implementation
    # This would integrate with your face detection service
    
    return []
