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
        elif 'co2' in col_lower or 'carbon' in col_lower:
            return 'Carbon Dioxide (ppm)'
        elif 'dust' in col_lower or 'pm' in col_lower:
            return 'Dust (μg/m³)'
        elif 'humidity' in col_lower or col_lower in ['rh', 'hum']:
            return 'Humidity (%)'
        elif 'temp' in col_lower:
            return 'Temperature (°C)'
        else:
            return col_name
    
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
    
    # Date filtering with day buttons
    if date_col:
        st.header("📅 Select Days")
        
        # Get unique dates from the data
        unique_dates = sorted(df[date_col].dt.date.unique())
        
        # Initialize session state for selected days (all selected by default)
        if 'selected_days' not in st.session_state:
            st.session_state.selected_days = set(unique_dates)
        
        # Create day buttons in a row
        st.write("Click to toggle days:")
        
        # Use custom CSS to make checkboxes look like buttons
        st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"] {
            gap: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create columns for each day
        cols = st.columns(len(unique_dates))
        
        for idx, day in enumerate(unique_dates):
            with cols[idx]:
                # Create checkbox styled as button
                day_str = day.strftime('%a %d')
                is_selected = day in st.session_state.selected_days
                
                # Use checkbox with custom styling
                checked = st.checkbox(
                    day_str,
                    value=is_selected,
                    key=f"day_{day}"
                )
                
                # Update session state
                if checked and day not in st.session_state.selected_days:
                    st.session_state.selected_days.add(day)
                elif not checked and day in st.session_state.selected_days:
                    st.session_state.selected_days.remove(day)
        
        # Filter dataframe based on selected days
        if st.session_state.selected_days:
            filtered_df = df[df[date_col].dt.date.isin(st.session_state.selected_days)]
        else:
            filtered_df = pd.DataFrame()  # Empty if no days selected
    else:
        filtered_df = df
    
    # Load annotations from admin-editable file
    ANNOTATIONS_FILE = "attached_assets/diary_1763478604977.xlsx"
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
        
        # Assign fixed accessible colors based on parameter type
        def get_param_color(param):
            """Assign fixed accessible colors based on parameter type"""
            param_lower = param.lower()
            if 'humidity' in param_lower or param_lower in ['rh', 'hum']:
                return '#28A745'  # Green
            elif 'temp' in param_lower:
                return '#DC3545'  # Red
            elif 'pidppm' in param_lower or 'voc' in param_lower:
                return '#D4A017'  # Mustard/Gold
            elif 'co2' in param_lower or 'carbon' in param_lower:
                return '#003D82'  # Dark Blue
            elif 'dust' in param_lower or 'pm' in param_lower:
                return '#8B4513'  # Brown
            else:
                return '#6C757D'  # Gray for unknown parameters
        
        # Create mapping of parameters to colors
        param_colors = {param: get_param_color(param) for param in selected_params}
        
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
            color = param_colors[param]
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
                # Check if annotation date is in selected days
                if 'selected_days' in st.session_state:
                    if ann_dt.date() in st.session_state.selected_days:
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
        
        # Intelligent row assignment to avoid overlap
        # Calculate approximate width of annotations based on text length
        if date_col and len(visible_annotations) > 0:
            # Get the x-axis range to calculate relative spacing
            x_range = (filtered_df[date_col].max() - filtered_df[date_col].min()).total_seconds()
            # Estimate annotation width as percentage of visible range (roughly 5% of range or 2 hours, whichever is larger)
            min_spacing_seconds = max(x_range * 0.05, 7200)  # 2 hours minimum
        else:
            min_spacing_seconds = None
        
        # Assign each annotation to a row
        rows = []  # Each row contains list of (x_position, annotation) tuples
        
        for ann in visible_annotations:
            # Try to find a row where this annotation fits
            placed = False
            for row in rows:
                # Check if annotation overlaps with any annotation in this row
                overlaps = False
                if date_col and min_spacing_seconds:
                    for existing_x, _ in row:
                        time_diff = abs((ann['x'] - existing_x).total_seconds())
                        if time_diff < min_spacing_seconds:
                            overlaps = True
                            break
                else:
                    # For non-datetime, use simple spacing
                    for existing_x, _ in row:
                        if abs(ann['x'] - existing_x) < 50:  # Index-based spacing
                            overlaps = True
                            break
                
                if not overlaps:
                    row.append((ann['x'], ann))
                    placed = True
                    break
            
            if not placed:
                # Create new row
                rows.append([(ann['x'], ann)])
        
        # Now render annotations based on their row assignment
        row_height = 0.12  # Vertical spacing between rows
        base_y = 1.02  # Starting position above chart
        
        for row_idx, row in enumerate(rows):
            y_position = base_y + row_idx * row_height
            
            for x_pos, ann in row:
                # Add vertical line from annotation down to chart
                annotation_shapes.append(
                    dict(
                        type='line',
                        x0=x_pos,
                        x1=x_pos,
                        y0=0,
                        y1=y_position - 0.01,  # Stop just below the annotation
                        xref='x',
                        yref='paper',
                        line=dict(
                            color='#666666',
                            width=1,
                            dash='dot'
                        )
                    )
                )
                
                # Wrap text to prevent horizontal overflow
                def wrap_text(text, max_chars=15):
                    """Wrap text to multiple lines at word boundaries"""
                    words = text.split()
                    lines = []
                    current_line = []
                    current_length = 0
                    
                    for word in words:
                        word_length = len(word)
                        if current_length + word_length + len(current_line) <= max_chars:
                            current_line.append(word)
                            current_length += word_length
                        else:
                            if current_line:
                                lines.append(' '.join(current_line))
                            current_line = [word]
                            current_length = word_length
                    
                    if current_line:
                        lines.append(' '.join(current_line))
                    
                    return '<br>'.join(lines)
                
                # Format datetime for display with wrapped text
                if 'datetime' in ann:
                    wrapped_action = wrap_text(ann['text'], max_chars=15)
                    datetime_str = ann['datetime'].strftime('%d %b %H:%M')
                    label_text = f"<b>{wrapped_action}</b><br><span style='font-size:9pt'>{datetime_str}</span>"
                else:
                    wrapped_action = wrap_text(ann['text'], max_chars=15)
                    label_text = f"<b>{wrapped_action}</b>"
                
                # Add text annotation above the chart
                chart_annotations.append(
                    dict(
                        x=x_pos,
                        y=y_position,
                        xref='x',
                        yref='paper',
                        text=label_text,
                        showarrow=False,
                        font=dict(
                            size=11,
                            color='#1a1a1a'
                        ),
                        bgcolor='rgba(255, 255, 255, 0.9)',
                        bordercolor='#666666',
                        borderwidth=1,
                        borderpad=4,
                        xanchor='center',
                        align='center'
                    )
                )
        
        # Configure layout with dual y-axes if needed
        has_right_axis = any(axis == "y2" for axis in y_axis_assignment.values())
        
        # Create title with display names
        display_param_names = [param_display_map[p] for p in selected_params]
        
        # Group parameters by axis with colors
        left_params_with_colors = [(param_display_map[p], param_colors[p]) 
                                   for p in selected_params if y_axis_assignment[p] == "y1"]
        right_params_with_colors = [(param_display_map[p], param_colors[p]) 
                                    for p in selected_params if y_axis_assignment[p] == "y2"]
        
        # Create dynamic title with date range
        if date_col:
            min_date = filtered_df[date_col].min()
            max_date = filtered_df[date_col].max()
            date_range = f"From {min_date.strftime('%d %b %Y')} To {max_date.strftime('%d %b %Y')}"
            chart_title = f"Chart of Indoor Air Quality Monitoring at 73 Oldfield Road {date_range} - {', '.join(display_param_names)}"
        else:
            chart_title = f"{chart_type} - {', '.join(display_param_names)}"
        
        layout_config = {
            'title': {
                'text': chart_title,
                'y': 0.98,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'pad': {'b': 30}
            },
            'hovermode': 'x unified',
            'annotations': chart_annotations,
            'shapes': annotation_shapes,
            'height': 600,
            'margin': {'t': 100, 'b': 120},
            'legend': {
                'orientation': 'h',
                'yanchor': 'top',
                'y': -0.25,
                'xanchor': 'center',
                'x': 0.5
            }
        }
        
        # Configure x-axis with time formatting and grid lines
        if date_col:
            # Generate custom tick values and labels
            # Show full date at midnight, just time at noon
            min_time = filtered_df[date_col].min()
            max_time = filtered_df[date_col].max()
            
            # Create tick values every 12 hours
            from datetime import datetime, timedelta
            current = min_time.replace(hour=0, minute=0, second=0, microsecond=0)
            if current < min_time:
                current += timedelta(hours=12)
            
            tickvals = []
            ticktext = []
            
            while current <= max_time:
                tickvals.append(current)
                if current.hour == 0:
                    # Midnight: show day name, date with arrow, and time
                    ticktext.append(current.strftime('%a<br>%d %b →<br>%H:%M'))
                else:
                    # Noon or other times: show time on third line to align with midnight
                    ticktext.append('<br><br>' + current.strftime('%H:%M'))
                current += timedelta(hours=12)
            
            layout_config['xaxis'] = {
                'title': x_title,
                'tickvals': tickvals,
                'ticktext': ticktext,
                'tickfont': {'color': '#333333'},
                'showgrid': True,
                'gridcolor': '#999999',
                'gridwidth': 1,
                'dtick': 86400000,  # Major ticks every 24 hours (for gridlines at midnight)
                'minor': {
                    'dtick': 43200000,  # Minor ticks every 12 hours (lighter gridlines at noon)
                    'showgrid': True,
                    'gridcolor': '#e8e8e8',
                    'gridwidth': 0.5
                }
            }
        else:
            layout_config['xaxis_title'] = x_title
        
        if has_right_axis:
            # Create y-axis titles with colored squares
            left_title_parts = [f"<span style='color:{color}'>■</span> {name}" 
                               for name, color in left_params_with_colors]
            right_title_parts = [f"<span style='color:{color}'>■</span> {name}" 
                                for name, color in right_params_with_colors]
            
            left_title = ', '.join(left_title_parts) if left_title_parts else "Left Y-axis"
            right_title = ', '.join(right_title_parts) if right_title_parts else "Right Y-axis"
            
            layout_config['yaxis'] = {
                'title': {'text': left_title},
                'tickfont': {'color': '#333333'}
            }
            layout_config['yaxis2'] = {
                'title': {'text': right_title},
                'overlaying': 'y',
                'side': 'right',
                'tickfont': {'color': '#333333'}
            }
        else:
            # Single axis - show all parameters with colored squares
            title_parts = [f"<span style='color:{param_colors[p]}'>■</span> {param_display_map[p]}" 
                          for p in selected_params]
            layout_config['yaxis'] = {
                'title': {'text': ', '.join(title_parts)},
                'tickfont': {'color': '#333333'}
            }
        
        fig.update_layout(**layout_config)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Data Summary Section
        st.header("📊 Data Summary")
        
        # Overall Statistics
        st.subheader("Overall Statistics")
        stats_cols = st.columns(len(selected_params))
        
        for idx, param in enumerate(selected_params):
            with stats_cols[idx]:
                display_name = param_display_map[param]
                avg_val = filtered_df[param].mean()
                min_val = filtered_df[param].min()
                max_val = filtered_df[param].max()
                
                st.metric(
                    label=display_name,
                    value=f"{avg_val:.2f}",
                    delta=None
                )
                st.write(f"**Range:** {min_val:.2f} - {max_val:.2f}")
        
        # Daily Highs and Lows
        if date_col:
            st.subheader("Daily Highs and Lows")
            
            # Create daily summary
            daily_stats = filtered_df.copy()
            daily_stats['Date'] = daily_stats[date_col].dt.date
            
            for param in selected_params:
                st.write(f"**{param_display_map[param]}**")
                
                daily_summary = daily_stats.groupby('Date')[param].agg(['min', 'max', 'mean']).reset_index()
                daily_summary.columns = ['Date', 'Low', 'High', 'Average']
                daily_summary['Date'] = pd.to_datetime(daily_summary['Date']).dt.strftime('%a %d %b')
                
                st.dataframe(
                    daily_summary,
                    use_container_width=True,
                    hide_index=True
                )
        
        # Correlation Matrix
        if len(selected_params) > 1:
            st.subheader("Parameter Correlations")
            
            # Calculate correlation matrix
            corr_matrix = filtered_df[selected_params].corr()
            
            # Create correlation heatmap
            fig_corr = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=[param_display_map[p] for p in corr_matrix.columns],
                y=[param_display_map[p] for p in corr_matrix.index],
                colorscale='RdBu',
                zmid=0,
                text=corr_matrix.values,
                texttemplate='%{text:.2f}',
                textfont={"size": 12},
                colorbar=dict(title="Correlation")
            ))
            
            fig_corr.update_layout(
                title="Correlation Matrix",
                xaxis_title="",
                yaxis_title="",
                height=400
            )
            
            st.plotly_chart(fig_corr, use_container_width=True)
        
        # Time-based Heatmaps
        if date_col:
            st.subheader("Time-based Heatmaps")
            
            for param in selected_params:
                display_name = param_display_map[param]
                
                # Create hourly data
                hourly_data = filtered_df.copy()
                hourly_data['Hour'] = hourly_data[date_col].dt.hour
                hourly_data['Date'] = hourly_data[date_col].dt.date
                
                # Pivot to create heatmap data
                heatmap_data = hourly_data.pivot_table(
                    values=param,
                    index='Hour',
                    columns='Date',
                    aggfunc='mean'
                )
                
                # Format column names
                heatmap_data.columns = [col.strftime('%a %d') for col in heatmap_data.columns]
                
                # Create heatmap
                fig_heat = go.Figure(data=go.Heatmap(
                    z=heatmap_data.values,
                    x=heatmap_data.columns,
                    y=heatmap_data.index,
                    colorscale='Viridis',
                    colorbar=dict(title=display_name),
                    hoverongaps=False
                ))
                
                fig_heat.update_layout(
                    title=f"{display_name} by Hour and Day",
                    xaxis_title="Day",
                    yaxis_title="Hour of Day",
                    height=400
                )
                
                st.plotly_chart(fig_heat, use_container_width=True)
        
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
