import streamlit as st
from homeharvest import scrape_property
import pandas as pd
import requests
import math

# Haversine formula to compute distance in miles
def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

st.set_page_config(page_title="HomeHarvest Rentals — POC", layout="wide")
st.title("🏠 HomeHarvest Rental Listings")

# Sidebar: filters
st.sidebar.header("Search Rentals (Active Only)")
location = st.sidebar.text_input("Location (address / city / ZIP)", "60614")
min_beds = st.sidebar.number_input("Min Beds", min_value=0, max_value=10, value=0)
min_baths = st.sidebar.number_input("Min Baths", min_value=0, max_value=10, value=0)
property_types = st.sidebar.multiselect(
    "Property Type (optional)",
    options=["single_family","multi_family","condos","condo_townhome",
             "townhomes","duplex_triplex","farm","land","mobile"],
    help="Select one or more types"
)
radius = st.sidebar.number_input(
    "Radius (miles)", min_value=0.0, max_value=100.0,
    value=10.0, step=1.0,
    help="Filter by distance from center location"
)
past_days = st.sidebar.number_input("Listed in last (days)", min_value=1, max_value=365, value=30)
limit = st.sidebar.number_input("Max Results", min_value=1, max_value=1000, value=100, step=50)
extra_data = st.sidebar.checkbox("Include Extra Data (e.g. schools)", value=False)

if st.sidebar.button("Search Rentals"):
    # 1) Geocode center via Census API
    with st.spinner("Geocoding location…"):
        try:
            resp = requests.get(
                "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
                params={"address": location, "benchmark": "Public_AR_Census2020", "format": "json"},
                timeout=5
            )
            matches = resp.json().get("result", {}).get("addressMatches", [])
            if matches:
                center = matches[0]["coordinates"]
                center_lat, center_lon = center["y"], center["x"]
            else:
                center_lat = center_lon = None
        except Exception:
            center_lat = center_lon = None

    # 2) Fetch listings (rentals only)
    with st.spinner("Fetching rental listings…"):
        try:
            props = scrape_property(
                location=location,
                listing_type="for_rent",
                property_type=property_types or None,
                past_days=past_days,
                limit=limit,
                proxy=None,
                extra_property_data=extra_data
            )
            df = pd.DataFrame(props)
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            df = pd.DataFrame()

    if df.empty:
        st.warning("No rentals found. Try adjusting filters or expand radius.")
    else:
        # 3) Filter by beds/baths
        df = df[df["beds"] >= min_beds]
        df = df[df["full_baths"].fillna(0) + df["half_baths"].fillna(0) >= min_baths]

        # 4) Filter by radius if geocoded
        if center_lat is not None and "latitude" in df and "longitude" in df:
            df["distance"] = df.apply(
                lambda r: haversine(center_lat, center_lon, r["latitude"], r["longitude"]), axis=1
            )
            df = df[df["distance"] <= radius]

        # 5) Render listings as cards
        st.markdown(f"### {len(df)} Rentals Found — Displaying as list")
        for i, row in df.iterrows():
            addr = row.get("street", "")
            unit = row.get("unit")
            city = row.get("city", "")
            state = row.get("state", "")
            zipc = row.get("zip_code", "")
            link = row.get("property_url")
            st.markdown(f"#### [{addr + (' ' + unit if unit else '')}, {city} {zipc}]({link})")

            cols = st.columns(4)
            cols[0].write(f"**Price:** {row.get('list_price', 'N/A')}")
            cols[1].write(f"**Beds:** {int(row.get('beds',0))}")
            total_baths = int(row.get('full_baths',0) + row.get('half_baths',0))
            cols[2].write(f"**Baths:** {total_baths}")
            cols[3].write(f"**Sqft:** {row.get('sqft', 'N/A')}")

            ag_col, of_col = st.columns(2)
            ag_col.write(f"**Agent:** {row.get('agent_name','N/A')}")
            ag_email = row.get('agent_email') or "N/A"
            ag_col.write(f"**Email:** {ag_email}")
            of_col.write(f"**Office:** {row.get('office_name','N/A')}")
            of_col.write(f"**Office Email:** {row.get('office_email','N/A')}")

            # Email template generator
            btn_key = f"email_{i}"
            if st.button(f"Generate Email to {row.get('agent_name','Agent')}", key=btn_key):
                template = (
                    f"Subject: Inquiry: {int(row.get('beds',0))}-bedroom rental at {addr}, {city}\n\n"
                    f"Hi {row.get('agent_name','')},\n\n"
                    f"I’m reaching out from [Your Company]. I saw your listing at {addr}, {city} for "
                    f"${row.get('list_price','')}. Would you consider a short-term (e.g., 1–3 month) lease?\n\n"
                    f"Please let me know if that’s possible.\n\n"
                    f"Thank you,\n[Your Name]"
                )
                st.text_area("Email Template", template, height=180)

            st.markdown("---")
