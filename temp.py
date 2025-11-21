import os
import requests
import pandas as pd
import numpy as np
import google.generativeai as genai
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from dotenv import load_dotenv

# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------
# Load environment variables from the .env file in the same directory
load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configuration Check
if not OPENWEATHER_API_KEY or not GEMINI_API_KEY:
    raise ValueError("❌ API Keys missing! Please check your .env file.")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

# DEFINING PATHS
# We assume the CSV files are inside the subfolder named "flood prediction"
SUBFOLDER_NAME = "Flood-Prediction"  
FILE_RAIN = os.path.join(SUBFOLDER_NAME, "Hoppers Crossing-Hourly-Rainfall.csv")
FILE_RIVER = os.path.join(SUBFOLDER_NAME, "Hoppers Crossing-Hourly-River-Level.csv")

# ---------------------------------------------------------
# 2. TRAIN MODEL (Runs on Startup)
# ---------------------------------------------------------
def train_model():
    print("\n⏳ [1/4] Loading data and training model...")

    # Check if files exist in the subfolder
    if not os.path.exists(FILE_RAIN) or not os.path.exists(FILE_RIVER):
        print(f"❌ Error: Could not find CSV files in folder: '{SUBFOLDER_NAME}/'")
        print("   Please ensure the folder structure matches the code.")
        return None

    # Load Data
    df_rain = pd.read_csv(FILE_RAIN)
    df_river = pd.read_csv(FILE_RIVER)

    # Data Preprocessing (Speed Fix)
    df_rain['Date/Time'] = pd.to_datetime(df_rain['Date/Time'])
    df_river['Date/Time'] = pd.to_datetime(df_river['Date/Time'])

    # Merge Data
    df = pd.merge(df_rain, df_river, how='outer', on=['Date/Time'])
    df['Cumulative rainfall (mm)'] = df['Cumulative rainfall (mm)'].fillna(0)
    df['Level (m)'] = df['Level (m)'].fillna(0)

    # Prepare Training Variables
    df_clean = df.drop(columns=['Current rainfall (mm)', 'Date/Time'])
    X = df_clean.iloc[:, :1].values  # Input: Rain
    y = df_clean.iloc[:, 1:2].values # Output: River Level

    # Train Linear Regression
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
    regressor = LinearRegression()
    regressor.fit(X_train, y_train)

    print("✅ Model Trained Successfully.")
    return regressor

# ---------------------------------------------------------
# 3. FETCH LIVE WEATHER
# ---------------------------------------------------------
def get_live_weather(city):
    print(f"\n⏳ [2/4] Fetching live weather for {city}...")
    
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"❌ Error fetching weather: {response.status_code}")
        return None
    
    data = response.json()
    
    return {
        "city": data["name"],
        "temp": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "description": data["weather"][0]["description"],
        # Get rain from last 1h (default to 0 if no rain)
        "rain_1h": data.get("rain", {}).get("1h", 0.0)
    }

# ---------------------------------------------------------
# 4. GEMINI AI CHECKLIST GENERATOR
# ---------------------------------------------------------
def generate_ai_checklist(weather, predicted_level, flood_status):
    print("\n⏳ [4/4] Generating AI Safety Checklist...")
    
    prompt = f"""
    You are an expert flood safety assistant.
    
    Live Situation Report for {weather['city']}:
    - Current Rainfall: {weather['rain_1h']} mm
    - Weather Description: {weather['description']}
    - ML Model Prediction (River Level): {predicted_level:.2f} meters
    - Official Status: {flood_status}
    
    Based on this, provide:
    1. A brief situation summary (1 sentence).
    2. A "To-Do" checklist of 5 actionable safety steps for residents RIGHT NOW.
    3. If the status is "FLOOD WARNING", make the tone urgent. If "SAFE", make it educational.
    """
    
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating AI advice: {e}"

# ---------------------------------------------------------
# 5. MAIN EXECUTION LOOP
# ---------------------------------------------------------
if __name__ == "__main__":
    # Step A: Train the model
    model = train_model()

    if model:
        # Step B: Get User Input
        city = input("\n🌍 Enter City Name to check Flood Risk: ")
        weather = get_live_weather(city)

        if weather:
            print(f"\n📊 Live Data for {weather['city']}:")
            print(f"   - Rainfall (1h): {weather['rain_1h']} mm")
            print(f"   - Condition: {weather['description']}")

            # Step C: Predict using the ML Model
            # The model expects a 2D array, e.g., [[0.5]]
            input_rain = [[weather['rain_1h']]]
            prediction = model.predict(input_rain)
            predicted_level = prediction[0][0]

            print(f"\n🌊 ML PREDICTION:")
            print(f"   - Predicted River Level: {predicted_level:.2f} meters")

            # Step D: Determine Risk (Threshold = 1.5 meters)
            if predicted_level > 1.5:
                status = "🚨 FLOOD WARNING"
                print(f"   - Status: {status}")
            else:
                status = "✅ SAFE"
                print(f"   - Status: {status}")

            # Step E: Generate AI Checklist
            checklist = generate_ai_checklist(weather, predicted_level, status)
            
            print("\n" + "="*50)
            print("🤖 GEMINI SAFETY PLAN")
            print("="*50)
            print(checklist)