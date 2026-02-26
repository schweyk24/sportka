import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np
import requests
import bcrypt

# --- KONFIGURACE ---
st.set_page_config(page_title="Sportka AI Analytik PRO", layout="wide")

# --- STYLING ---
st.markdown("""
    <style>
    div.stAlert p { color: #000000 !important; font-weight: bold; }
    [data-testid="stMetricValue"] { color: #FF4B4B; }
    .stMetric { 
        background-color: rgba(255, 75, 75, 0.05); 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid rgba(255, 75, 75, 0.2); 
    }
    .stButton button { width: 100%; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- ZABEZPEČENÍ (Hashování hesel pro veřejnou síť) ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# --- PAMĚŤ STAVU ---
if 'moje_cisla' not in st.session_state:
    st.session_state.moje_cisla = set()
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- DATA ---
def stahnout_aktualni_data():
    url = "https://www.sazka.cz/loterie/historie-cisel?game=sportka&format=csv"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            with open('sportka.csv', 'wb') as f:
                f.write(response.content)
            return True
    except:
        return False
    return False

@st.cache_data(ttl=3600)
def load_data():
    stahnout_aktualni_data()
    try:
        df = pd.read_csv('sportka.csv', sep=';')
        df['tyden_int'] = pd.to_numeric(df['tyden'], errors='coerce')
        df['rok'] = pd.to_numeric(df['rok'], errors='coerce')
        return df
    except:
        return None

data = load_data()

# --- HLAVNÍ LOGIKA ---
if data is not None:
    tah1_cols = ['1. cislo 1. tah', '2. cislo 1. tah', '3. cislo 1. tah', '4. cislo 1. tah', '5. cislo 1. tah', '6. cislo 1. tah']
    dt1_col = 'dodatkove cislo 1. tah'
    tah2_cols = ['1. cislo 2. tah', '2. cislo 2. tah', '3. cislo 2. tah', '4. cislo 2. tah', '5. cislo 2. tah', '6. cislo 2. tah']
    dt2_col = 'dodatkove cislo 2. tah'

    st.title("🚀 Sportka AI Analytik PRO")

    # --- SIDEBAR ---
    st.sidebar.header("🔐 Přihlášení")
    if not st.session_state.logged_in:
        user = st.sidebar.text_input("Uživatel")
        pwd = st.sidebar.text_input("Heslo", type="password")
        if st.sidebar.button("Přihlásit"):
            # Demo logika (v ostrém provozu ověřit proti DB s hashem)
            st.session_state.logged_in = True
            st.rerun()
    else:
        st.sidebar.success(f"Přihlášen jako: Uživatel")
        if st.sidebar.button("Odhlásit"):
            st.session_state.logged_in = False
            st.rerun()

    st.sidebar.divider()
    st.sidebar.header("📅 Plánování")
    vybrane_datum = st.sidebar.date_input("Datum slosování", value=datetime.now())
    _, vybrany_tyden, _ = vybrane_datum.isocalendar()
    st.sidebar.info(f"Analyzujeme **{vybrany_tyden}. týden**")
    
    min_rok, max_rok = int(data['rok'].min()), int(data['rok'].max())
    rozsah_let = st.sidebar.slider("Historie (roky)", min_rok, max_rok, (min_rok, max_rok))

    mask = (data['tyden_int'] == vybrany_tyden) & (data['rok'].between(rozsah_let[0], rozsah_let[1]))
    hist = data[mask]

    # --- ZÁLOŽKY ---
    tab1, tab2, tab3 = st.tabs(["📊 Statistiky", "🔮 Generátor", "⚖️ Interaktivní Tiket"])

    with tab1:
        vsechna = np.concatenate([hist[tah1_cols].values.flatten(), hist[tah2_cols].values.flatten()])
        vsechna = vsechna[~np.isnan(vsechna)].astype(int)
        
        m1, m2 = st.columns([2, 1])
        with m1:
            st.subheader(f"Četnost čísel v {vybrany_tyden}. týdnu")
            if len(vsechna) > 0:
                st.bar_chart(pd.Series(vsechna).value_counts().sort_index(), color="#FF4B4B")
        with m2:
            st.metric("Vzorek tahů", len(hist))
            if len(vsechna) > 0:
                top = pd.Series(vsechna).value_counts().head(6).reset_index()
                top.columns = ['Číslo', 'Výskyty']
                st.table(top)

    with tab2:
        st.subheader("🔮 Generátor historicky nejúspěšnějších kombinací")
        st.write("Generuje tikety z 'horkých' čísel a provádí zpětnou kontrolu v historii.")
        
        if st.button("🚀 GENEROVAT 8 TOP TIKETŮ"):
            if len(vsechna) > 0:
                vsechna_mozna = np.arange(1, 50)
                counts_all = pd.Series(vsechna).value_counts()
                
                # Ošetření Numpy Casting Error pomocí dtype=float
                weights = np.array([counts_all.get(c, 0.1) for c in vsechna_mozna], dtype=float)
                weights = weights**2 
                weights /= weights.sum()

                cols = st.columns(4)
                for i in range(8):
                    tip = sorted(np.random.choice(vsechna_mozna, size=6, replace=False, p=weights))
                    s_tip = set(tip)
                    
                    # Backtesting tiketu
                    res = {"p1": 0, "p2": 0, "p3": 0, "p4": 0, "p5": 0}
                    for _, radek in data.iterrows():
                        for t_cols, d_col in [(tah1_cols, dt1_col), (tah2_cols, dt2_col)]:
                            try:
                                taz = set(radek[t_cols].dropna().astype(int))
                                if not taz: continue
                                shoda = len(s_tip & taz)
                                dod = int(radek[d_col])
                                if shoda == 6: res["p1"] += 1
                                elif shoda == 5 and dod in s_tip: res["p2"] += 1
                                elif shoda == 5: res["p3"] += 1
                                elif shoda == 4: res["p4"] += 1
                                elif shoda == 3: res["p5"] += 1
                            except: continue
                    
                    with cols[i % 4]:
                        st.success(f"**TIKET {i+1}**\n\n{', '.join(map(str, tip))}")
                        st.caption(f"🏆 Celkem výher: **{sum(res.values())}x**")
                        with st.expander("Detail"):
                            st.write(f"1.p: {res['p1']}x | 2.p: {res['p2']}x")
                            st.write(f"3.p: {res['p3']}x | 4.p: {res['p4']}x | 5.p: {res['p5']}x")
                st.balloons()

    with tab3:
        st.subheader("⚖️ Virtuální tiket (7x7)")
        cols = st.columns(7)
        for i in range(1, 50):
            col_idx = (i - 1) % 7
            with cols[col_idx]:
                is_sel = i in st.session_state.moje_cisla
                if st.button(f"{'🎯 ' if is_sel else ''}{i}", key=f"btn_{i}", type="primary" if is_sel else "secondary"):
                    if is_sel: st.session_state.moje_cisla.remove(i)
                    elif len(st.session_state.moje_cisla) < 6: st.session_state.moje_cisla.add(i)
                    st.rerun()

        vyber = sorted(list(st.session_state.moje_cisla))
        c_vypis, c_mazani = st.columns([3, 1])
        c_vypis.write(f"**Vybráno ({len(vyber)}/6):** {', '.join(map(str, vyber))}")
        if c_mazani.button("🗑️ Smazat tiket"):
            st.session_state.moje_cisla = set()
            st.rerun()

        if len(vyber) == 6:
            st.divider()
            vysledky = {"p1": 0, "p2": 0, "p3": 0, "p4": 0, "p5": 0}
            s_cisla = set(vyber)
            for _, radek in data.iterrows():
                for t_cols, d_col in [(tah1_cols, dt1_col), (tah2_cols, dt2_col)]:
                    try:
                        taz = set(radek[t_cols].dropna().astype(int))
                        shoda = len(s_cisla & taz)
                        dod = int(radek[d_col])
                        if shoda == 6: vysledky["p1"] += 1
                        elif shoda == 5 and dod in s_cisla: vysledky["p2"] += 1
                        elif shoda == 5: vysledky["p3"] += 1
                        elif shoda == 4: vysledky["p4"] += 1
                        elif shoda == 3: vysledky["p5"] += 1
                    except: continue
            
            r1, r2, r3, r4, r5 = st.columns(5)
            r1.metric("1. pořadí", vysledky["p1"])
            r2.metric("2. pořadí", vysledky["p2"])
            r3.metric("3. pořadí", vysledky["p3"])
            r4.metric("4. pořadí", vysledky["p4"])
            r5.metric("5. pořadí", vysledky["p5"])
            st.info(f"Celkem výher v historii od r. {min_rok}: **{sum(vysledky.values())}x**")
else:
    st.error("Nepodařilo se načíst data ze serveru Sazka.")
