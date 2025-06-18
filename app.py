import streamlit as st
import pandas as pd
import requests, math, re
from io import BytesIO
from homeharvest import scrape_property

# ——— Helpers ———
def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8
    φ1,φ2 = math.radians(lat1), math.radians(lat2)
    dφ, dλ = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

def geocode(address):
    resp = requests.get(
        "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
        params={"address": address, "benchmark":"Public_AR_Census2020","format":"json"},
        timeout=5
    ).json().get("result",{}).get("addressMatches",[])
    if resp:
        c = resp[0]["coordinates"]
        return c["y"], c["x"]
    return None, None

def extract_zip(address):
    m = re.search(r"\b\d{5}\b", address)
    return m.group(0) if m else address

# ——— Streamlit UI ———
st.set_page_config(layout="wide")
st.title("🏠 Rental Search & Select POC")

with st.sidebar:
    st.header("Search Parameters")
    raw_address = st.text_input("Enter full address", "8891 Crestview Dr, Frisco, TX 75034")
    min_beds     = st.number_input("Min Beds",  0, 10, 1)
    min_baths    = st.number_input("Min Baths", 0, 10, 1)
    radius       = st.number_input("Radius (miles)", 1.0, 100.0, 10.0)
    past_days    = st.number_input("Listed in last (days)", 1, 365, 360)
    limit        = st.number_input("Max Results (ZIP-wide)", 10, 1000, 200)
    extra_data   = st.checkbox("Include Extra Data", value=False)
    if st.button("🔍 Search Rentals"):
        # 1) Geocode
        center_lat, center_lon = geocode(raw_address)
        if not center_lat:
            st.error("Could not geocode that address.")
            st.stop()

        # 2) Scrape entire ZIP/city market
        search_loc = extract_zip(raw_address)
        with st.spinner("Fetching listings…"):
            props = scrape_property(
                location=search_loc,
                listing_type="for_rent",
                past_days=past_days,
                limit=limit,
                proxy=None,
                extra_property_data=extra_data
            )
        df = pd.DataFrame(props)
        if df.empty:
            st.warning("No rentals returned for that area.")
            st.stop()

        # 3) Clean & filter
        df["beds"]       = pd.to_numeric(df["beds"], errors="coerce").fillna(0).astype(int)
        df["full_baths"] = pd.to_numeric(df["full_baths"], errors="coerce").fillna(0)
        df["half_baths"] = pd.to_numeric(df["half_baths"], errors="coerce").fillna(0)
        df["baths"]      = df["full_baths"] + df["half_baths"]
        df = df[(df["beds"]>=min_beds) & (df["baths"]>=min_baths)]

        if {"latitude","longitude"} <= set(df.columns):
            df["distance"] = df.apply(
                lambda r: haversine(center_lat, center_lon, r["latitude"], r["longitude"]), axis=1
            )
            df = df[df["distance"]<=radius].sort_values("distance")

        st.session_state.df = df.reset_index(drop=True)

# 4) Display & select
if "df" in st.session_state:
    df = st.session_state.df
    st.markdown(f"### {len(df)} Options Within {radius} miles")
    selections = []
    for idx, row in df.iterrows():
        cols = st.columns([1,4,1,1,1,2])
        select = cols[0].checkbox("", key=f"sel_{idx}")
        if select:
            selections.append(idx)
        cols[1].markdown(f"**[{row['street']}, {row['city']} {row['zip_code']}]({row['property_url']})**")
        cols[2].write(f"{row['beds']} bd")
        cols[3].write(f"{int(row['baths'])} ba")
        cols[4].write(f"${row['list_price']:,}")
        cols[5].write(f"{row.get('distance',0):.1f} mi")

    if selections:
        out = df.loc[selections, ["street","city","zip_code","property_url","list_price","beds","baths","distance","agent_email"]]
        buf = BytesIO()
        out.to_excel(buf, index=False, sheet_name="Queue")
        buf.seek(0)
        st.download_button("📥 Download Selected for Outreach", buf, "OutreachQueue.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Check the box next to each listing you want to contact.")

