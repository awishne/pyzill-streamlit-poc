import streamlit as st
from homeharvest import scrape_property
import pandas as pd
import requests
import math
import urllib.parse

# Haversine formula for distance in miles
def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

st.set_page_config(page_title="Rental Finder POC", layout="wide")
st.title("🏠 Active Rental Listings — POC")

# Sidebar inputs
with st.sidebar:
    st.header("Search Parameters")
    location  = st.text_input("Location (address / city / ZIP)", "60614")
    min_beds  = st.number_input("Min Beds",  min_value=0, max_value=10, value=0)
    min_baths = st.number_input("Min Baths", min_value=0, max_value=10, value=0)
    radius    = st.number_input("Radius (miles)", 0.0, 100.0, 10.0, step=1.0)
    past_days = st.number_input("Listed in last (days)", 1, 365, 30)
    limit     = st.number_input("Max Results", 1, 1000, 100, step=50)
    extra     = st.checkbox("Include Extra Data (e.g. schools)", value=False)
    go        = st.button("Search Rentals")

if go:
    # 1) Geocode via Census API
    with st.spinner("Geocoding your location…"):
        try:
            resp = requests.get(
                "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
                params={
                    "address": location,
                    "benchmark": "Public_AR_Census2020",
                    "format": "json"
                },
                timeout=5
            ).json()
            matches = resp.get("result", {}).get("addressMatches", [])
            if matches:
                center = matches[0]["coordinates"]
                center_lat, center_lon = center["y"], center["x"]
            else:
                center_lat = center_lon = None
        except:
            center_lat = center_lon = None

    # 2) Fetch rentals
    with st.spinner("Fetching rental listings…"):
        try:
            props = scrape_property(
                location=location,
                listing_type="for_rent",
                past_days=past_days,
                limit=limit,
                proxy=None,
                extra_property_data=extra
            )
            df = pd.DataFrame(props)
        except Exception as e:
            st.error(f"Failed to fetch data: {e}")
            df = pd.DataFrame()

    if df.empty:
        st.warning("No rentals found. Try widening your radius or loosening filters.")
    else:
        # 3) Clean numeric fields
        df["beds"]       = pd.to_numeric(df["beds"],       errors="coerce").fillna(0).astype(int)
        df["full_baths"] = pd.to_numeric(df["full_baths"], errors="coerce").fillna(0)
        df["half_baths"] = pd.to_numeric(df["half_baths"], errors="coerce").fillna(0)
        df["baths"]      = df["full_baths"] + df["half_baths"]

        # 4) Filter by beds/baths
        df = df[df["beds"]  >= min_beds]
        df = df[df["baths"] >= min_baths]

        # 5) Filter by radius
        if center_lat and "latitude" in df and "longitude" in df:
            df["distance"] = df.apply(
                lambda r: haversine(center_lat, center_lon, r["latitude"], r["longitude"]),
                axis=1
            )
            df = df[df["distance"] <= radius]

        # 6) Display as cards
        st.markdown(f"### {len(df)} Rentals Found")
        for idx, row in df.iterrows():
            # Title link
            addr = row.get("street", "")
            unit = row.get("unit") or ""
            city = row.get("city", "")
            zipc = row.get("zip_code", "")
            url  = row.get("property_url")
            title = f"{addr} {unit}, {city} {zipc}".strip()
            st.markdown(f"#### [{title}]({url})", unsafe_allow_html=True)

            # Summary stats
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"💰 **Price:** {row.get('list_price','N/A')}")
            c2.write(f"🛏️ **Beds:** {row['beds']}")
            c3.write(f"🛁 **Baths:** {int(row['baths'])}")
            c4.write(f"📐 **Sqft:** {row.get('sqft','N/A')}")

            # Agent info
            a1, a2 = st.columns(2)
            agent = row.get("agent_name","N/A")
            email = row.get("agent_email","")
            office = row.get("office_name","N/A")
            off_email = row.get("office_email","")
            a1.write(f"👤 **Agent:** {agent}")
            if email:
                mailto = (
                    f"mailto:{email}"
                    f"?subject={urllib.parse.quote(f'Inquiry: {row['beds']}-bed rental at {addr}')}"
                    f"&body={urllib.parse.quote('Hi ' + agent + ',\n\nI saw your rental at ' + title + ' for ' + str(row.get('list_price','')) + '. Would you consider a 1–3 month lease?\n\nThanks,\n[Your Name]')}"
                )
                a1.markdown(f"[✉️ Email Agent]({mailto})")
            a2.write(f"🏢 **Office:** {office}")
            if off_email:
                a2.markdown(f"[✉️ Email Office]({urllib.parse.quote(off_email)})")

            st.markdown("---")
