import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURATION (IMPORTANT) ---
# Remplace par tes vrais identifiants Strava
CLIENT_ID = '190978'
CLIENT_SECRET = 'TON_CLIENT_SECRET_ICI' 
# L'URL de ton application une fois publiée (ex: https://mon-app.streamlit.app/)
REDIRECT_URI = 'https://ton-app.streamlit.app/' 

# --- CONFIGURATION UI ---
st.set_page_config(page_title="Performance Report 2026", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FDFBF7; }
    h1, h2, h3, h4, p, span, label { color: #000000 !important; font-family: 'Inter', sans-serif; }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 2px solid #D1D5DB !important;
        border-radius: 10px;
        padding: 10px 12px !important;
    }
    div[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 800 !important; color: #000000 !important; }
    .status-box {
        background-color: #FFFFFF; padding: 20px; border-radius: 10px;
        border: 2px solid #D1D5DB; border-left: 8px solid #FC4C02; margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

MOIS_FR = {1: "Jan", 2: "Fév", 3: "Mar", 4: "Avr", 5: "Mai", 6: "Juin", 
           7: "Juil", 8: "Août", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Déc"}

# --- LOGIQUE DE CONNEXION ---

if 'access_token' not in st.session_state:
    st.title("🏃 Performance Report 2026")
    st.subheader("Connectez votre compte Strava pour voir vos statistiques")
    
    auth_url = (
        f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}"
        f"&response_type=code&redirect_uri={REDIRECT_URI}"
        f"&scope=activity:read_all&approval_prompt=auto"
    )
    
    st.link_button("🚀 Se connecter avec Strava", auth_url)

    # Récupération du code de retour dans l'URL
    code = st.query_params.get("code")
    if code:
        res = requests.post("https://www.strava.com/oauth/token", data={
            'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
            'code': code, 'grant_type': 'authorization_code'
        }).json()
        
        if 'access_token' in res:
            st.session_state['access_token'] = res['access_token']
            st.rerun()
    st.stop() # Arrête le code ici tant qu'on n'est pas connecté

# Si on arrive ici, c'est qu'on a le token de l'utilisateur
token = st.session_state['access_token']

@st.cache_data(ttl=3600)
def fetch_activities(token):
    all_activities = []
    for page in range(1, 6): # Récupère les 1000 dernières activités
        url = f"https://www.strava.com/api/v3/athlete/activities?per_page=200&page={page}"
        data = requests.get(url, headers={'Authorization': f'Bearer {token}'}).json()
        if not data or 'message' in data: break
        all_activities.extend(data)
    
    df = pd.DataFrame(all_activities)
    if df.empty: return df
    
    df = df[df['type'].isin(['Run', 'TrailRun'])]
    df['start_date_local'] = pd.to_datetime(df['start_date_local']).dt.tz_localize(None)
    df['distance_km'] = (df['distance'] / 1000).round(2)
    df['elevation_gain'] = df['total_elevation_gain'].fillna(0)
    df['year'] = df['start_date_local'].dt.year
    df['jour_annee'] = df['start_date_local'].dt.dayofyear
    df['mois_num'] = df['start_date_local'].dt.month
    df['mois_fr'] = df['mois_num'].map(MOIS_FR)
    return df

# --- AFFICHAGE DU RAPPORT (Utilise maintenant les données de l'utilisateur connecté) ---
try:
    df_all = fetch_activities(token)
    if df_all.empty:
        st.warning("Aucune course trouvée.")
    else:
        # (Ici on garde toute la logique de tes graphiques précédents...)
        st.success("Connecté !")
        dist_totale = df_all[df_all['year'] == 2026]['distance_km'].sum()
        st.metric("Ton Cumul 2026", f"{dist_totale:.1f} km")
        
        if st.sidebar.button("Déconnexion"):
            del st.session_state['access_token']
            st.rerun()
except Exception as e:
    st.error(f"Erreur : {e}")
