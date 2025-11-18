import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Data Charting Tool", layout="wide")

st.title("📊 Interactive Data Charting Tool")

# Initialize session state for annotations
if 'annotations' not in st.session_state:
    st.session_state.annotations = []

# Auto-load the data file
DATA_FILE = "attached_assets/73 Oldfield Road - Full Data_1763474740403.xlsx"

try:
    # Read Excel file
    df = pd.read_excel(DATA_FILE)
    
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
    
    # Create display names with units for parameters
    def get_display_name(col_name):
        """Convert column name to display name with appropriate units"""
        col_lower = col_name.lower()
        
        if 'pidppm' in col_lower:
            return 'VOC (ppm)'
        elif 'co2' in col_lower:
            return 'CO2 (ppm)'
        elif 'dust' in col_lower or 'pm' in col_lower:
            return 'Dust (μg/m³)'
        elif 'humidity' in col_lower or col_lower in ['rh', 'hum']:
            return 'Humidity (%)'
        elif 'temp' in col_lower:
            return 'Temperature (°C)'
        else:
            return col_name
    
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
        
        # Create mapping of display names to original column names
        param_display_map = {col: get_display_name(col) for col in numeric_cols}
        param_reverse_map = {v: k for k, v in param_display_map.items()}
        
        # Show display names in multiselect
        display_names = [param_display_map[col] for col in numeric_cols]
        default_display = [param_display_map[col] for col in numeric_cols[:min(3, len(numeric_cols))]]
        
        selected_display_params = st.multiselect(
            "Select Parameters to Chart",
            display_names,
            default=default_display
        )
        
        if not selected_display_params:
            st.warning("Please select at least one parameter to chart.")
            st.stop()
        
        # Convert back to original column names
        selected_params = [param_reverse_map[disp] for disp in selected_display_params]
        
        # Axis configuration
        st.subheader("Axis Configuration")
        y_axis_assignment = {}
        
        for param in selected_params:
            display_name = param_display_map[param]
            axis = st.radio(
                f"{display_name} →",
                ["Left Y-axis", "Right Y-axis"],
                key=f"axis_{param}",
                horizontal=True
            )
            y_axis_assignment[param] = "y1" if axis == "Left Y-axis" else "y2"
    
    # Date filtering
    if date_col:
        st.header("📅 Date Filtering")
        
        col1, col2 = st.columns(2)
        
        min_date = df[date_col].min().date()
        max_date = df[date_col].max().date()
        
        with col1:
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
                st.rerun()
        
        with col2:
            if st.button("Last 30 Days"):
                start_date = max_date - timedelta(days=30)
                end_date = max_date
                st.rerun()
        
        with col3:
            if st.button("Last 90 Days"):
                start_date = max_date - timedelta(days=90)
                end_date = max_date
                st.rerun()
        
        with col4:
            if st.button("All Data"):
                start_date = min_date
                end_date = max_date
                st.rerun()
        
        # Filter dataframe
        filtered_df = df[
            (df[date_col].dt.date >= start_date) & 
            (df[date_col].dt.date <= end_date)
        ]
    else:
        filtered_df = df
        start_date = None
        end_date = None
    
    # Load annotations from admin-editable file
    ANNOTATIONS_FILE = "attached_assets/diary_1763476206890.xlsx"
    if os.path.exists(ANNOTATIONS_FILE):
        try:
            annotations_df = pd.read_excel(ANNOTATIONS_FILE)
            if 'Datetime' in annotations_df.columns and 'Action' in annotations_df.columns:
                annotations_df['Datetime'] = pd.to_datetime(annotations_df['Datetime'], errors='coerce')
                
                # Clear and reload annotations from file
                st.session_state.annotations = []
                for _, row in annotations_df.iterrows():
                    if pd.notna(row['Datetime']) and pd.notna(row['Action']):
                        st.session_state.annotations.append({
                            'datetime': row['Datetime'].to_pydatetime(),
                            'text': str(row['Action']),
                            'type': 'datetime'
                        })
        except Exception as e:
            st.warning(f"Could not load annotations: {str(e)}")
    
    # Create the chart
    st.header("📈 Chart")
    
    if filtered_df.empty:
        st.warning("No data in the selected date range!")
    else:
        # Define accessible high-contrast color palette
        accessible_colors = [
            '#0072B2',  # Blue
            '#D55E00',  # Orange
            '#009E73',  # Green
            '#CC79A7',  # Pink
            '#F0E442',  # Yellow
            '#56B4E9',  # Light Blue
            '#E69F00',  # Dark Orange
            '#000000'   # Black
        ]
        
        def hex_to_rgba(hex_color, alpha=0.3):
            """Convert hex color to rgba with specified alpha"""
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return f'rgba({r}, {g}, {b}, {alpha})'
        
        fig = go.Figure()
        
        # Determine x-axis
        if date_col:
            x_data = filtered_df[date_col]
            x_title = date_col
        else:
            x_data = filtered_df.index
            x_title = "Row Index"
        
        # Add traces for each selected parameter
        for idx, param in enumerate(selected_params):
            color = accessible_colors[idx % len(accessible_colors)]
            display_name = param_display_map[param]
            
            # For line and area charts with time data, break lines on gaps > 2 minutes
            if (chart_type in ["Line Chart", "Area Chart"]) and date_col:
                # Create a copy of the data to insert breaks
                plot_df = filtered_df[[date_col, param]].copy()
                
                # Calculate time differences
                plot_df['time_diff'] = plot_df[date_col].diff()
                
                # Insert None rows where gap > 2 minutes
                rows_to_insert = []
                for idx in plot_df.index[1:]:
                    time_diff = plot_df.loc[idx, 'time_diff']
                    if pd.notna(time_diff) and time_diff > timedelta(minutes=2):
                        # Insert a row with None to break the line
                        rows_to_insert.append({
                            date_col: plot_df.loc[idx, date_col] - timedelta(seconds=1),
                            param: None
                        })
                
                if rows_to_insert:
                    # Create DataFrame from new rows and combine
                    insert_df = pd.DataFrame(rows_to_insert)
                    plot_df = pd.concat([plot_df[[date_col, param]], insert_df], ignore_index=True)
                    plot_df = plot_df.sort_values(date_col).reset_index(drop=True)
                
                x_plot = plot_df[date_col]
                y_plot = plot_df[param]
            else:
                x_plot = x_data
                y_plot = filtered_df[param]
            
            if chart_type == "Line Chart":
                trace = go.Scatter(
                    x=x_plot,
                    y=y_plot,
                    name=display_name,
                    mode='lines',
                    line=dict(color=color, width=3),
                    yaxis=y_axis_assignment[param],
                    connectgaps=False
                )
            elif chart_type == "Scatter Plot":
                trace = go.Scatter(
                    x=x_plot,
                    y=y_plot,
                    name=display_name,
                    mode='markers',
                    marker=dict(color=color, size=8),
                    yaxis=y_axis_assignment[param]
                )
            elif chart_type == "Bar Chart":
                trace = go.Bar(
                    x=x_plot,
                    y=y_plot,
                    name=display_name,
                    marker=dict(color=color),
                    yaxis=y_axis_assignment[param]
                )
            elif chart_type == "Area Chart":
                trace = go.Scatter(
                    x=x_plot,
                    y=y_plot,
                    name=display_name,
                    fill='tozeroy',
                    mode='lines',
                    line=dict(color=color, width=3),
                    fillcolor=hex_to_rgba(color, 0.3),
                    yaxis=y_axis_assignment[param],
                    connectgaps=False
                )
            
            fig.add_trace(trace)
        
        # Add annotations as vertical lines with labels above the chart
        chart_annotations = []
        annotation_shapes = []
        
        # Sort annotations by x position to space them vertically
        visible_annotations = []
        for ann in st.session_state.annotations:
            if ann['type'] == 'datetime' and date_col:
                ann_dt = pd.Timestamp(ann['datetime'])
                if start_date and end_date:
                    if start_date <= ann_dt.date() <= end_date:
                        visible_annotations.append({
                            'x': ann_dt,
                            'text': ann['text'],
                            'datetime': ann_dt
                        })
                else:
                    visible_annotations.append({
                        'x': ann_dt,
                        'text': ann['text'],
                        'datetime': ann_dt
                    })
            elif ann['type'] == 'index' and not date_col:
                if ann['index'] in filtered_df.index:
                    visible_annotations.append({
                        'x': ann['index'],
                        'text': ann['text'],
                        'index': ann['index']
                    })
        
        # Sort by x position
        visible_annotations.sort(key=lambda a: a['x'])
        
        # Stagger annotation heights to avoid overlap
        for i, ann in enumerate(visible_annotations):
            y_position = 1.02 + (i % 3) * 0.08
            
            # Add vertical line from top to bottom of plot
            annotation_shapes.append(
                dict(
                    type='line',
                    x0=ann['x'],
                    x1=ann['x'],
                    y0=0,
                    y1=1,
                    xref='x',
                    yref='paper',
                    line=dict(
                        color='#666666',
                        width=1,
                        dash='dot'
                    )
                )
            )
            
            # Format datetime for display
            if 'datetime' in ann:
                datetime_str = ann['datetime'].strftime('%Y-%m-%d %H:%M')
                label_text = f"{ann['text']}<br><sub>{datetime_str}</sub>"
            else:
                label_text = ann['text']
            
            # Add text annotation above the chart
            chart_annotations.append(
                dict(
                    x=ann['x'],
                    y=y_position,
                    xref='x',
                    yref='paper',
                    text=label_text,
                    showarrow=False,
                    font=dict(
                        size=10,
                        color='#333333'
                    ),
                    bgcolor='rgba(255, 255, 255, 0.9)',
                    bordercolor='#666666',
                    borderwidth=1,
                    borderpad=4,
                    xanchor='center'
                )
            )
        
        # Configure layout with dual y-axes if needed
        has_right_axis = any(axis == "y2" for axis in y_axis_assignment.values())
        
        # Create title with display names
        display_param_names = [param_display_map[p] for p in selected_params]
        
        # Group parameters by axis
        left_params = [param_display_map[p] for p in selected_params if y_axis_assignment[p] == "y1"]
        right_params = [param_display_map[p] for p in selected_params if y_axis_assignment[p] == "y2"]
        
        layout_config = {
            'title': f"{chart_type} - {', '.join(display_param_names)}",
            'xaxis_title': x_title,
            'hovermode': 'x unified',
            'annotations': chart_annotations,
            'shapes': annotation_shapes,
            'height': 600
        }
        
        if has_right_axis:
            # Create y-axis titles with parameter names and units
            left_title = ', '.join(left_params) if left_params else "Left Y-axis"
            right_title = ', '.join(right_params) if right_params else "Right Y-axis"
            
            layout_config['yaxis'] = {'title': left_title}
            layout_config['yaxis2'] = {
                'title': right_title,
                'overlaying': 'y',
                'side': 'right'
            }
        else:
            # Single axis - show all parameters
            layout_config['yaxis_title'] = ', '.join(display_param_names)
        
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

except FileNotFoundError:
    st.error(f"Data file not found: {DATA_FILE}")
    st.info("Please make sure the data file exists in the attached_assets folder.")
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.write("Please check that the file is a valid Excel file.")
