import streamlit as st
import requests
from textblob import TextBlob
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from gtts import gTTS
import folium
from streamlit_folium import st_folium
from audio_recorder_streamlit import audio_recorder
import speech_recognition as sr
import tempfile

# --- CONFIG ---
st.set_page_config(page_title="AI Disaster Survival Assistant", layout="wide")

# --- DARK/LIGHT MODE TOGGLE ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

mode_icon = "🌙 Dark" if not st.session_state.dark_mode else "☀️ Light"
if st.button(mode_icon, key="mode_toggle"):
    st.session_state.dark_mode = not st.session_state.dark_mode

# Apply CSS for modes
if st.session_state.dark_mode:
    st.markdown("""
        <style>
        body, .stApp { background-color: #121212; color: #ffffff; }
        .stButton>button { background-color: #1f1f1f; color: #ffffff; border-radius: 8px; }
        label { color: #00adb5 !important; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        body, .stApp { background-color: #ffffff; color: #000000; }
        .stButton>button { background-color: #f0f0f0; color: #000000; border-radius: 8px; }
        label { color: #0077b6 !important; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR SETTINGS ---
st.sidebar.title("⚙️ Settings")
lang = st.sidebar.selectbox("Choose your language", ["en", "hi", "te", "ta"])

# --- TITLE ---
st.title("🌊🔥 AI Disaster Survival Assistant")
st.write("Get survival tips, weather alerts, and nearest shelters based on your location.")

# --- API KEY ---
API_KEY = "fa0d13abe47d80f5147f94e0c2491736"  # Replace with your OpenWeatherMap API key

# --- AUTO-DETECT LOCATION ---
def get_ip_location():
    try:
        res = requests.get("https://ipinfo.io/json").json()
        lat, lon = map(float, res["loc"].split(","))
        return lat, lon, res.get("city", "Unknown")
    except:
        return 17.5400, 78.4867, "Hyderabad"  # default fallback

user_lat, user_lon, detected_city = get_ip_location()
st.success(f"📍 Auto-detected location: {detected_city} (Lat: {user_lat}, Lon: {user_lon})")

# --- SHELTER DATA ---
shelters = [
    {"name": "Community Center - Balapur", "lat": 17.3100, "lon": 78.5400, "capacity": "200", "contact": "9876543210"},
    {"name": "Relief Camp - Dundigal", "lat": 17.5405, "lon": 78.4870, "capacity": "150", "contact": "9876543211"},
    {"name": "Govt School Shelter - Hyderabad", "lat": 17.3850, "lon": 78.4867, "capacity": "300", "contact": "9876543212"},
    {"name": "NGO Shelter - Miyapur", "lat": 17.5000, "lon": 78.4000, "capacity": "100", "contact": "9876543213"}
]

# --- REVERSE GEOCODING ---
def get_city_from_location(lat, lon):
    geolocator = Nominatim(user_agent="disaster-assistant")
    try:
        location = geolocator.reverse((lat, lon), language='en')
        address = location.raw.get("address", {})
        return address.get("city") or address.get("town") or address.get("village") or "Unknown"
    except:
        return "Unknown"

# --- WEATHER ALERT ---
def get_weather_alert(city="Hyderabad"):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    response = requests.get(url).json()
    if response.get("cod") != 200:
        return f"⚠️ Weather data unavailable for {city}."

    temp = response["main"]["temp"]
    weather = response["weather"][0]["description"]

    if temp > 40:
        return f"⚠️ Heatwave Alert in {city}! Temp: {temp}°C. Stay hydrated and avoid sunlight."
    elif "rain" in weather or "storm" in weather:
        return f"⚠️ Flood/Storm Alert in {city}! Weather: {weather}. Move to safe areas."
    else:
        return f"✅ Current weather in {city}: {weather}, Temp: {temp}°C."

# --- NEAREST SHELTERS ---
def get_nearest_shelters(user_lat, user_lon, shelters, top_n=3):
    for shelter in shelters:
        shelter['distance'] = geodesic((user_lat, user_lon), (shelter['lat'], shelter['lon'])).km
    shelters_sorted = sorted(shelters, key=lambda x: x['distance'])
    return shelters_sorted[:top_n]

# --- VOICE OUTPUT ---
def speak_multilingual(text, lang='hi', filename="response.mp3"):
    tts = gTTS(text, lang=lang)
    tts.save(filename)
    st.audio(filename, format="audio/mp3")

# --- NLP RESPONSE ---
def get_response(message, city_name):
    blob = TextBlob(message)
    mood = blob.sentiment.polarity

    if "flood" in message.lower() or "rain" in message.lower() or "storm" in message.lower():
        response = "🌊 During floods: Move to higher ground, avoid waterlogged areas, carry drinking water."
        response += "\n" + get_weather_alert(city_name)
    elif "heat" in message.lower() or "heatwave" in message.lower():
        response = "🔥 During heatwaves: Stay hydrated, avoid direct sunlight, wear light clothing."
        response += "\n" + get_weather_alert(city_name)
    elif "shelter" in message.lower() or "safe place" in message.lower():
        nearest = get_nearest_shelters(user_lat, user_lon, shelters)
        response = "🏠 Nearest shelters:\n"
        for s in nearest:
            response += f"- {s['name']} ({s['distance']:.2f} km)\n  Capacity: {s['capacity']}, Contact: {s['contact']}\n"
    else:
        response = "🤖 I can give tips about floods, heatwaves, or shelters. Try asking about them!"

    if mood < -0.3:
        response += "\n⚠️ You seem stressed. Stay calm and follow safety instructions."

    response += "\n📞 Emergency Helpline: 108 (Ambulance), 100 (Police), 101 (Fire)"
    return response

# --- DETECT CITY ---
city_name = get_city_from_location(user_lat, user_lon)
st.write(f"📍 Detected city (via GPS/Map): **{city_name}**")

# --- CHAT INPUT ---
user_input = st.text_input("💬 Type your question:")
st.write("🎤 Or record your voice:")
audio_bytes = audio_recorder()

voice_input = None
if audio_bytes:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        recognizer = sr.Recognizer()
        with sr.AudioFile(f.name) as source:
            audio = recognizer.record(source)
            try:
                voice_input = recognizer.recognize_google(audio)
            except:
                voice_input = "Sorry, could not recognize speech."

final_input = user_input if user_input else voice_input
if final_input:
    reply = get_response(final_input, city_name)
    st.write(f"**AI:** {reply}")
    if lang != "en":
        speak_multilingual(reply, lang=lang)

# --- MAP DISPLAY ---
nearest = get_nearest_shelters(user_lat, user_lon, shelters)
m = folium.Map(location=[user_lat, user_lon], zoom_start=14)
folium.Marker([user_lat, user_lon], popup="You are here", icon=folium.Icon(color='blue')).add_to(m)

for shelter in nearest:
    popup_text = f"{shelter['name']}<br>Capacity: {shelter['capacity']}<br>Contact: {shelter['contact']}<br>Distance: {shelter['distance']:.2f} km"
    folium.Marker(
        [shelter['lat'], shelter['lon']],
        popup=popup_text,
        icon=folium.Icon(color='green', icon='info-sign')
    ).add_to(m)

st_folium(m, width=700, height=500)
