import streamlit as st
import pyzill
import pandas as pd
import requests
from json.decoder import JSONDecodeError

st.set_page_config(page_title="Pyzill POC", layout="wide")
st.title("🔍 Zillow Rental POC with Census Geocoding")

loc   = st.text_input("Location (full address / ZIP)", "60614")
beds  = st.number_input("Min beds",   min_value=0, max_value=10, value=1)
baths = st.number_input("Min baths",  min_value=0, max_value=10, value=1)

if st.button("Search"):
    # 1) Try Census geocoding
    with st.spinner("Geocoding via Census API…"):
        try:
            resp = requests.get(
                "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
                params={
                  "address": loc,
                  "benchmark": "Public_AR_Census2020",
                  "format": "json"
                },
                timeout=5
            )
            geo_json = resp.json()
            matches = geo_json["result"]["addressMatches"]
        except Exception:
            matches = []

    if not matches:
        st.error("❌ Census geocoding failed. Please enter a bounding box manually below.")
        # Show manual lat/lon inputs
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Center latitude", value=41.85, format="%.5f")
            delta = st.number_input("± degrees for box", value=0.02, format="%.5f")
        with col2:
            lon = st.number_input("Center longitude", value=-87.75, format="%.5f")
        ne_lat, ne_long = lat + delta, lon + delta
        sw_lat, sw_long = lat - delta, lon - delta
    else:
        # Take the first match
        coord = matches[0]["coordinates"]
        lat, lon = coord["y"], coord["x"]
        delta = 0.02
        ne_lat, ne_long = lat + delta, lon + delta
        sw_lat, sw_long = lat - delta, lon - delta

    # 2) Fetch from Zillow
    with st.spinner("Fetching Zillow rentals…"):
        try:
            results = pyzill.for_rent(
                1,
                search_value=loc or None,
                is_entire_place=True,
                is_room=False,
                min_beds=beds or None,
                max_beds=None,
                min_bathrooms=baths or None,
                max_bathrooms=None,
                min_price=None,
                max_price=None,
                ne_lat=ne_lat,
                ne_long=ne_long,
                sw_lat=sw_lat,
                sw_long=sw_long,
                zoom_value=12,
                proxy_url=None
            )
            if not results:
                st.warning("No listings found—try loosening your filters or increasing the box size.")
            else:
                df = pd.DataFrame(results)
                st.dataframe(df)
        except JSONDecodeError:
            st.error("❌ Zillow returned invalid JSON—consider adding a proxy.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")
