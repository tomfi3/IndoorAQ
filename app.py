import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

st.set_page_config(page_title="Data Charting Tool", layout="wide")

st.title("📊 Interactive Data Charting Tool")

# Initialize session state for annotations
if 'annotations' not in st.session_state:
    st.session_state.annotations = []

# Sidebar for file upload and main controls
with st.sidebar:
    st.header("📁 Data Upload")
    uploaded_file = st.file_uploader("Upload Excel file", type=['xlsx', 'xls'])
    
    if uploaded_file:
        st.success("File uploaded successfully!")

# Main content
if uploaded_file is not None:
    try:
        # Read Excel file
        df = pd.read_excel(uploaded_file)
        
        # Try to identify date columns
        date_columns = []
        for col in df.columns:
            if df[col].dtype in ['datetime64[ns]', 'object']:
                try:
                    pd.to_datetime(df[col])
                    date_columns.append(col)
                except:
                    pass
        
        # Convert date columns to datetime
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Display data preview
        with st.expander("📋 Data Preview", expanded=False):
            st.dataframe(df.head(20), use_container_width=True)
            st.write(f"Total rows: {len(df)} | Total columns: {len(df.columns)}")
        
        # Sidebar controls
        with st.sidebar:
            st.header("⚙️ Chart Configuration")
            
            # Select date column
            if date_columns:
                date_col = st.selectbox("Select Date Column", date_columns)
            else:
                st.warning("No date columns detected. Using row index instead.")
                date_col = None
            
            # Chart type
            chart_type = st.selectbox(
                "Chart Type",
                ["Line Chart", "Scatter Plot", "Bar Chart", "Area Chart"]
            )
            
            # Parameter selection
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            
            if not numeric_cols:
                st.error("No numeric columns found in the data!")
                st.stop()
            
            selected_params = st.multiselect(
                "Select Parameters to Chart",
                numeric_cols,
                default=numeric_cols[:min(3, len(numeric_cols))]
            )
            
            if not selected_params:
                st.warning("Please select at least one parameter to chart.")
                st.stop()
            
            # Axis configuration
            st.subheader("Axis Configuration")
            y_axis_assignment = {}
            
            for param in selected_params:
                axis = st.radio(
                    f"{param} →",
                    ["Left Y-axis", "Right Y-axis"],
                    key=f"axis_{param}",
                    horizontal=True
                )
                y_axis_assignment[param] = "y1" if axis == "Left Y-axis" else "y2"
        
        # Date filtering
        if date_col:
            st.header("📅 Date Filtering")
            
            col1, col2 = st.columns(2)
            
            with col1:
                min_date = df[date_col].min()
                max_date = df[date_col].max()
                
                start_date = st.date_input(
                    "Start Date",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date
                )
            
            with col2:
                end_date = st.date_input(
                    "End Date",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date
                )
            
            # Quick filters
            st.write("Quick Filters:")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("Last 7 Days"):
                    start_date = max_date - timedelta(days=7)
                    end_date = max_date
            
            with col2:
                if st.button("Last 30 Days"):
                    start_date = max_date - timedelta(days=30)
                    end_date = max_date
            
            with col3:
                if st.button("Last 90 Days"):
                    start_date = max_date - timedelta(days=90)
                    end_date = max_date
            
            with col4:
                if st.button("All Data"):
                    start_date = min_date
                    end_date = max_date
            
            # Filter dataframe
            filtered_df = df[
                (df[date_col] >= pd.Timestamp(start_date)) & 
                (df[date_col] <= pd.Timestamp(end_date))
            ]
        else:
            filtered_df = df
        
        # Annotation/Diary System
        st.header("📝 Event Annotations")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if date_col:
                annotation_date = st.date_input(
                    "Event Date",
                    value=datetime.now(),
                    key="annotation_date"
                )
                annotation_time = st.time_input("Event Time (optional)", key="annotation_time")
            else:
                annotation_index = st.number_input(
                    "Row Index",
                    min_value=0,
                    max_value=len(df)-1,
                    value=0
                )
            
            annotation_text = st.text_input("Event Description", key="annotation_text")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Add Annotation", use_container_width=True):
                    if annotation_text:
                        if date_col:
                            annotation_datetime = datetime.combine(annotation_date, annotation_time)
                            st.session_state.annotations.append({
                                'datetime': annotation_datetime,
                                'text': annotation_text,
                                'type': 'datetime'
                            })
                        else:
                            st.session_state.annotations.append({
                                'index': annotation_index,
                                'text': annotation_text,
                                'type': 'index'
                            })
                        st.success("Annotation added!")
                        st.rerun()
            
            with col_b:
                if st.button("Clear All Annotations", use_container_width=True):
                    st.session_state.annotations = []
                    st.rerun()
        
        with col2:
            st.write(f"**Total Annotations:** {len(st.session_state.annotations)}")
            
            if st.session_state.annotations:
                with st.expander("View All Annotations"):
                    for i, ann in enumerate(st.session_state.annotations):
                        if ann['type'] == 'datetime':
                            st.write(f"{i+1}. {ann['datetime'].strftime('%Y-%m-%d %H:%M')} - {ann['text']}")
                        else:
                            st.write(f"{i+1}. Row {ann['index']} - {ann['text']}")
        
        # Create the chart
        st.header("📈 Chart")
        
        if filtered_df.empty:
            st.warning("No data in the selected date range!")
        else:
            fig = go.Figure()
            
            # Determine x-axis
            if date_col:
                x_data = filtered_df[date_col]
                x_title = date_col
            else:
                x_data = filtered_df.index
                x_title = "Row Index"
            
            # Add traces for each selected parameter
            for param in selected_params:
                if chart_type == "Line Chart":
                    trace = go.Scatter(
                        x=x_data,
                        y=filtered_df[param],
                        name=param,
                        mode='lines+markers',
                        yaxis=y_axis_assignment[param]
                    )
                elif chart_type == "Scatter Plot":
                    trace = go.Scatter(
                        x=x_data,
                        y=filtered_df[param],
                        name=param,
                        mode='markers',
                        yaxis=y_axis_assignment[param]
                    )
                elif chart_type == "Bar Chart":
                    trace = go.Bar(
                        x=x_data,
                        y=filtered_df[param],
                        name=param,
                        yaxis=y_axis_assignment[param]
                    )
                elif chart_type == "Area Chart":
                    trace = go.Scatter(
                        x=x_data,
                        y=filtered_df[param],
                        name=param,
                        fill='tozeroy',
                        yaxis=y_axis_assignment[param]
                    )
                
                fig.add_trace(trace)
            
            # Add annotations to the chart
            chart_annotations = []
            for ann in st.session_state.annotations:
                if ann['type'] == 'datetime' and date_col:
                    ann_dt = pd.Timestamp(ann['datetime'])
                    if start_date <= ann_dt.date() <= end_date:
                        chart_annotations.append(
                            dict(
                                x=ann_dt,
                                y=0,
                                xref='x',
                                yref='paper',
                                text=ann['text'],
                                showarrow=True,
                                arrowhead=2,
                                arrowsize=1,
                                arrowwidth=2,
                                arrowcolor='red',
                                ax=0,
                                ay=-40
                            )
                        )
                elif ann['type'] == 'index' and not date_col:
                    if ann['index'] in filtered_df.index:
                        chart_annotations.append(
                            dict(
                                x=ann['index'],
                                y=0,
                                xref='x',
                                yref='paper',
                                text=ann['text'],
                                showarrow=True,
                                arrowhead=2,
                                arrowsize=1,
                                arrowwidth=2,
                                arrowcolor='red',
                                ax=0,
                                ay=-40
                            )
                        )
            
            # Configure layout with dual y-axes if needed
            has_right_axis = any(axis == "y2" for axis in y_axis_assignment.values())
            
            layout_config = dict(
                title=f"{chart_type} - {', '.join(selected_params)}",
                xaxis_title=x_title,
                hovermode='x unified',
                annotations=chart_annotations,
                height=600
            )
            
            if has_right_axis:
                layout_config['yaxis'] = dict(title="Left Y-axis")
                layout_config['yaxis2'] = dict(
                    title="Right Y-axis",
                    overlaying='y',
                    side='right'
                )
            else:
                layout_config['yaxis_title'] = "Value"
            
            fig.update_layout(**layout_config)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Export options
            st.header("💾 Export Chart")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                export_format = st.selectbox("Export Format", ["PNG", "JPG", "SVG", "PDF"])
            
            with col2:
                export_width = st.number_input("Width (px)", min_value=400, max_value=4000, value=1200)
            
            with col3:
                export_height = st.number_input("Height (px)", min_value=300, max_value=3000, value=600)
            
            filename = st.text_input("Filename", value="chart_export")
            
            if st.button("📥 Download Chart", use_container_width=True):
                try:
                    img_bytes = fig.to_image(
                        format=export_format.lower(),
                        width=export_width,
                        height=export_height
                    )
                    
                    st.download_button(
                        label=f"💾 Save {export_format}",
                        data=img_bytes,
                        file_name=f"{filename}.{export_format.lower()}",
                        mime=f"image/{export_format.lower()}",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
    
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        st.write("Please make sure the file is a valid Excel file.")

else:
    st.info("👈 Please upload an Excel file from the sidebar to get started.")
    
    st.markdown("""
    ### Features:
    - 📊 **Multiple chart types**: Line, Scatter, Bar, Area
    - 🎯 **Multi-parameter selection**: Choose which columns to visualize
    - ⚖️ **Dual Y-axis support**: Assign parameters to left or right axis
    - 📅 **Date filtering**: Filter data by date range with quick presets
    - 📝 **Event annotations**: Add diary entries to mark important events
    - 💾 **Export charts**: Download as PNG, JPG, SVG, or PDF
    
    Simply upload your Excel file to begin!
    """)
