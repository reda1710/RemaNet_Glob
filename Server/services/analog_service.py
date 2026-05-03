from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any
from database import db
from data_generator import generate_sample_analog_data
from config import get_settings

logger = logging.getLogger(__name__)

async def get_logs_data(
    filter_date: Optional[str] = None,
    sensor_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get analog sensor data from database ONLY (no sample data generation) for logs page
    
    Args:
        filter_date: Optional date filter in format "MM/DD/YYYY"
        sensor_type: Optional sensor type filter ('analog_0' or 'analog_1')
        
    Returns:
        Dictionary containing data and notifications
    """
    try:
        collection = db.get_collection("analog")
        
        # Build query
        query = {}
        
        if filter_date:
            # Convert string to datetime for filtering
            date_obj = datetime.strptime(filter_date, "%m/%d/%Y")
            next_day = date_obj + timedelta(days=1)
            
            query["Time"] = {
                "$gte": date_obj,
                "$lt": next_day
            }
        
        # Add sensor type filter if specified
        if sensor_type:
            query["sensor_type"] = sensor_type
        
        # Project all feature fields
        projection = {
            "Time": 1,
            "sensor_type": 1,
            "clog_label": 1,
            "rms": 1,
            "spectral_energy": 1,
            "acoustic_power_derivative": 1,
            "kurtosis": 1,
            "peak_to_peak": 1,
            "dominant_freq": 1,
            "spectral_centroid": 1,
            "high_band_ratio": 1,
            "zero_crossing_rate": 1,
            "energy_entropy": 1,
            "_id": 0
        }
        
        # Fetch data from MongoDB ONLY - no fallback
        data = []
        try:
            if collection is not None:
                cursor = collection.find(query, projection).sort("Time", 1).limit(5000)
                data = list(cursor)
                logger.info(f"Retrieved {len(data)} records from analog collection for logs")
            else:
                logger.warning("Collection not available")
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
        
        # Transform field names to match frontend expectations
        transformed_data = []
        for item in data:
            # Convert datetime to ISO format string for JSON serialization
            time_value = item.get("Time")
            if isinstance(time_value, datetime):
                time_value = time_value.isoformat()
            
            transformed_item = {
                "Time": time_value,
                "RMS": item.get("rms"),
                "Spectral_Energy": item.get("spectral_energy"),
                "Peak_Frequency": item.get("dominant_freq"),
                "sensor_type": item.get("sensor_type"),
                "clog_label": item.get("clog_label")
            }
            
            # Add Acoustic_Derivative for acoustic sensor (analog_1)
            if item.get("sensor_type") == "analog_1":
                transformed_item["Acoustic_Derivative"] = item.get("acoustic_power_derivative")
            
            # Keep all original fields for backwards compatibility
            for key, value in item.items():
                if key not in transformed_item:
                    transformed_item[key] = value
            
            transformed_data.append(transformed_item)
        
        return {
            "data": transformed_data,
            "notifications": []
        }
    except Exception as e:
        logger.error(f"Error in get_logs_data: {e}")
        return {
            "data": [],
            "notifications": []
        }

async def get_filtered_data(
    filter_date: Optional[str] = None,
    sensor_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get analog sensor data with optional date and sensor type filtering
    
    Args:
        filter_date: Optional date filter in format "MM/DD/YYYY"
        sensor_type: Optional sensor type filter ('analog_0' or 'analog_1')
        
    Returns:
        Dictionary containing data and notifications
    """
    try:
        settings = get_settings()
        collection = db.get_collection("analog")
        
        # Build query
        query = {}
        
        if filter_date:
            # Convert string to datetime for filtering
            date_obj = datetime.strptime(filter_date, "%m/%d/%Y")
            next_day = date_obj + timedelta(days=1)
            
            query["Time"] = {
                "$gte": date_obj,
                "$lt": next_day
            }
        else:
            # For real-time data, get the last hour of data
            one_hour_ago = datetime.now() - timedelta(hours=1)
            query["Time"] = {
                "$gte": one_hour_ago
            }
        
        # Add sensor type filter if specified
        if sensor_type:
            query["sensor_type"] = sensor_type
        
        # Project all feature fields
        projection = {
            "Time": 1,
            "sensor_type": 1,
            "clog_label": 1,
            "rms": 1,
            "spectral_energy": 1,
            "acoustic_power_derivative": 1,
            "kurtosis": 1,
            "peak_to_peak": 1,
            "dominant_freq": 1,
            "spectral_centroid": 1,
            "high_band_ratio": 1,
            "zero_crossing_rate": 1,
            "energy_entropy": 1,
            "_id": 0
        }
        
        # Try to fetch data from MongoDB
        try:
            if collection is not None:
                cursor = collection.find(query, projection).sort("Time", 1).limit(5000)
                data = list(cursor)
                logger.info(f"Retrieved {len(data)} records from analog collection")
            else:
                logger.error("Collection not available")
                data = []
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            data = []
        
        # If no data found, generate sample data
        if not data:
            logger.info(f"No data found in database, generating sample data")
            data = generate_sample_analog_data(sensor_type=sensor_type or "analog_0")
        
        # Transform field names to match frontend expectations for logs page
        transformed_data = []
        for item in data:
            # Convert datetime to ISO format string for JSON serialization
            time_value = item.get("Time")
            if isinstance(time_value, datetime):
                time_value = time_value.isoformat()
            
            transformed_item = {
                "Time": time_value,
                "RMS": item.get("rms"),  # Capitalize for frontend
                "Spectral_Energy": item.get("spectral_energy"),
                "Peak_Frequency": item.get("dominant_freq"),  # Map dominant_freq to Peak_Frequency
                "sensor_type": item.get("sensor_type"),
                "clog_label": item.get("clog_label")
            }
            
            # Add Acoustic_Derivative for acoustic sensor (analog_1)
            if item.get("sensor_type") == "analog_1":
                transformed_item["Acoustic_Derivative"] = item.get("acoustic_power_derivative")
            
            # Keep all original fields for backwards compatibility
            for key, value in item.items():
                if key not in transformed_item:
                    transformed_item[key] = value
            
            transformed_data.append(transformed_item)
        
        data = transformed_data
        
        # Data is already processed in MongoDB
        # Check for anomalies based on feature thresholds
        notifications = []
        
        for item in data:
            timestamp = item.get("Time", "")
            s_type = item.get("sensor_type", "unknown")
            
            # Check RMS threshold (abnormal vibration/sound levels)
            if item.get("rms", 0) > getattr(settings, "MAX_RMS", 100):
                notifications.append({
                    "type": "warning",
                    "parameter": "rms",
                    "value": item["rms"],
                    "threshold": getattr(settings, "MAX_RMS", 100),
                    "timestamp": timestamp,
                    "sensor_type": s_type,
                    "message": f"RMS exceeded threshold for {s_type}: {item['rms']} > {getattr(settings, 'MAX_RMS', 100)}"
                })
            
            # Check spectral energy threshold
            if item.get("spectral_energy", 0) > getattr(settings, "MAX_SPECTRAL_ENERGY", 1000):
                notifications.append({
                    "type": "warning",
                    "parameter": "spectral_energy",
                    "value": item["spectral_energy"],
                    "threshold": getattr(settings, "MAX_SPECTRAL_ENERGY", 1000),
                    "timestamp": timestamp,
                    "sensor_type": s_type,
                    "message": f"Spectral energy exceeded threshold for {s_type}: {item['spectral_energy']} > {getattr(settings, 'MAX_SPECTRAL_ENERGY', 1000)}"
                })
            
            # Check kurtosis threshold (indicates signal abnormality)
            if item.get("kurtosis", 0) > getattr(settings, "MAX_KURTOSIS", 10):
                notifications.append({
                    "type": "warning",
                    "parameter": "kurtosis",
                    "value": item["kurtosis"],
                    "threshold": getattr(settings, "MAX_KURTOSIS", 10),
                    "timestamp": timestamp,
                    "sensor_type": s_type,
                    "message": f"Kurtosis exceeded threshold for {s_type}: {item['kurtosis']} > {getattr(settings, 'MAX_KURTOSIS', 10)}"
                })
        
        return {
            "data": data,
            "notifications": notifications
        }
    except Exception as e:
        logger.error(f"Error in get_filtered_data: {e}")
        return {
            "data": [],
            "notifications": []
        }
