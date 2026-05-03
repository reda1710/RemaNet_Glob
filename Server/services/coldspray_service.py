from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any
from database import db
from data_generator import generate_sample_coldspray_data
from config import get_settings
from services import analog_service

logger = logging.getLogger(__name__)

async def get_logs_data(filter_date: Optional[str] = None) -> Dict[str, Any]:
    """Get cold spray data from database ONLY (no sample data generation) for logs page"""
    try:
        settings = get_settings()
        collection = db.get_collection("coldspray")
        
        if filter_date:
            # Convert string to datetime for filtering
            date_obj = datetime.strptime(filter_date, "%m/%d/%Y")
            next_day = date_obj + timedelta(days=1)
            
            # Query for specific date
            query = {
                "Time": {
                    "$gte": date_obj,
                    "$lt": next_day
                }
            }
        else:
            # Get all available data (no time filter)
            query = {}
        
        # Project only the fields we need
        projection = {
            "Time": 1,
            "clog_label": 1,
            "P_Gun": 1,
            "sigma_P": 1,
            "Q_PG_N2": 1,
            "R_FP": 1,
            "U3_Input": 1,
            "T_Gun": 1,
            "Q_WC": 1,
            "T_WC": 1,
            "m_dot_pow": 1,
            "P_PF1": 1,
            "Q_CG_PF1": 1,
            "acoustic_power_derivative": 1,
            "_id": 0
        }
        
        # Fetch data from MongoDB ONLY - no fallback
        data = []
        try:
            if collection is not None:
                cursor = collection.find(query, projection).sort("Time", 1).limit(5000)
                data = list(cursor)
                logger.info(f"Retrieved {len(data)} records from coldspray for logs")
            else:
                logger.warning("Collection not available")
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
        
        # Convert datetime objects to ISO format strings for JSON serialization
        for item in data:
            if "Time" in item and isinstance(item["Time"], datetime):
                item["Time"] = item["Time"].isoformat()
        
        return {
            "data": data,
            "notifications": []
        }
    except Exception as e:
        logger.error(f"Error in get_logs_data: {e}")
        return {
            "data": [],
            "notifications": []
        }

async def get_filtered_data(filter_date: Optional[str] = None) -> Dict[str, Any]:
    """Get cold spray data with optional date filtering"""
    try:
        settings = get_settings()
        collection = db.get_collection("coldspray")
        
        if filter_date:
            # Convert string to datetime for filtering
            date_obj = datetime.strptime(filter_date, "%m/%d/%Y")
            next_day = date_obj + timedelta(days=1)
            
            # Query for specific date
            query = {
                "Time": {
                    "$gte": date_obj,
                    "$lt": next_day
                }
            }
        else:
            # For real-time data, get the last hour of data
            one_hour_ago = datetime.now() - timedelta(hours=1)
            query = {
                "Time": {
                    "$gte": one_hour_ago
                }
            }
        
        # Project only the fields we need (13 KPIs + Clog_Label + Time)
        # Note: Database uses sigma_P and m_dot_pow instead of Unicode characters
        projection = {
            "Time": 1,
            "clog_label": 1,  # Database uses lowercase
            "P_Gun": 1,
            "sigma_P": 1,  # Database field name
            "Q_PG_N2": 1,
            "R_FP": 1,
            "U3_Input": 1,
            "T_Gun": 1,
            "Q_WC": 1,
            "T_WC": 1,
            "m_dot_pow": 1,  # Database field name
            "P_PF1": 1,
            "Q_CG_PF1": 1,
            "acoustic_power_derivative": 1,  # Coldspray acoustic derivative
            "_id": 0
        }
        
        # Try to fetch data from MongoDB
        try:
            if collection is not None:
                cursor = collection.find(query, projection).sort("Time", 1).limit(5000)
                data = list(cursor)
                logger.info(f"Retrieved {len(data)} records from coldspray")
            else:
                logger.error("Collection not available")
                data = []
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            data = []
        
        # If no data found, generate sample data
        if not data:
            logger.info(f"No data found in database, generating sample data")
            data = generate_sample_coldspray_data()
        
        # Convert datetime objects to ISO format strings for JSON serialization
        for item in data:
            if "Time" in item and isinstance(item["Time"], datetime):
                item["Time"] = item["Time"].isoformat()
        
        # Check for threshold exceedances and generate notifications
        notifications = []
        
        for item in data:
            timestamp = item.get("Time", "")
            
            # Check T_Gun threshold
            if item.get("T_Gun", 0) > settings.MAX_T_GUN:
                notifications.append({
                    "type": "warning",
                    "parameter": "T_Gun",
                    "value": item["T_Gun"],
                    "threshold": settings.MAX_T_GUN,
                    "timestamp": timestamp,
                    "message": f"T_Gun exceeded maximum threshold: {item['T_Gun']} > {settings.MAX_T_GUN}"
                })
            
            # Check P_Gun threshold
            if item.get("P_Gun", 0) > settings.MAX_P_GUN:
                notifications.append({
                    "type": "warning",
                    "parameter": "P_Gun",
                    "value": item["P_Gun"],
                    "threshold": settings.MAX_P_GUN,
                    "timestamp": timestamp,
                    "message": f"P_Gun exceeded maximum threshold: {item['P_Gun']} > {settings.MAX_P_GUN}"
                })
            
            # Check Q_PG_N2 threshold
            if item.get("Q_PG_N2", 0) > settings.MAX_Q_PG_N2:
                notifications.append({
                    "type": "warning",
                    "parameter": "Q_PG_N2",
                    "value": item["Q_PG_N2"],
                    "threshold": settings.MAX_Q_PG_N2,
                    "timestamp": timestamp,
                    "message": f"Q_PG_N2 exceeded maximum threshold: {item['Q_PG_N2']} > {settings.MAX_Q_PG_N2}"
                })
        
        # Fetch analog sensor data for the same time period
        analog_0_result = await analog_service.get_filtered_data(filter_date, "analog_0")
        analog_1_result = await analog_service.get_filtered_data(filter_date, "analog_1")
        
        # Combine all notifications
        all_notifications = notifications + analog_0_result.get("notifications", []) + analog_1_result.get("notifications", [])
        
        return {
            "data": data,
            "analog_0": analog_0_result.get("data", []),
            "analog_1": analog_1_result.get("data", []),
            "notifications": all_notifications
        }
    except Exception as e:
        logger.error(f"Error in get_filtered_data: {e}")
        return {
            "data": [],
            "notifications": []
        }
