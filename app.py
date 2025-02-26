import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from research.zero_study_research import ZeroStudyResearcher
from utils.visualization import Visualizer
from utils.export import DataExporter
import zipfile
import io

# Page config with responsive layout
st.set_page_config(
    page_title="Zero Domain Analysis",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapse sidebar by default on mobile
)

# Custom CSS for better mobile responsiveness
st.markdown("""
<style>
    /* Make content area wider on mobile */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    /* Improve readability of metrics on mobile */
    [data-testid="metric-container"] {
        width: fit-content;
        margin: auto;
    }

    /* Better button visibility on mobile */
    .stButton>button {
        width: 100%;
        margin: 0.5rem 0;
    }

    /* Improve text readability */
    .st-text {
        font-size: 1rem;
    }

    /* Better spacing for expanders */
    .streamlit-expanderHeader {
        font-size: 1rem;
        padding: 0.5rem;
    }

    /* Adjust chart container for mobile */
    [data-testid="stPlotlyChart"] {
        width: 100%;
        min-height: 400px;
    }
</style>
""",
            unsafe_allow_html=True)

# Title and description
st.title("Zero Domain Analysis")
st.markdown("""
This tool visualizes the Zero domain ecosystem, showing relationships between
worlds, domains, and their owners.
""")

try:
    # Initialize researcher if not in session state
    if 'researcher' not in st.session_state:
        st.session_state.researcher = ZeroStudyResearcher()

    # Add refresh button and search box in sidebar
    st.sidebar.header("Controls")

    # Get current data and last refresh time
    data, last_refresh = st.session_state.researcher.load_saved_data()

    # Check if refresh is allowed (more than 24 hours since last refresh)
    now = datetime.now()
    time_since_refresh = now - last_refresh
    refresh_allowed = time_since_refresh > timedelta(days=1)

    # Create refresh button with dynamic state
    if not refresh_allowed:
        hours_until_refresh = 24 - (time_since_refresh.total_seconds() / 3600)
        st.sidebar.warning(
            f"Refresh available in {int(hours_until_refresh)} hours")
        refresh = st.sidebar.button("🔄 Refresh Data", disabled=True)
    else:
        refresh = st.sidebar.button("🔄 Refresh Data")

    # Show last refresh time
    st.sidebar.caption(
        f"Last Refreshed: {last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")

    st.sidebar.markdown("---")
    st.sidebar.header("Search")
    search_term = st.sidebar.text_input("Search domains", "")

    # Add export options in sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("Export Data")
    export_format = st.sidebar.selectbox("Choose format",
                                         ["CSV", "JSON", "Excel"])

    # Add compression option for large datasets
    if data is not None and len(data) > 1000:
        st.sidebar.info("Large dataset detected - compression recommended")
        use_compression = st.sidebar.checkbox("Compress export file",
                                              value=True)
    else:
        use_compression = False

    # Fetch data with loading indicator
    with st.spinner("Loading domain data..." if not refresh else
                    "Fetching fresh data from Reservoir..."):
        if refresh and refresh_allowed:
            try:
                data, last_refresh = st.session_state.researcher.get_nft_data(
                    force_refresh=True)
                if not data:
                    st.error(
                        "No domain data available. This could be due to API rate limits or an invalid API key."
                    )
                    st.info(
                        "Please wait a few minutes and try again, or check your Reservoir API key."
                    )
                    st.stop()
            except Exception as e:
                st.error(f"Error fetching data: {str(e)}")
                st.info(
                    "Please check your Reservoir API key or try again later.")
                st.stop()

    # Convert to DataFrame and validate data
    try:
        df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error processing domain data: {str(e)}")
        st.stop()

    # Apply search filter if term is provided
    if search_term:
        mask = (df['name'].str.contains(search_term, case=False, na=False)
                | df['world'].str.contains(search_term, case=False, na=False)
                | df['domain'].str.contains(search_term, case=False, na=False))
        df = df[mask]

    # Calculate metrics
    total_domains = len(df)
    total_worlds = df['world'].nunique()
    domains_with_members = len(df[df['member_count'] > 0])
    total_subdomains = len(df[df['is_subdomain'] == True])

    # Display metrics in responsive columns
    col1, col2 = st.columns(2)
    with col1:
        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            st.metric("Total Domains", total_domains)
        with metric_col2:
            st.metric("Worlds", total_worlds)
    with col2:
        metric_col3, metric_col4 = st.columns(2)
        with metric_col3:
            st.metric("Domains with Members", domains_with_members)
        with metric_col4:
            st.metric("Subdomains", total_subdomains)

    # Add view toggle with Visualize as default
    view_mode = st.radio("View Mode",
                         ["Visualize", "Member Growth", "Details"],
                         horizontal=True)

    if view_mode == "Visualize":
        # Display network visualization
        st.subheader("Domain Network Visualization")
        min_members = st.slider("Show domains with more than X members",
                                min_value=1,
                                max_value=50,
                                value=20)
        fig = Visualizer.create_network_graph(df, min_members=min_members)
        st.plotly_chart(fig, use_container_width=True)
    elif view_mode == "Member Growth":
        st.subheader("Domain Member Growth Over Time")

        # Get top domains by member count
        top_domains = df.nlargest(10, 'member_count')

        # Allow user to select domains to compare
        selected_domains = st.multiselect(
            "Select domains to compare",
            options=top_domains['name'].tolist(),
            default=top_domains['name'].head(5).tolist(),
            help="Choose up to 5 domains to compare their member growth")

        if selected_domains:
            fig = Visualizer.create_member_growth_chart(df, selected_domains)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(
                "Please select at least one domain to view its growth trend.")
    else:
        # Display domain details
        st.subheader("Domain Details")

        if df.empty:
            if search_term:
                st.info("No domains found matching your search term.")
            else:
                st.warning("No domains found in the data.")
        else:
            # Group by world with better mobile formatting
            for world in sorted(df['world'].unique()):
                world_df = df[df['world'] == world]
                world_members = world_df['member_count'].sum()

                with st.expander(
                        f"🌍 0://{world} (Total Members: {world_members})",
                        expanded=False):
                    # Create container for better mobile layout
                    container = st.container()
                    with container:
                        # Group by root_domain
                        for root_domain in sorted(
                                world_df['root_domain'].unique()):
                            root_df = world_df[world_df['root_domain'] ==
                                               root_domain]
                            root_members = root_df['member_count'].sum()

                            # Display root domain with 0:// only if it's the same as world
                            root_display = root_domain if '.' in root_domain else f"0://{root_domain}"
                            st.markdown(f"### 🌐 {root_display}")
                            st.markdown(f"**Members:** {root_members}")

                            # Show domains in a more compact format
                            for _, row in root_df.iterrows():
                                with st.container():
                                    owner_text = f"`{row['owner']}`" if row[
                                        'owner'] != "Unknown" else "Unknown"
                                    if row['is_subdomain']:
                                        st.markdown(f"""
                                        - **{row['domain']}** ({row['name']})
                                          - Owner: {owner_text}
                                          - Members: {row['member_count']}
                                        """)
                                    else:
                                        st.markdown(f"""
                                        - Owner: {owner_text}
                                        - Members: {row['member_count']}
                                        """)

    # Show raw data option with horizontal scroll on mobile
    if st.checkbox("Show Raw Data"):
        st.markdown("""
            <style>
            .dataframe-container {
                overflow-x: auto;
                max-width: 100%;
                margin: 1rem 0;
            }
            </style>
        """,
                    unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="dataframe-container">',
                        unsafe_allow_html=True)
            st.dataframe(df)
            st.markdown('</div>', unsafe_allow_html=True)

    # Add export button
    if not df.empty:
        compression = 'zip' if use_compression else None
        filename = DataExporter.get_filename(
            format=export_format.lower(),
            filter_term=search_term if search_term else None,
            min_members=min_members if view_mode == "Visualize" else None,
            compression=compression)

        if export_format == "CSV":
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            export_data = csv_buffer.getvalue()
            mime = "text/csv"
            if compression:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w') as zf:
                    zf.writestr(filename, export_data)
                export_data = zip_buffer.getvalue()
                mime = "application/zip"

        elif export_format == "JSON":
            json_buffer = io.StringIO()
            df.to_json(json_buffer, orient='records')
            export_data = json_buffer.getvalue()
            mime = "application/json"
            if compression:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w') as zf:
                    zf.writestr(filename, export_data)
                export_data = zip_buffer.getvalue()
                mime = "application/zip"

        else:  # Excel
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False, engine='openpyxl')
            export_data = excel_buffer.getvalue()
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if compression:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w') as zf:
                    zf.writestr(filename, export_data)
                export_data = zip_buffer.getvalue()
                mime = "application/zip"

        st.sidebar.download_button(
            label=f"📥 Download {export_format}" +
            (" (Compressed)" if compression else ""),
            data=export_data,
            file_name=filename,
            mime=mime,
            help=f"Download the current data as {export_format}" +
            (" (ZIP compressed)" if compression else ""))

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.write("Please check the logs for more details.")
