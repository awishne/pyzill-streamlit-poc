import streamlit as st
import pyzill
import pandas as pd

st.set_page_config(page_title="Pyzill POC", layout="wide")
st.title("🔍 Zillow Rental POC")

# Inputs
loc   = st.text_input("Location (ZIP / city / address)", "60614")
beds  = st.number_input("Min beds", min_value=0, max_value=10, value=1)
baths = st.number_input("Min baths", min_value=0, max_value=10, value=1)

if st.button("Search"):
    with st.spinner("Fetching listings…"):
        # Call pyzill without proxies for light use
        results = pyzill.for_rent(
            1,
            search_value=loc,
            min_beds=beds or None,
            min_bathrooms=baths or None,
            max_beds=None,
            max_bathrooms=None,
            ne_lat=None, ne_long=None,
            sw_lat=None, sw_long=None,
            zoom_value=12,
            proxy_url=None
        )
    if not results:
        st.warning("No results returned—try a different location or fewer filters.")
    else:
        # Show as a table
        df = pd.DataFrame(results)
        st.dataframe(df)
        # And give links
        st.markdown("### Listing URLs")
        for r in results:
            st.write(f"[{r['address']}]({r['detailUrl']}) — {r['price']}")
