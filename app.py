import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np
import requests

# --- KONFIGURACE ---
st.set_page_config(page_title="Sportka AI Analytik PRO", layout="wide")

# --- STYLING (Vynucení bílého písma a kontrastu) ---
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
    /* Styl pro tlačítka v mřížce */
    .stButton button { width: 100%; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- PAMĚŤ PRO TIKET ---
if 'moje_cisla' not in st.session_state:
    st.session_state.moje_cisla = set()

# --- AUTOMATICKÁ AKTUALIZACE DAT ---
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
    stahnout_aktualni_data() # Pokus o stažení čerstvých dat
    try:
        df = pd.read_csv('sportka.csv', sep=';')
        df['tyden_int'] = pd.to_numeric(df['tyden'], errors='coerce')
        df['rok'] = pd.to_numeric(df['rok'], errors='coerce')
        return df
    except:
        return None

# --- NAČTENÍ DAT ---
data = load_data()

if data is not None:
    # Definice sloupců
    tah1_cols = ['1. cislo 1. tah', '2. cislo 1. tah', '3. cislo 1. tah', '4. cislo 1. tah', '5. cislo 1. tah', '6. cislo 1. tah']
    dt1_col = 'dodatkove cislo 1. tah'
    tah2_cols = ['1. cislo 2. tah', '2. cislo 2. tah', '3. cislo 2. tah', '4. cislo 2. tah', '5. cislo 2. tah', '6. cislo 2. tah']
    dt2_col = 'dodatkove cislo 2. tah'

    st.title("🚀 Sportka AI Analytik PRO")
    
    # --- SIDEBAR ---
    st.sidebar.header("📅 Plánování")
    vybrane_datum = st.sidebar.date_input("Datum slosování", value=datetime.now())
    _, vybrany_tyden, _ = vybrane_datum.isocalendar()
    
    st.sidebar.info(f"Analyzujeme **{vybrany_tyden}. týden**")
    
    min_rok, max_rok = int(data['rok'].min()), int(data['rok'].max())
    rozsah_let = st.sidebar.slider("Historie (roky)", min_rok, max_rok, (min_rok, max_rok))

    # Filtrace
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
        st.subheader("Generátor na základě historie týdne")
        if st.button("🚀 GENEROVAT 8 TIKETŮ"):
            if len(vsechna) > 0:
                vsechna_mozna = np.arange(1, 50)
                counts_all = pd.Series(vsechna).value_counts(normalize=True)
                weights = np.array([counts_all.get(c, 0.005) for c in vsechna_mozna])
                weights /= weights.sum()

                cols = st.columns(4)
                for i in range(8):
                    tip = sorted(np.random.choice(vsechna_mozna, size=6, replace=False, p=weights))
                    cols[i % 4].success(f"**TIKET {i+1}**\n\n{', '.join(map(str, tip))}")
                st.balloons()

    with tab3:
        st.subheader("⚖️ Virtuální tiket (7x7)")
        st.write("Navolte svých 6 čísel pro kontrolu celé historie:")

        # Mřížka 7x7
        cols = st.columns(7)
        for i in range(1, 50):
            col_idx = (i - 1) % 7
            with cols[col_idx]:
                is_sel = i in st.session_state.moje_cisla
                if st.button(f"{'🎯 ' if is_sel else ''}{i}", key=f"btn_{i}", type="primary" if is_sel else "secondary"):
                    if is_sel:
                        st.session_state.moje_cisla.remove(i)
                    elif len(st.session_state.moje_cisla) < 6:
                        st.session_state.moje_cisla.add(i)
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
                        if not taz: continue
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

    st.error("Nepodařilo se načíst data.")
