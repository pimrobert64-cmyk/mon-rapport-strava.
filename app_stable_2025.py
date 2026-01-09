import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURATION API ---
CLIENT_ID = '190978'
CLIENT_SECRET = 'a3b87fce4f2bcdd92dc18c19548f0f9a22d6b6e8'
REFRESH_TOKEN = '8b4054d6454a4f92e449b6e7937f7784e4cc816f'

# --- CONFIGURATION UI ---
st.set_page_config(page_title="Performance Report 2026", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FDFBF7; }
    h1, h2, h3, h4, p, span, label { color: #000000 !important; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-weight: 900 !important; }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 2px solid #D1D5DB !important;
        border-radius: 10px;
        padding: 10px 12px !important;
    }
    div[data-testid="stMetricValue"] { 
        font-size: 26px !important; 
        color: #000000 !important;
        font-weight: 800 !important;
    }
    div[data-testid="stMetricLabel"] p { 
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        margin-bottom: 0px !important;
        text-transform: uppercase;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 0.8rem !important;
    }

    .status-box {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #D1D5DB;
        border-left: 8px solid #FC4C02;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

if st.sidebar.button("🔄 Forcer la synchro complète"):
    st.cache_data.clear()
    st.rerun()

MOIS_FR = {1: "Jan", 2: "Fév", 3: "Mar", 4: "Avr", 5: "Mai", 6: "Juin", 
           7: "Juil", 8: "Août", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Déc"}

def get_new_access_token():
    res = requests.post("https://www.strava.com/oauth/token", data={
        'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN, 'grant_type': 'refresh_token'
    })
    return res.json()['access_token']

@st.cache_data(ttl=3600)
def fetch_all_activities(token):
    all_activities = []
    for page in range(1, 15):
        url = f"https://www.strava.com/api/v3/athlete/activities?per_page=200&page={page}"
        data = requests.get(url, headers={'Authorization': f'Bearer {token}'}).json()
        if not data or len(data) == 0: break
        all_activities.extend(data)
    
    df = pd.DataFrame(all_activities)
    df = df[df['type'].isin(['Run', 'TrailRun'])]
    df['start_date_local'] = pd.to_datetime(df['start_date_local']).dt.tz_localize(None)
    df['distance_km'] = (df['distance'] / 1000).round(2)
    df['elevation_gain'] = df['total_elevation_gain'].fillna(0)
    df['year'] = df['start_date_local'].dt.year
    df['jour_annee'] = df['start_date_local'].dt.dayofyear
    df['mois_num'] = df['start_date_local'].dt.month
    df['mois_fr'] = df['mois_num'].map(MOIS_FR)
    df['semaine_date'] = df['start_date_local'].dt.to_period('W').apply(lambda r: r.start_time).dt.strftime('%d/%m')
    return df

try:
    token = get_new_access_token()
    df_all = fetch_all_activities(token)
    
    df_2026 = df_all[df_all['year'] == 2026].sort_values('start_date_local')
    df_2025 = df_all[df_all['year'] == 2025].sort_values('start_date_local')

    maintenant = datetime.now()
    mois_actuel = maintenant.month
    nom_mois_actuel = MOIS_FR[mois_actuel]
    jour_actuel_annee = maintenant.timetuple().tm_yday

    # --- CALCULS ---
    dist_2026 = df_2026['distance_km'].sum()
    dist_2025_totale = df_2025['distance_km'].sum()
    
    dist_mois_2026 = df_2026[df_2026['mois_num'] == mois_actuel]['distance_km'].sum()
    dist_mois_2025 = df_2025[df_2025['mois_num'] == mois_actuel]['distance_km'].sum()
    diff_mois = dist_mois_2026 - dist_mois_2025
    pct_mois = (diff_mois / dist_mois_2025 * 100) if dist_mois_2025 > 0 else 0

    diff_annuelle = dist_2026 - dist_2025_totale
    pct_annuel = (diff_annuelle / dist_2025_totale * 100) if dist_2025_totale > 0 else 0

    obj_km = st.sidebar.number_input("Objectif annuel (km)", value=1500.0, step=10.0)
    reste_total = max(0.0, obj_km - dist_2026)
    jours_restants = (datetime(2026, 12, 31) - maintenant).days + 1
    cible_hebdo = reste_total if jours_restants <= 7 else (reste_total / jours_restants) * 7

    st.title("🏃 Performance Report 2026")

    # 1. MÉTRIQUES
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Cumul 2026", f"{dist_2026:,.1f} km")
    m2.metric(f"Mois ({nom_mois_actuel})", f"{dist_mois_2026:,.1f} km", delta=f"{diff_mois:+,.1f} ({pct_mois:+.1f}%)")
    m3.metric("Reste à courir", f"{reste_total:,.1f} km")
    m4.metric("Cible Hebdo", f"{cible_hebdo:,.1f} km")
    m5.metric("Évol. vs 2025", f"{diff_annuelle:+,.1f} km", delta=f"{pct_annuel:+.1f}%")

    # 2. ANALYSE DE FORME
    st.markdown("---")
    debut_sem = maintenant.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=maintenant.weekday())
    moy_4_sem = df_all[(df_all['start_date_local'] >= (debut_sem - timedelta(weeks=4))) & (df_all['start_date_local'] < debut_sem)]['distance_km'].sum() / 4
    actuel_sem = df_all[df_all['start_date_local'] >= debut_sem]['distance_km'].sum()
    diff_forme = ((actuel_sem - moy_4_sem) / moy_4_sem * 100) if moy_4_sem > 0 else 0
    
    st.markdown(f"""<div class='status-box'>
        <h3>💡 État de forme : {"🔥 Intensif" if diff_forme > 15 else "⚖️ Stable" if diff_forme > -15 else "📉 Récupération"}</h3>
        <p><b>Cette semaine :</b> {actuel_sem:.1f} km | <b>Moyenne (4 sem) :</b> {moy_4_sem:.1f} km | <b>Ecart :</b> {diff_forme:+.1f}%</p>
    </div>""", unsafe_allow_html=True)

    # --- GRAPHIQUES ---

    st.subheader("📅 Volume Mensuel (km)")
    mensuel = df_2026.groupby(['mois_num', 'mois_fr'])['distance_km'].sum().reset_index()
    fig_m = px.bar(mensuel, x='mois_fr', y='distance_km', text_auto='.1f', color_discrete_sequence=['#FC4C02'])
    fig_m.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_m, use_container_width=True)

    st.markdown("---")
    st.subheader("🗓️ Volume Hebdomadaire (km)")
    hebdo = df_2026.groupby('semaine_date', sort=False)['distance_km'].sum().reset_index()
    fig_h = px.line(hebdo, x='semaine_date', y='distance_km', markers=True, color_discrete_sequence=['#2D2D2D'])
    fig_h.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_h, use_container_width=True)

    st.markdown("---")
    # --- NOUVEAU GRAPH : CUMUL vs OBJECTIF DYNAMIQUE ---
    st.subheader("📈 Progression Cumulée vs Objectif Annuel")
    
    # Calcul du cumul réel par jour de l'année
    cumul_reel = df_2026.groupby('jour_annee')['distance_km'].sum().reindex(range(1, 366), fill_value=0).cumsum()
    cumul_reel_actuel = cumul_reel[:jour_actuel_annee]
    
    # Ligne d'objectif dynamique (droite de progression théorique)
    ligne_objectif = [ (obj_km / 365) * i for i in range(1, 366) ]
    jours = list(range(1, 366))

    fig_cumul = go.Figure()
    # Zone d'objectif
    fig_cumul.add_trace(go.Scatter(x=jours, y=ligne_objectif, name='Objectif théorique', 
                                  line=dict(color='#D1D5DB', width=2, dash='dash')))
    # Progression réelle
    fig_cumul.add_trace(go.Scatter(x=jours[:jour_actuel_annee], y=cumul_reel_actuel, name='Cumul Réel', 
                                  fill='tozeroy', line=dict(color='#FC4C02', width=4)))
    
    fig_cumul.update_layout(height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                            hovermode="x unified", xaxis_title="Jour de l'année", yaxis_title="Kilomètres")
    st.plotly_chart(fig_cumul, use_container_width=True)

    st.markdown("---")
    st.subheader("⛰️ Dénivelé Cumulé par Mois (m)")
    elev_m_data = df_2026.groupby(['mois_num', 'mois_fr'])['elevation_gain'].sum().reset_index()
    template = pd.DataFrame({'mois_num': range(1, 13), 'mois_fr': [MOIS_FR[i] for i in range(1, 13)]})
    elev_m = pd.merge(template, elev_m_data, on=['mois_num', 'mois_fr'], how='left').fillna(0)
    fig_e = px.bar(elev_m, x='mois_fr', y='elevation_gain', color_discrete_sequence=['#FC4C02'])
    fig_e.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis_title="Dénivelé (D+)")
    st.plotly_chart(fig_e, use_container_width=True)

    st.markdown("---")
    st.subheader("🎯 Typologie des sorties")
    def cat(d): return "Courte (<10km)" if d < 10 else ("Moyenne (10-20km)" if d <= 20 else "Longue (>20km)")
    df_2026['cat'] = df_2026['distance_km'].apply(cat)
    counts = df_2026['cat'].value_counts().reset_index()
    fig_p = px.pie(counts, values='count', names='cat', hole=0.5,
                   color_discrete_sequence=['#FC4C02', '#2D2D2D', '#D1D5DB'])
    fig_p.update_layout(height=450, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5))
    fig_p.update_traces(textinfo='percent+label', textfont_size=13)
    st.plotly_chart(fig_p, use_container_width=True)

    st.markdown("---")
    st.subheader("🏁 Duel : 2025 vs 2026 (Cumul)")
    c25 = df_2025.groupby('jour_annee')['distance_km'].sum().reindex(range(1, 367), fill_value=0).cumsum()
    fig_d = go.Figure()
    fig_d.add_trace(go.Scatter(x=list(range(1, 367)), y=c25, name='2025', line=dict(color='#D1D5DB', width=2)))
    fig_d.add_trace(go.Scatter(x=list(range(1, jour_actuel_annee+1)), y=cumul_reel_actuel, name='2026', line=dict(color='#FC4C02', width=5)))
    fig_d.update_layout(height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified")
    st.plotly_chart(fig_d, use_container_width=True)

except Exception as e:
    st.error(f"Erreur : {e}")