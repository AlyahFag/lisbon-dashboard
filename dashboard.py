import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium import plugins
from streamlit_folium import st_folium
import plotly.express as px
import numpy as np

 
# Page Configuration
 
st.set_page_config(
    page_title="Lisbon Road Accidents 2023",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

 
# Data Loading and Caching
 
@st.cache_data
def load_data():
    """
    Loads, processes, and caches the accident data.
    """
    try:
        # Assumes the CSV is in a 'data' subfolder
        df = pd.read_csv("data/Road_Accidents_Lisbon.csv")
    except FileNotFoundError:
        st.error("Error: The data file 'data/Road_Accidents_Lisbon.csv' was not found.")
        st.info("Please make sure the 'Road_Accidents_Lisbon.csv' file is inside a folder named 'data'.")
        st.stop()
        
      #Feature Engineering 

    # 1. Create a single 'severity' column for easier filtering
    conditions = [
        (df['fatalities_30d'] > 0),
        (df['serious_injuries_30d'] > 0),
        (df['minor_injuries_30d'] > 0)
    ]
    choices = ['Fatal', 'Serious Injury', 'Minor Injury']
    # Use 'No Injury' as default if no victims are recorded
    df['severity'] = np.select(conditions, choices, default='No Injury')

    # 2. Create 'total_victims'
    df['total_victims'] = df['fatalities_30d'] + df['serious_injuries_30d'] + df['minor_injuries_30d']

    # 3. Define correct categorical order for weekdays
    weekday_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ]
    df['weekday'] = pd.Categorical(df['weekday'], categories=weekday_order, ordered=True)
    
    # 4. Define correct categorical order for months (NEW)
    month_order = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    df['month'] = pd.Categorical(df['month'], categories=month_order, ordered=True)
    
    return df

# Load the data
df = load_data()

 
# Sidebar Filters
 
st.sidebar.title("Dashboard Filters")
st.sidebar.markdown("Use the filters below to explore the data.")

# 1. Severity Filter
severity_options = sorted(df['severity'].unique())
selected_severity = st.sidebar.multiselect(
    "Filter by Accident Severity",
    options=severity_options,
    default=severity_options
)

# 2. Hour of Day Filter
hour_range = st.sidebar.slider(
    "Filter by Hour of Day",
    min_value=0,
    max_value=23,
    value=(0, 23)  # Default is all hours
)

# 3. Weekday Filter
weekday_options = df['weekday'].cat.categories
selected_weekdays = st.sidebar.multiselect(
    "Filter by Weekday",
    options=weekday_options,
    default=weekday_options
)

# 4. Month Filter (NEW)
month_options = df['month'].cat.categories
selected_months = st.sidebar.multiselect(
    "Filter by Month",
    options=month_options,
    default=month_options
)


# Data Filtering Logic

# Apply all filters to create the final filtered DataFrame
df_filtered = df[
    (df['severity'].isin(selected_severity)) &
    (df['weekday'].isin(selected_weekdays)) &
    (df['month'].isin(selected_months)) &
    (df['hour'] >= hour_range[0]) &
    (df['hour'] <= hour_range[1])
]

# Stop execution if no data matches the filters
if df_filtered.empty:
    st.warning("No data found for the selected filter combination. Please adjust your filters.")
    st.stop()

 
# Main Page Layout
st.title("🚗 Lisbon Road Accidents Dashboard (2023)")
st.markdown(
    """
    This dashboard provides an interactive analysis of road accidents in Lisbon for the year 2023. 
    Use the filters on the left to explore patterns by **severity**, **time of day**, **weekday**, and **month**.
    """
)

 
# KPI Metrics
 
st.subheader(f"Summary for Selected Filters")

# Calculate KPIs from the *filtered* data
total_accidents = df_filtered.shape[0]
total_fatalities = df_filtered['fatalities_30d'].sum()
total_serious_injuries = df_filtered['serious_injuries_30d'].sum()
total_minor_injuries = df_filtered['minor_injuries_30d'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Accidents", f"{total_accidents:,}")
col2.metric("Total Fatalities", f"{total_fatalities:,}")
col3.metric("Serious Injuries", f"{total_serious_injuries:,}")
col4.metric("Minor Injuries", f"{total_minor_injuries:,}")

st.markdown("---") # Visual separator

 
# Visualizations in Tabs
 
tab1, tab2, tab3 = st.tabs(["🗺️ Geospatial Map", "📊 Time & Severity Analysis", "💡 Trend Heatmap"])

  #Tab 1: Geospatial Map ---
with tab1:
    st.subheader("Accident Location Map")
    st.markdown("This map displays all filtered accidents. Markers are clustered for readability. Click a cluster to zoom in. Markers are colored by severity.")

    # Convert to GeoDataFrame for mapping
    gdf = gpd.GeoDataFrame(
        df_filtered,
        geometry=[Point(xy) for xy in zip(df_filtered["longitude"], df_filtered["latitude"])],
        crs="EPSG:4326"
    )

    # Center map on Lisbon
    center = [gdf["latitude"].mean(), gdf["longitude"].mean()]
    m = folium.Map(location=center, zoom_start=12, tiles="CartoDB Positron")

    # Define a color map for severity
    severity_color_map = {
        'Fatal': 'darkred',
        'Serious Injury': 'red',
        'Minor Injury': 'orange',
        'No Injury': 'lightblue'
    }

    # Add marker clustering (Bonus feature)
    marker_cluster = plugins.MarkerCluster().add_to(m)

    # Add accident markers
    for _, row in gdf.iterrows():
        sev = row['severity']
        color = severity_color_map.get(sev, 'gray') # Default to gray if unknown
        
        # Create a more informative popup
        popup_html = f"""
        <b>ID:</b> {row['id']}<br>
        <b>Severity:</b> {sev}<br>
        <b>Date:</b> {row['day']}-{row['month']}-2023<br>
        <b>Time:</b> {row['hour']}:00, {row['weekday']}<br>
        <b>Total Victims:</b> {int(row['total_victims'])}
        """
        iframe = folium.IFrame(popup_html, width=200, height=130)
        popup = folium.Popup(iframe, max_width=200)

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=popup,
            tooltip=f"{sev} accident (ID {row['id']})"
        ).add_to(marker_cluster) # Add to cluster, not map

    # Show map
    st_folium(m, width="100%", height=500, returned_objects=[])


 # Tab 2: Time & Severity Analysis (CHARTS) 
with tab2:
    st.subheader("Analysis of Accidents by Time and Severity")
    
    col_time_1, col_time_2 = st.columns(2)
    
    # Chart 1: Accidents by Hour of Day
    with col_time_1:
        st.markdown("##### Accidents by Hour of Day")
        hourly_data = df_filtered['hour'].value_counts().sort_index()
        fig_hour = px.bar(
            hourly_data,
            x=hourly_data.index,
            y=hourly_data.values,
            labels={'x': 'Hour of Day (0-23)', 'y': 'Number of Accidents'},
            template="plotly_white"
        )
        fig_hour.update_layout(xaxis=dict(tickmode='linear', dtick=2))
        st.plotly_chart(fig_hour, use_container_width=True)

    # Chart 2: Accidents by Day of Week
    with col_time_2:
        st.markdown("##### Accidents by Day of Week")
        weekday_data = df_filtered['weekday'].value_counts().reindex(weekday_options)
        fig_day = px.bar(
            weekday_data,
            x=weekday_data.index,
            y=weekday_data.values,
            labels={'x': 'Day of Week', 'y': 'Number of Accidents'},
            template="plotly_white"
        )
        st.plotly_chart(fig_day, use_container_width=True)

    # Chart 3: Severity Breakdown (Pie Chart)
    st.markdown("##### Accident Severity Breakdown")
    severity_data = df_filtered['severity'].value_counts()
    fig_sev = px.pie(
        severity_data,
        values=severity_data.values,
        names=severity_data.index,
        color=severity_data.index,
        # Apply the same color map from the Folium chart
        color_discrete_map={
            'Fatal': 'darkred',
            'Serious Injury': 'red',
            'Minor Injury': 'orange',
            'No Injury': 'lightblue'
        },
        template="plotly_white"
    )
    fig_sev.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_sev, use_container_width=True)


  #Tab 3: Heatmap Analysis
with tab3:
    st.subheader("Accident Heatmap: Hour of Day vs. Day of Week")
    st.markdown("""
    This heatmap helps identify high-risk periods. Darker squares show a high 
    concentration of accidents at that specific hour and day, helping to answer:
    * *When do most accidents occur?*
    * *Are workday rush hours (e.g., 8-10h, 17-19h) hotspots?*
    * *Are there weekend-specific patterns (e.g., late nights)?*
    """)
    
    # Create pivot table
    heatmap_data = df_filtered.pivot_table(
        index='weekday',
        columns='hour',
        values='id',
        aggfunc='count'
    ).fillna(0)
    
    # Ensure the index follows the correct weekday order
    heatmap_data = heatmap_data.reindex(weekday_options)
    
    # Create the heatmap
    fig_heatmap = px.imshow(
        heatmap_data,
        labels=dict(x="Hour of Day", y="Day of Week", color="Accident Count"),
        x=heatmap_data.columns,
        y=heatmap_data.index,
        text_auto=False,  # Set to True if you want numbers on each square
        aspect="auto",
        color_continuous_scale="Reds" # Use a Red color scale for danger
    )
    fig_heatmap.update_xaxes(side="bottom", tickmode='linear', dtick=2, title="Hour of Day")
    fig_heatmap.update_layout(
        title="Accident Concentration by Hour and Weekday"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

 
# Footer and Data Notice
 
st.markdown("---")
st.markdown(
    """
    > **Important Notice** > This dataset contains real road accident records from Portugal in 2023, provided by **ANSR (National Road Safety Authority)**.  
    > It is intended **exclusively for educational use within this course**. Redistribution or use for any other purpose is strictly prohibited.
    """
)