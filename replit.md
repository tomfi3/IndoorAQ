# Overview

This is an interactive data charting tool built with Streamlit that automatically loads a specific Excel data file and creates customizable visualizations using Plotly. The application provides a user-friendly interface for data exploration, chart creation with flexible parameter selection, date filtering, and event annotation capabilities via diary import or manual entry.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture

**Framework**: Streamlit
- **Decision**: Use Streamlit as the primary web framework
- **Rationale**: Streamlit provides rapid development of data applications with minimal boilerplate code, making it ideal for interactive dashboards
- **Key Features**: 
  - Wide layout configuration for better data visualization
  - Session state management for persisting annotations across interactions
  - Sidebar navigation for controls and file upload

## Data Processing

**Library**: Pandas
- **Decision**: Use Pandas for data manipulation and Excel file processing
- **Rationale**: Industry-standard library for tabular data operations with built-in Excel support
- **Key Features**:
  - Automatic date column detection and conversion
  - Support for both .xlsx and .xls file formats
  - Error handling with 'coerce' for robust date parsing

## Visualization

**Library**: Plotly (graph_objects)
- **Decision**: Use Plotly for interactive charting
- **Rationale**: Provides interactive, publication-quality graphs with built-in zoom, pan, and hover capabilities
- **Advantages**: Superior interactivity compared to static plotting libraries, web-ready output

## State Management

**Approach**: Streamlit Session State
- **Decision**: Use Streamlit's built-in session state for managing annotations
- **Rationale**: Maintains user-added annotations across app reruns without requiring external database
- **Structure**: Annotations stored as a list in `st.session_state.annotations`

## File Handling

**Approach**: Auto-load data file with diary file for annotations
- **Decision**: Auto-load specific data file and diary file from attached_assets folder
- **Rationale**: Simplifies workflow for single-dataset use case; admin can edit diary file to manage annotations
- **Data File**: `attached_assets/73 Oldfield Road - Full Data_1763474740403.xlsx` (times adjusted -90 minutes)
- **Diary File**: `attached_assets/diary_1763478604977.xlsx` with Datetime and Action columns (9 entries)

## Annotation System

**Approach**: Always-visible vertical line markers with stacked labels
- **Decision**: Display annotations as vertical dotted lines with labels positioned above the chart
- **Rationale**: User explicitly requested always-visible markers (not just hover tooltips) to clearly mark when events occurred
- **Implementation**: 
  - Red dotted vertical lines span from bottom to top of chart
  - Text labels positioned above chart with white background and red border
  - Labels stagger at three different heights to minimize overlap
  - Annotations persist in session state and can be imported from Excel diary files

# External Dependencies

## Python Libraries

- **streamlit**: Web application framework and UI components
- **pandas**: Data manipulation and Excel file reading (includes openpyxl/xlrd for Excel support)
- **plotly**: Interactive charting and visualization library
- **datetime**: Standard library for date/time handling (used for potential date filtering/manipulation)
- **json**: Standard library for data serialization (likely for annotation export/import features)

## File Format Support

- Excel files (.xlsx, .xls) via pandas' `read_excel()` function

## Notes

- No external database currently implemented
- No external API integrations present
- Application is self-contained with no authentication/authorization system
- All data processing happens client-side within the Streamlit application