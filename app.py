import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Data Charting Tool", layout="wide")

# Password protection
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Indoor Air Quality Monitoring")
    st.subheader("Login Required")
    
    password = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
        if password == "pollution":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    
    st.stop()

st.title("Interactive Data Charting Tool")

# Initialize session state for annotations
if 'annotations' not in st.session_state:
    st.session_state.annotations = []

# Auto-load the data file
DATA_FILE = "attached_assets/73 Chestnut Road - Full Data_1763474740403.xlsx"
TYPICAL_DAY_FILE = "attached_assets/typical_day_averages.xlsx"

try:
    # Read Excel file
    df = pd.read_excel(DATA_FILE)
    
    # Load pre-calculated typical day averages
    try:
        typical_day_df = pd.read_excel(TYPICAL_DAY_FILE)
    except FileNotFoundError:
        typical_day_df = None
        st.warning("Typical day averages file not found. Run preprocess_typical_day.py to generate it.")
    
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
        st.header("Chart Configuration")
        
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
        
        # Annotations toggle
        show_annotations = st.checkbox("Show Annotations", value=True)
        
        # Parameter selection
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        # Filter out Unnamed: 6
        numeric_cols = [col for col in numeric_cols if 'unnamed' not in col.lower()]
        
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
        
        # Add annotations as vertical lines with labels above the chart (if enabled)
        chart_annotations = []
        annotation_shapes = []
        
        if show_annotations:
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
            chart_title = f"Chart of Indoor Air Quality Monitoring at 73 Chestnut Road {date_range} - {', '.join(display_param_names)}"
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
        
        # Data Summary Section (always shows ALL parameters)
        st.header("Data Summary")
        
        # Overall Statistics
        st.subheader("Overall Statistics")
        stats_cols = st.columns(len(numeric_cols))
        
        for idx, param in enumerate(numeric_cols):
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
        
        # Daily Highs and Lows - All Parameters Combined
        if date_col:
            st.subheader("Daily Min/Max/Average - All Parameters")
            
            # Create daily summary
            daily_stats = filtered_df.copy()
            daily_stats['Date'] = daily_stats[date_col].dt.date
            
            # Build combined table with all parameters
            combined_daily = None
            
            for param in numeric_cols:
                # Calculate daily stats for this parameter
                param_daily = daily_stats.groupby('Date')[param].agg(['min', 'max', 'mean']).reset_index()
                param_display = param_display_map[param]
                
                # Rename columns to include parameter name
                param_daily.columns = ['Date', f'{param_display} Min', f'{param_display} Max', f'{param_display} Avg']
                
                # Merge with combined table
                if combined_daily is None:
                    combined_daily = param_daily
                else:
                    combined_daily = combined_daily.merge(param_daily, on='Date', how='outer')
            
            # Format date for display
            combined_daily['Date'] = pd.to_datetime(combined_daily['Date']).dt.strftime('%a %d %b')
            
            # Display the combined table
            st.dataframe(
                combined_daily,
                use_container_width=True,
                hide_index=True
            )
            
            # Add download button for easy export
            csv = combined_daily.to_csv(index=False)
            st.download_button(
                label="Download Daily Stats as CSV",
                data=csv,
                file_name=f"daily_stats_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            st.caption("Tip: You can select and copy all cells from the table above, or download as CSV for easy import into Excel/Google Sheets.")
        
        # Correlation Matrix (always shows ALL parameters except Unnamed: 6)
        # Filter out Unnamed: 6 from correlation matrix
        corr_params = [p for p in numeric_cols if 'unnamed' not in p.lower()]
        
        if len(corr_params) > 1:
            st.subheader("Parameter Correlations")
            
            # Calculate correlation matrix for filtered parameters
            corr_matrix = filtered_df[corr_params].corr()
            
            # Create a copy of the correlation values and modify diagonal to be grey
            corr_values = corr_matrix.values.copy()
            
            # Create custom colorscale data with grey diagonal
            import numpy as np
            z_data = corr_values.copy()
            
            # Create mask for diagonal (will be displayed in grey)
            n = len(corr_values)
            colors = []
            for i in range(n):
                row_colors = []
                for j in range(n):
                    if i == j:
                        # Diagonal - grey
                        row_colors.append('#D3D3D3')
                    else:
                        # Use color based on correlation value
                        val = corr_values[i, j]
                        if val >= 0:
                            # Positive correlation: interpolate from white (0) to red (1)
                            intensity = int(255 * (1 - val))
                            row_colors.append(f'rgb({255}, {intensity}, {intensity})')
                        else:
                            # Negative correlation: interpolate from white (0) to blue (-1)
                            intensity = int(255 * (1 + val))
                            row_colors.append(f'rgb({intensity}, {intensity}, {255})')
                colors.append(row_colors)
            
            # Create correlation heatmap with custom colors
            fig_corr = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=[param_display_map[p] for p in corr_matrix.columns],
                y=[param_display_map[p] for p in corr_matrix.index],
                colorscale='RdBu_r',  # Reversed: Blue for negative, Red for positive
                zmid=0,
                text=corr_matrix.values,
                texttemplate='%{text:.2f}',
                textfont={"size": 12},
                colorbar=dict(title="Correlation"),
                zmin=-1,
                zmax=1,
                customdata=np.arange(n*n).reshape(n, n),
                hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.2f}<extra></extra>'
            ))
            
            # Update to use custom colors for diagonal
            for i in range(n):
                for j in range(n):
                    if i == j:
                        fig_corr.add_shape(
                            type="rect",
                            x0=j-0.5, x1=j+0.5,
                            y0=i-0.5, y1=i+0.5,
                            fillcolor='#D3D3D3',
                            line_width=0,
                            layer='above'
                        )
            
            fig_corr.update_layout(
                title="Correlation Matrix (excluding Unnamed: 6)",
                xaxis_title="",
                yaxis_title="",
                height=400
            )
            
            st.plotly_chart(fig_corr, use_container_width=True)
        
        # Typical Day Pattern - 15-minute intervals averaged across all days (always shows ALL parameters)
        if date_col:
            st.subheader("Typical Day Pattern (15-minute intervals)")
            
            if typical_day_df is not None:
                try:
                    # Extract time labels from the first column
                    time_slot_labels = typical_day_df['Time'].tolist()
                    
                    # Prepare data for ALL parameters (data is already in percentage format)
                    typical_day_data_percent = []
                    param_names = []
                    
                    for param in numeric_cols:
                        if param in typical_day_df.columns:
                            # Data is already stored as percentage of max
                            percent_values = typical_day_df[param].values
                            typical_day_data_percent.append(percent_values)
                            param_names.append(param_display_map[param])
                    
                    # Only display if we have data
                    if typical_day_data_percent and len(typical_day_data_percent) > 0:
                        # Create combined heatmap with all parameters (grey to brown color scale)
                        fig_typical = go.Figure(data=go.Heatmap(
                            z=typical_day_data_percent,
                            x=time_slot_labels,
                            y=param_names,
                            colorscale=[[0, '#E8E8E8'], [0.5, '#A89968'], [1, '#5C4033']],  # Pale grey to brown
                            colorbar=dict(title="% of Range"),
                            hoverongaps=False,
                            hovertemplate='%{y}<br>Time: %{x}<br>Value: %{z:.1f}%<extra></extra>',
                            zmin=0,
                            zmax=100
                        ))
                        
                        # Update layout to show only hourly labels
                        # Calculate hourly ticks based on actual number of time slots
                        num_slots = len(time_slot_labels)
                        hourly_ticks = [i for i in range(0, num_slots, 4)]  # Every 4th slot = hourly
                        hourly_labels = [time_slot_labels[i] for i in hourly_ticks]
                        
                        fig_typical.update_layout(
                            title="Typical Day - Average Pattern Across All Data (06:00-23:45)",
                            xaxis_title="Time of Day",
                            yaxis_title="Parameter",
                            height=max(200, len(numeric_cols) * 60),  # Scale height with number of parameters
                            xaxis=dict(
                                tickmode='array',
                                tickvals=hourly_ticks,
                                ticktext=hourly_labels
                            )
                        )
                        
                        st.plotly_chart(fig_typical, use_container_width=True)
                        
                        st.caption("This heatmap shows typical daily patterns for each parameter. Colors represent percentage (0-100%) between minimum and maximum values for that parameter across the typical day.")
                    else:
                        st.info("No matching parameters found in typical day data.")
                        
                except Exception as e:
                    st.error(f"Error creating typical day pattern: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
            else:
                st.info("Typical day averages not available. Run preprocess_typical_day.py to generate them.")

except FileNotFoundError:
    st.error(f"Data file not found: {DATA_FILE}")
    st.info("Please make sure the data file exists in the attached_assets folder.")
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.write("Please check that the file is a valid Excel file.")
