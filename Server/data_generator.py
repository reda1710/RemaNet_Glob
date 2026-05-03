import random
from datetime import datetime, timedelta
import numpy as np
import base64

def generate_sample_coldspray_data(num_points=50):
    """Generate sample cold spray data for testing"""
    start_time = datetime.now() - timedelta(seconds=num_points)
    data = []
    
    for i in range(num_points):
        time = start_time + timedelta(seconds=i)
        timestamp = int(time.timestamp())  # Convert to Unix timestamp
        
        # Generate Clog_Label (mostly 0, occasional 1 for testing notifications)
        clog_label = 1 if random.random() < 0.05 else 0  # 5% chance of clogging
        
        data.append({
            "Time": timestamp,
            "clog_label": clog_label,  # Lowercase to match database
            # 13 KPI columns (using database field names)
            "P_Gun": 45 + random.uniform(-3, 3) + (i % 5),  # Pressure pattern
            "sigma_P": 2 + random.uniform(-0.5, 0.5),  # Pressure standard deviation (DB field name)
            "Q_PG_N2": 45 + random.uniform(-2, 2) + (i % 7),  # N2 flow rate
            "R_FP": 0.8 + random.uniform(-0.1, 0.1),  # Feed rate ratio
            "U3_Input": 220 + random.uniform(-10, 10),  # Input voltage
            "T_Gun": 45 + random.uniform(-5, 5) + (i % 10),  # Gun temperature
            "Q_WC": 10 + random.uniform(-1, 1),  # Water cooling flow rate
            "T_WC": 20 + random.uniform(-2, 2),  # Water cooling temperature
            "m_dot_pow": 30 + random.uniform(-3, 3),  # Powder mass flow rate (DB field name)
            "P_PF1": 40 + random.uniform(-2, 2),  # Powder feeder 1 pressure
            "Q_CG_PF1": 45 + random.uniform(-1, 1) + (i % 3),  # Feeder 1 flow rate
            "acoustic_power_derivative": random.uniform(-5, 5)  # Acoustic pressure derivative (coldspray)
        })
    
    return data

def generate_mic_waveform(num_samples=100):
    """Generate sample microphone waveform data"""
    t = np.linspace(0, 1, num_samples)
    
    # Generate base sine wave with some noise
    frequency = random.uniform(10, 20)  # Random frequency
    amplitude = random.uniform(0.5, 1.0)  # Random amplitude
    
    # Create waveform with harmonics
    waveform = amplitude * np.sin(2 * np.pi * frequency * t)
    waveform += 0.3 * np.sin(2 * np.pi * frequency * 2 * t)  # Add first harmonic
    waveform += 0.15 * np.sin(2 * np.pi * frequency * 3 * t)  # Add second harmonic
    
    # Add some noise
    noise = np.random.normal(0, 0.05, num_samples)
    waveform += noise
    
    # Convert to float32 (typical audio format)
    waveform = waveform.astype(np.float32)
    
    # Convert to base64 for transmission
    waveform_bytes = waveform.tobytes()
    base64_data = base64.b64encode(waveform_bytes).decode('utf-8')
    
    return {
        "timestamp": datetime.now(),    
        "data": base64_data,
    }

def generate_sample_analog_data(num_points=50, sensor_type="analog_0"):
    """
    Generate sample analog sensor data for testing (11 features per 0.2s window)
    
    Args:
        num_points: Number of data points to generate
        sensor_type: 'analog_0' (ultrasonic) or 'analog_1' (acoustic)
    """
    start_time = datetime.now() - timedelta(seconds=num_points * 0.2)  # 0.2s window
    data = []
    
    for i in range(num_points):
        time = start_time + timedelta(seconds=i * 0.2)
        timestamp = int(time.timestamp())
        
        # Generate clog_label (mostly 0, occasional 1 for testing)
        clog_label = 1 if random.random() < 0.05 else 0  # 5% chance of clogging
        
        # Base values differ slightly between sensor types
        base_multiplier = 1.0 if sensor_type == "analog_0" else 1.2
        
        data.append({
            "Time": timestamp,
            "sensor_type": sensor_type,
            "clog_label": clog_label,
            # 11 acoustic/vibration features
            "rms": (30 + random.uniform(-5, 5) + (i % 8)) * base_multiplier,
            "spectral_energy": (200 + random.uniform(-30, 30) + (i % 10)) * base_multiplier,
            "acoustic_power_derivative": random.uniform(-2, 2),
            "kurtosis": 3 + random.uniform(-0.5, 0.5) + (0.1 * i % 2),
            "peak_to_peak": (60 + random.uniform(-10, 10)) * base_multiplier,
            "dominant_freq": 1000 + random.uniform(-200, 200) + (i % 15),
            "spectral_centroid": 2000 + random.uniform(-300, 300),
            "high_band_ratio": 0.3 + random.uniform(-0.05, 0.05),
            "zero_crossing_rate": 0.15 + random.uniform(-0.03, 0.03),
            "energy_entropy": 2.5 + random.uniform(-0.3, 0.3)
        })
    
    return data
