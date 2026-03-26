import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import numpy as np

st.set_page_config(page_title="Indoor Air Quality - 73 Chestnut Road", layout="wide")

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

# --- Session configuration ---
SESSIONS = {
    "Session 1 (Nov 2025)": {
        "data": "attached_assets/session1/data.xlsx",
        "diary": "attached_assets/session1/diary.xlsx",
        "typical_day": "attached_assets/session1/typical_day_averages.xlsx",
        "date_range": "Nov 11-18, 2025",
    },
    "Session 2 (Mar 2026)": {
        "data": "attached_assets/session2/data.xlsx",
        "diary": "attached_assets/session2/diary.xlsx",
        "typical_day": "attached_assets/session2/typical_day_averages.xlsx",
        "date_range": "Mar 17-23, 2026",
    },
}

# --- Shared helper functions ---

def get_display_name(col_name):
    """Convert column name to display name with appropriate units"""
    col_lower = col_name.lower()
    if 'pidppm' in col_lower:
        return 'VOC (ppm)'
    elif 'co2' in col_lower or col_lower == 'carbondioxide':
        return 'Carbon Dioxide (ppm)'
    elif col_lower == 'carbonmonoxide':
        return 'Carbon Monoxide (ppm)'
    elif col_lower == 'dewpoint':
        return 'Dew Point (°C)'
    elif 'dust' in col_lower or 'pm' in col_lower:
        return 'Dust (μg/m³)'
    elif 'humidity' in col_lower or col_lower in ['rh', 'hum']:
        return 'Humidity (%)'
    elif 'temp' in col_lower:
        return 'Temperature (°C)'
    else:
        return col_name


def get_param_color(param):
    """Assign fixed accessible colors based on parameter type"""
    param_lower = param.lower()
    if 'humidity' in param_lower or param_lower in ['rh', 'hum']:
        return '#28A745'
    elif 'temp' in param_lower:
        return '#DC3545'
    elif 'pidppm' in param_lower or 'voc' in param_lower:
        return '#D4A017'
    elif param_lower == 'carbonmonoxide':
        return '#9B59B6'  # Purple
    elif 'co2' in param_lower or param_lower == 'carbondioxide':
        return '#003D82'
    elif 'dust' in param_lower or 'pm' in param_lower:
        return '#8B4513'
    elif param_lower == 'dewpoint':
        return '#17A2B8'  # Teal
    else:
        return '#6C757D'


def hex_to_rgba(hex_color, alpha=0.3):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {alpha})'


def wrap_text(text, max_chars=15):
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


@st.cache_data
def load_session_data(data_path, diary_path, typical_day_path):
    """Load all data for a session."""
    df = pd.read_excel(data_path)

    # Identify and convert date columns
    date_columns = []
    for col in df.columns:
        if df[col].dtype in ['datetime64[ns]', 'datetime64[us]', 'object']:
            try:
                pd.to_datetime(df[col])
                date_columns.append(col)
            except:
                pass
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Load typical day
    typical_day_df = None
    if os.path.exists(typical_day_path):
        try:
            typical_day_df = pd.read_excel(typical_day_path)
        except:
            pass

    # Load diary annotations
    annotations = []
    if os.path.exists(diary_path):
        try:
            ann_df = pd.read_excel(diary_path)
            if 'Datetime' in ann_df.columns and 'Action' in ann_df.columns:
                ann_df['Datetime'] = pd.to_datetime(ann_df['Datetime'], errors='coerce')
                for _, row in ann_df.iterrows():
                    if pd.notna(row['Datetime']) and pd.notna(row['Action']):
                        annotations.append({
                            'datetime': row['Datetime'].to_pydatetime(),
                            'text': str(row['Action']),
                            'type': 'datetime'
                        })
        except:
            pass

    return df, date_columns, typical_day_df, annotations


def get_numeric_cols(df):
    """Get numeric columns, filtering out unnamed ones."""
    cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    return [c for c in cols if 'unnamed' not in c.lower()]


def render_session_tab(session_key, session_config):
    """Render a full session analysis tab."""
    try:
        df, date_columns, typical_day_df, annotations = load_session_data(
            session_config["data"],
            session_config["diary"],
            session_config["typical_day"],
        )
    except FileNotFoundError:
        st.error(f"Data file not found: {session_config['data']}")
        return
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    # Date column
    if date_columns:
        date_col = date_columns[0]
    else:
        st.warning("No date columns detected.")
        date_col = None

    numeric_cols = get_numeric_cols(df)
    if not numeric_cols:
        st.error("No numeric columns found in the data!")
        return

    param_display_map = {col: get_display_name(col) for col in numeric_cols}
    param_reverse_map = {v: k for k, v in param_display_map.items()}

    # --- Sidebar controls (scoped by session key) ---
    with st.sidebar:
        st.header(f"Chart Settings")

        chart_type = st.selectbox(
            "Chart Type",
            ["Line Chart", "Scatter Plot", "Bar Chart", "Area Chart"],
            key=f"{session_key}_chart_type"
        )

        show_annotations = st.checkbox("Show Annotations", value=True, key=f"{session_key}_annotations")

        display_names = [param_display_map[col] for col in numeric_cols]
        default_display = [param_display_map[col] for col in numeric_cols[:min(3, len(numeric_cols))]]

        selected_display_params = st.multiselect(
            "Select Parameters to Chart",
            display_names,
            default=default_display,
            key=f"{session_key}_params"
        )

        if not selected_display_params:
            st.warning("Please select at least one parameter to chart.")
            st.stop()

        selected_params = [param_reverse_map[d] for d in selected_display_params]

        st.subheader("Axis Configuration")
        y_axis_assignment = {}
        for param in selected_params:
            dn = param_display_map[param]
            axis = st.radio(
                f"{dn} →",
                ["Left Y-axis", "Right Y-axis"],
                key=f"{session_key}_axis_{param}",
                horizontal=True
            )
            y_axis_assignment[param] = "y1" if axis == "Left Y-axis" else "y2"

    # --- Day filtering ---
    if date_col:
        st.header("Select Days")
        unique_dates = sorted(df[date_col].dt.date.unique())
        sk = f"{session_key}_selected_days"
        if sk not in st.session_state:
            st.session_state[sk] = set(unique_dates)

        st.write("Click to toggle days:")
        cols = st.columns(len(unique_dates))
        for idx, day in enumerate(unique_dates):
            with cols[idx]:
                day_str = day.strftime('%a %d')
                is_selected = day in st.session_state[sk]
                checked = st.checkbox(day_str, value=is_selected, key=f"{session_key}_day_{day}")
                if checked and day not in st.session_state[sk]:
                    st.session_state[sk].add(day)
                elif not checked and day in st.session_state[sk]:
                    st.session_state[sk].remove(day)

        if st.session_state[sk]:
            filtered_df = df[df[date_col].dt.date.isin(st.session_state[sk])]
        else:
            filtered_df = pd.DataFrame()
    else:
        filtered_df = df

    # --- Chart ---
    st.header("Chart")

    if filtered_df.empty:
        st.warning("No data in the selected date range!")
        return

    param_colors = {p: get_param_color(p) for p in selected_params}
    fig = go.Figure()

    if date_col:
        x_data = filtered_df[date_col]
        x_title = date_col
    else:
        x_data = filtered_df.index
        x_title = "Row Index"

    for param in selected_params:
        color = param_colors[param]
        display_name = param_display_map[param]

        if (chart_type in ["Line Chart", "Area Chart"]) and date_col:
            plot_df = filtered_df[[date_col, param]].copy()
            plot_df['time_diff'] = plot_df[date_col].diff()
            rows_to_insert = []
            for i in plot_df.index[1:]:
                td = plot_df.loc[i, 'time_diff']
                if pd.notna(td) and td > timedelta(minutes=2):
                    rows_to_insert.append({date_col: plot_df.loc[i, date_col] - timedelta(seconds=1), param: None})
            if rows_to_insert:
                insert_df = pd.DataFrame(rows_to_insert)
                plot_df = pd.concat([plot_df[[date_col, param]], insert_df], ignore_index=True)
                plot_df = plot_df.sort_values(date_col).reset_index(drop=True)
            x_plot = plot_df[date_col]
            y_plot = plot_df[param]
        else:
            x_plot = x_data
            y_plot = filtered_df[param]

        trace_kwargs = dict(name=display_name, yaxis=y_axis_assignment[param])
        if chart_type == "Line Chart":
            trace = go.Scatter(x=x_plot, y=y_plot, mode='lines',
                               line=dict(color=color, width=3), connectgaps=False, **trace_kwargs)
        elif chart_type == "Scatter Plot":
            trace = go.Scatter(x=x_plot, y=y_plot, mode='markers',
                               marker=dict(color=color, size=8), **trace_kwargs)
        elif chart_type == "Bar Chart":
            trace = go.Bar(x=x_plot, y=y_plot, marker=dict(color=color), **trace_kwargs)
        elif chart_type == "Area Chart":
            trace = go.Scatter(x=x_plot, y=y_plot, fill='tozeroy', mode='lines',
                               line=dict(color=color, width=3),
                               fillcolor=hex_to_rgba(color, 0.3), connectgaps=False, **trace_kwargs)
        fig.add_trace(trace)

    # --- Annotations ---
    chart_annotations = []
    annotation_shapes = []

    if show_annotations and annotations:
        visible_annotations = []
        for ann in annotations:
            if ann['type'] == 'datetime' and date_col:
                ann_dt = pd.Timestamp(ann['datetime'])
                sk = f"{session_key}_selected_days"
                if sk in st.session_state:
                    if ann_dt.date() in st.session_state[sk]:
                        visible_annotations.append({'x': ann_dt, 'text': ann['text'], 'datetime': ann_dt})
                else:
                    visible_annotations.append({'x': ann_dt, 'text': ann['text'], 'datetime': ann_dt})

        visible_annotations.sort(key=lambda a: a['x'])

        if date_col and visible_annotations:
            x_range = (filtered_df[date_col].max() - filtered_df[date_col].min()).total_seconds()
            min_spacing_seconds = max(x_range * 0.05, 7200)
        else:
            min_spacing_seconds = None

        rows = []
        for ann in visible_annotations:
            placed = False
            for row in rows:
                overlaps = False
                if date_col and min_spacing_seconds:
                    for existing_x, _ in row:
                        if abs((ann['x'] - existing_x).total_seconds()) < min_spacing_seconds:
                            overlaps = True
                            break
                if not overlaps:
                    row.append((ann['x'], ann))
                    placed = True
                    break
            if not placed:
                rows.append([(ann['x'], ann)])

        row_height = 0.12
        base_y = 1.02
        for row_idx, row in enumerate(rows):
            y_position = base_y + row_idx * row_height
            for x_pos, ann in row:
                annotation_shapes.append(dict(
                    type='line', x0=x_pos, x1=x_pos, y0=0, y1=y_position - 0.01,
                    xref='x', yref='paper',
                    line=dict(color='#666666', width=1, dash='dot')
                ))
                if 'datetime' in ann:
                    wrapped = wrap_text(ann['text'], max_chars=15)
                    dt_str = ann['datetime'].strftime('%d %b %H:%M')
                    label = f"<b>{wrapped}</b><br><span style='font-size:9pt'>{dt_str}</span>"
                else:
                    label = f"<b>{wrap_text(ann['text'], max_chars=15)}</b>"

                chart_annotations.append(dict(
                    x=x_pos, y=y_position, xref='x', yref='paper', text=label,
                    showarrow=False, font=dict(size=11, color='#1a1a1a'),
                    bgcolor='rgba(255, 255, 255, 0.9)', bordercolor='#666666',
                    borderwidth=1, borderpad=4, xanchor='center', align='center'
                ))

    # --- Layout ---
    has_right_axis = any(a == "y2" for a in y_axis_assignment.values())
    display_param_names = [param_display_map[p] for p in selected_params]

    left_params_with_colors = [(param_display_map[p], param_colors[p]) for p in selected_params if y_axis_assignment[p] == "y1"]
    right_params_with_colors = [(param_display_map[p], param_colors[p]) for p in selected_params if y_axis_assignment[p] == "y2"]

    if date_col:
        min_date = filtered_df[date_col].min()
        max_date = filtered_df[date_col].max()
        date_range_str = f"From {min_date.strftime('%d %b %Y')} To {max_date.strftime('%d %b %Y')}"
        chart_title = f"Indoor Air Quality at 73 Chestnut Road {date_range_str} - {', '.join(display_param_names)}"
    else:
        chart_title = f"{chart_type} - {', '.join(display_param_names)}"

    layout_config = {
        'title': {'text': chart_title, 'y': 0.98, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top', 'pad': {'b': 30}},
        'hovermode': 'x unified',
        'annotations': chart_annotations,
        'shapes': annotation_shapes,
        'height': 600,
        'margin': {'t': 100, 'b': 120},
        'legend': {'orientation': 'h', 'yanchor': 'top', 'y': -0.25, 'xanchor': 'center', 'x': 0.5}
    }

    if date_col:
        min_time = filtered_df[date_col].min()
        max_time = filtered_df[date_col].max()
        current = min_time.replace(hour=0, minute=0, second=0, microsecond=0)
        if current < min_time:
            current += timedelta(hours=12)
        tickvals = []
        ticktext = []
        while current <= max_time:
            tickvals.append(current)
            if current.hour == 0:
                ticktext.append(current.strftime('%a<br>%d %b →<br>%H:%M'))
            else:
                ticktext.append('<br><br>' + current.strftime('%H:%M'))
            current += timedelta(hours=12)

        layout_config['xaxis'] = {
            'title': x_title, 'tickvals': tickvals, 'ticktext': ticktext,
            'tickfont': {'color': '#333333'},
            'showgrid': True, 'gridcolor': '#999999', 'gridwidth': 1,
            'dtick': 86400000,
            'minor': {'dtick': 43200000, 'showgrid': True, 'gridcolor': '#e8e8e8', 'gridwidth': 0.5}
        }
    else:
        layout_config['xaxis_title'] = x_title

    if has_right_axis:
        left_title_parts = [f"<span style='color:{c}'>■</span> {n}" for n, c in left_params_with_colors]
        right_title_parts = [f"<span style='color:{c}'>■</span> {n}" for n, c in right_params_with_colors]
        layout_config['yaxis'] = {'title': {'text': ', '.join(left_title_parts) if left_title_parts else "Left Y-axis"}, 'tickfont': {'color': '#333333'}}
        layout_config['yaxis2'] = {'title': {'text': ', '.join(right_title_parts) if right_title_parts else "Right Y-axis"}, 'overlaying': 'y', 'side': 'right', 'tickfont': {'color': '#333333'}}
    else:
        title_parts = [f"<span style='color:{param_colors[p]}'>■</span> {param_display_map[p]}" for p in selected_params]
        layout_config['yaxis'] = {'title': {'text': ', '.join(title_parts)}, 'tickfont': {'color': '#333333'}}

    fig.update_layout(**layout_config)
    st.plotly_chart(fig, use_container_width=True)

    # --- Data Summary ---
    st.header("Data Summary")
    st.subheader("Overall Statistics")
    stats_cols = st.columns(len(numeric_cols))
    for idx, param in enumerate(numeric_cols):
        with stats_cols[idx]:
            dn = param_display_map[param]
            avg_val = filtered_df[param].mean()
            min_val = filtered_df[param].min()
            max_val = filtered_df[param].max()
            st.metric(label=dn, value=f"{avg_val:.2f}", delta=None)
            st.write(f"**Range:** {min_val:.2f} - {max_val:.2f}")

    # Daily stats
    if date_col:
        st.subheader("Daily Min/Max/Average - All Parameters")
        daily_stats = filtered_df.copy()
        daily_stats['Date'] = daily_stats[date_col].dt.date
        combined_daily = None
        for param in numeric_cols:
            param_daily = daily_stats.groupby('Date')[param].agg(['min', 'max', 'mean']).reset_index()
            pd_name = param_display_map[param]
            param_daily.columns = ['Date', f'{pd_name} Min', f'{pd_name} Max', f'{pd_name} Avg']
            if combined_daily is None:
                combined_daily = param_daily
            else:
                combined_daily = combined_daily.merge(param_daily, on='Date', how='outer')
        combined_daily['Date'] = pd.to_datetime(combined_daily['Date']).dt.strftime('%a %d %b')
        st.dataframe(combined_daily, use_container_width=True, hide_index=True)
        csv = combined_daily.to_csv(index=False)
        st.download_button("Download Daily Stats as CSV", data=csv,
                           file_name=f"daily_stats_{session_key}_{datetime.now().strftime('%Y%m%d')}.csv",
                           mime="text/csv", key=f"{session_key}_csv_dl")

    # Correlation matrix
    corr_params = [p for p in numeric_cols if 'unnamed' not in p.lower()]
    if len(corr_params) > 1:
        st.subheader("Parameter Correlations")
        corr_matrix = filtered_df[corr_params].corr()
        n = len(corr_params)
        fig_corr = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=[param_display_map[p] for p in corr_matrix.columns],
            y=[param_display_map[p] for p in corr_matrix.index],
            colorscale='RdBu_r', zmid=0,
            text=corr_matrix.values, texttemplate='%{text:.2f}', textfont={"size": 12},
            colorbar=dict(title="Correlation"), zmin=-1, zmax=1,
            hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.2f}<extra></extra>'
        ))
        for i in range(n):
            fig_corr.add_shape(type="rect", x0=i-0.5, x1=i+0.5, y0=i-0.5, y1=i+0.5,
                               fillcolor='#D3D3D3', line_width=0, layer='above')
        fig_corr.update_layout(title="Correlation Matrix", xaxis_title="", yaxis_title="", height=400)
        st.plotly_chart(fig_corr, use_container_width=True)

    # Typical day pattern
    if date_col and typical_day_df is not None:
        st.subheader("Typical Day Pattern (15-minute intervals)")
        try:
            time_slot_labels = typical_day_df['Time'].tolist()
            typical_data = []
            param_names = []
            for param in numeric_cols:
                if param in typical_day_df.columns:
                    typical_data.append(typical_day_df[param].values)
                    param_names.append(param_display_map[param])

            if typical_data:
                fig_typical = go.Figure(data=go.Heatmap(
                    z=typical_data, x=time_slot_labels, y=param_names,
                    colorscale=[[0, '#E8E8E8'], [0.5, '#A89968'], [1, '#5C4033']],
                    colorbar=dict(title="% of Range"), hoverongaps=False,
                    hovertemplate='%{y}<br>Time: %{x}<br>Value: %{z:.1f}%<extra></extra>',
                    zmin=0, zmax=100
                ))
                num_slots = len(time_slot_labels)
                hourly_ticks = [i for i in range(0, num_slots, 4)]
                hourly_labels = [time_slot_labels[i] for i in hourly_ticks]
                fig_typical.update_layout(
                    title="Typical Day - Average Pattern Across All Data (06:00-23:45)",
                    xaxis_title="Time of Day", yaxis_title="Parameter",
                    height=max(200, len(numeric_cols) * 60),
                    xaxis=dict(tickmode='array', tickvals=hourly_ticks, ticktext=hourly_labels)
                )
                st.plotly_chart(fig_typical, use_container_width=True)
                st.caption("Heatmap shows typical daily patterns. Colors represent percentage (0-100%) between min and max values.")
        except Exception as e:
            st.error(f"Error creating typical day pattern: {e}")


def render_comparison_tab():
    """Render the comparison tab aligning sessions by day-of-week."""
    # Load both sessions
    try:
        df1, date_cols1, _, _ = load_session_data(
            SESSIONS["Session 1 (Nov 2025)"]["data"],
            SESSIONS["Session 1 (Nov 2025)"]["diary"],
            SESSIONS["Session 1 (Nov 2025)"]["typical_day"],
        )
        df2, date_cols2, _, _ = load_session_data(
            SESSIONS["Session 2 (Mar 2026)"]["data"],
            SESSIONS["Session 2 (Mar 2026)"]["diary"],
            SESSIONS["Session 2 (Mar 2026)"]["typical_day"],
        )
    except Exception as e:
        st.error(f"Error loading session data: {e}")
        return

    date_col1 = date_cols1[0] if date_cols1 else None
    date_col2 = date_cols2[0] if date_cols2 else None
    if not date_col1 or not date_col2:
        st.error("Both sessions need date columns for comparison.")
        return

    # Find common parameters (by display name to handle column name differences)
    numeric1 = get_numeric_cols(df1)
    numeric2 = get_numeric_cols(df2)
    common_params = [c for c in numeric1 if c in numeric2]

    if not common_params:
        st.error("No common parameters between the two sessions.")
        return

    param_display_map = {col: get_display_name(col) for col in common_params}

    # Sidebar controls for comparison
    with st.sidebar:
        st.header("Comparison Settings")

        display_names = [param_display_map[c] for c in common_params]
        param_reverse = {v: k for k, v in param_display_map.items()}
        default = [display_names[0]] if display_names else []

        selected_display = st.multiselect(
            "Parameters to Compare",
            display_names,
            default=default,
            key="comparison_params"
        )

        if not selected_display:
            st.warning("Select at least one parameter.")
            st.stop()

        selected = [param_reverse[d] for d in selected_display]

    # Build day-of-week aligned data
    # Session 1: starts Tue Nov 11. Session 2: starts Tue Mar 17.
    # Align by day-of-week name + time of day.
    df1_copy = df1.copy()
    df2_copy = df2.copy()
    df1_copy['_weekday'] = df1_copy[date_col1].dt.dayofweek  # 0=Mon
    df2_copy['_weekday'] = df2_copy[date_col2].dt.dayofweek
    df1_copy['_time'] = df1_copy[date_col1].dt.time
    df2_copy['_time'] = df2_copy[date_col2].dt.time

    # Use a common reference week for x-axis (Mon=2026-01-05 as arbitrary reference)
    ref_monday = pd.Timestamp('2026-01-05')
    df1_copy['_aligned'] = df1_copy.apply(
        lambda r: ref_monday + timedelta(days=int(r['_weekday'])) + timedelta(
            hours=r['_time'].hour, minutes=r['_time'].minute, seconds=r['_time'].second), axis=1)
    df2_copy['_aligned'] = df2_copy.apply(
        lambda r: ref_monday + timedelta(days=int(r['_weekday'])) + timedelta(
            hours=r['_time'].hour, minutes=r['_time'].minute, seconds=r['_time'].second), axis=1)

    df1_copy = df1_copy.sort_values('_aligned')
    df2_copy = df2_copy.sort_values('_aligned')

    # Day filter for comparison
    st.header("Select Days")
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    # Both sessions have data for these weekdays
    s1_weekdays = set(df1_copy['_weekday'].unique())
    s2_weekdays = set(df2_copy['_weekday'].unique())
    common_weekdays = sorted(s1_weekdays & s2_weekdays)

    if 'comparison_selected_days' not in st.session_state:
        st.session_state.comparison_selected_days = set(common_weekdays)

    cols = st.columns(len(common_weekdays))
    for idx, wd in enumerate(common_weekdays):
        with cols[idx]:
            is_sel = wd in st.session_state.comparison_selected_days
            checked = st.checkbox(day_names[wd], value=is_sel, key=f"comp_day_{wd}")
            if checked and wd not in st.session_state.comparison_selected_days:
                st.session_state.comparison_selected_days.add(wd)
            elif not checked and wd in st.session_state.comparison_selected_days:
                st.session_state.comparison_selected_days.remove(wd)

    sel_days = st.session_state.comparison_selected_days
    f1 = df1_copy[df1_copy['_weekday'].isin(sel_days)]
    f2 = df2_copy[df2_copy['_weekday'].isin(sel_days)]

    if f1.empty and f2.empty:
        st.warning("No data for selected days.")
        return

    # --- Comparison chart ---
    st.header("Session Comparison")

    # Distinct colours for each session
    SESSION1_COLOR = '#0072B2'  # Blue
    SESSION2_COLOR = '#D55E00'  # Orange

    def insert_gap_breaks(df_in, x_col, y_col, gap_minutes=2):
        """Insert None values where time gaps exceed threshold to break line."""
        plot_df = df_in[[x_col, y_col]].copy()
        plot_df = plot_df.sort_values(x_col).reset_index(drop=True)
        plot_df['_td'] = plot_df[x_col].diff()
        rows_to_insert = []
        for i in plot_df.index[1:]:
            td = plot_df.loc[i, '_td']
            if pd.notna(td) and td > timedelta(minutes=gap_minutes):
                rows_to_insert.append({x_col: plot_df.loc[i, x_col] - timedelta(seconds=1), y_col: None})
        if rows_to_insert:
            insert_df = pd.DataFrame(rows_to_insert)
            plot_df = pd.concat([plot_df[[x_col, y_col]], insert_df], ignore_index=True)
            plot_df = plot_df.sort_values(x_col).reset_index(drop=True)
        return plot_df[x_col], plot_df[y_col]

    for param in selected:
        dn = param_display_map[param]

        fig = go.Figure()

        # Session 1 - solid blue
        if not f1.empty:
            x_plot, y_plot = insert_gap_breaks(f1, '_aligned', param)
            fig.add_trace(go.Scatter(
                x=x_plot, y=y_plot,
                name=f'Session 1 - {dn}',
                mode='lines', line=dict(color=SESSION1_COLOR, width=2),
                connectgaps=False
            ))

        # Session 2 - solid orange
        if not f2.empty:
            x_plot, y_plot = insert_gap_breaks(f2, '_aligned', param)
            fig.add_trace(go.Scatter(
                x=x_plot, y=y_plot,
                name=f'Session 2 - {dn}',
                mode='lines', line=dict(color=SESSION2_COLOR, width=2),
                connectgaps=False
            ))

        # X-axis: show day names
        tickvals = [ref_monday + timedelta(days=d) for d in range(7)]
        ticktext = [day_names[d] for d in range(7)]

        fig.update_layout(
            title=f'{dn} - Session 1 (Nov 2025) vs Session 2 (Mar 2026)',
            xaxis=dict(
                title='Day of Week',
                tickvals=tickvals,
                ticktext=ticktext,
                showgrid=True, gridcolor='#999999',
            ),
            yaxis=dict(title=dn),
            hovermode='x unified',
            height=450,
            legend=dict(orientation='h', yanchor='top', y=-0.15, xanchor='center', x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- Side-by-side daily stats ---
    st.header("Daily Statistics Comparison")

    for param in selected:
        dn = param_display_map[param]
        st.subheader(dn)

        stats_data = []
        for wd in sorted(sel_days):
            day_name = day_names[wd]
            s1_day = f1[f1['_weekday'] == wd][param].dropna()
            s2_day = f2[f2['_weekday'] == wd][param].dropna()

            row = {'Day': day_name}
            if len(s1_day) > 0:
                row['S1 Min'] = f"{s1_day.min():.1f}"
                row['S1 Avg'] = f"{s1_day.mean():.1f}"
                row['S1 Max'] = f"{s1_day.max():.1f}"
            else:
                row['S1 Min'] = '-'
                row['S1 Avg'] = '-'
                row['S1 Max'] = '-'

            if len(s2_day) > 0:
                row['S2 Min'] = f"{s2_day.min():.1f}"
                row['S2 Avg'] = f"{s2_day.mean():.1f}"
                row['S2 Max'] = f"{s2_day.max():.1f}"
            else:
                row['S2 Min'] = '-'
                row['S2 Avg'] = '-'
                row['S2 Max'] = '-'

            # Change indicator
            if len(s1_day) > 0 and len(s2_day) > 0:
                change = ((s2_day.mean() - s1_day.mean()) / s1_day.mean()) * 100
                row['Change'] = f"{change:+.1f}%"
            else:
                row['Change'] = '-'

            stats_data.append(row)

        st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)


# --- Main app ---
st.title("Indoor Air Quality Monitoring - 73 Chestnut Road")

tab1, tab2, tab3 = st.tabs(["Session 1 (Nov 2025)", "Session 2 (Mar 2026)", "Comparison"])

with tab1:
    render_session_tab("s1", SESSIONS["Session 1 (Nov 2025)"])

with tab2:
    render_session_tab("s2", SESSIONS["Session 2 (Mar 2026)"])

with tab3:
    render_comparison_tab()
