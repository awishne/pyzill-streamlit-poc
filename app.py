import streamlit as st
from homeharvest import scrape_property
import pandas as pd
import requests
import math
import urllib.parse

# Haversine formula (if you still want to compute distance client-side)
def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
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
    # 1) Geocode center via Census API (for display/optional filtering)
    with st.spinner("Geocoding location…"):
        try:
            resp = requests.get(
                "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
                params={"address": location,
                        "benchmark": "Public_AR_Census2020",
                        "format": "json"},
                timeout=5
            ).json()
            matches = resp.get("result", {}).get("addressMatches", [])
            if matches:
                c = matches[0]["coordinates"]
                center_lat, center_lon = c["y"], c["x"]
            else:
                center_lat = center_lon = None
        except:
            center_lat = center_lon = None

    # 2) Fetch only rentals within given radius
    with st.spinner("Fetching rental listings…"):
        try:
            props = scrape_property(
                location=location,
                listing_type="for_rent",
                radius=radius,                     # <-- pass radius here
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
        st.warning("No rentals found. Try widening radius or loosening filters.")
    else:
        # 3) Clean numeric fields
        df["beds"]       = pd.to_numeric(df["beds"],       errors="coerce").fillna(0).astype(int)
        df["full_baths"] = pd.to_numeric(df["full_baths"], errors="coerce").fillna(0)
        df["half_baths"] = pd.to_numeric(df["half_baths"], errors="coerce").fillna(0)
        df["baths"]      = df["full_baths"] + df["half_baths"]

        # 4) Filter by beds/baths
        df = df[df["beds"]  >= min_beds]
        df = df[df["baths"] >= min_baths]

        # 5) Display as cards
        st.markdown(f"### {len(df)} Rentals Found within {radius} miles")
        for idx, row in df.iterrows():
            addr     = row.get("street","")
            unit_raw = row.get("unit")
            unit     = unit_raw if pd.notna(unit_raw) else ""
            city     = row.get("city","")
            zipc     = row.get("zip_code","")
            title    = f"{addr} {unit}, {city} {zipc}".strip()
            url      = row.get("property_url","#")

            st.markdown(f"#### [{title}]({url})", unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"💰 **Price:** {row.get('list_price','N/A')}")
            c2.write(f"🛏️ **Beds:** {row['beds']}")
            c3.write(f"🛁 **Baths:** {int(row['baths'])}")
            c4.write(f"📐 **Sqft:** {row.get('sqft','N/A')}")

            a1, a2 = st.columns(2)
            agent    = row.get("agent_name","N/A")
            email    = row.get("agent_email", "")
            office   = row.get("office_name","N/A")
            off_email= row.get("office_email","")

            a1.write(f"👤 **Agent:** {agent}")
            if isinstance(email, str) and email.strip():
                subject = f"Inquiry: {row['beds']}-bed rental at {title}"
                body    = (
                    f"Hi {agent},\n\n"
                    f"I saw your listing at {title} for ${row.get('list_price','')} per month. "
                    f"Would you consider a 1–3 month lease?\n\nThanks,\n[Your Name]"
                )
                mailto = (
                    f"mailto:{email}"
                    f"?subject={urllib.parse.quote(subject)}"
                    f"&body={urllib.parse.quote(body)}"
                )
                a1.markdown(f"[✉️ Email Agent]({mailto})")

            a2.write(f"🏢 **Office:** {office}")
            if isinstance(off_email, str) and off_email.strip():
                a2.markdown(f"[✉️ Email Office](mailto:{off_email})")

            st.markdown("---")
