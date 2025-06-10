import re as _re
from typing import BinaryIO
from ..utils import wildcard_expansion as _wildcard_expansion
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
import xlsxwriter
import pandas as _pd
from pandas.api.types import is_scalar
import numpy as _np
import xlsxwriter.utility as _xlu


# def file_formatting(
#     file_name: str,
#     buffer: BinaryIO,
#     column_settings: dict = {},
#     max_row_height: int = 60,
#     **kwargs
#     ):
#     """
#     Format a .xlsx file using openpyxl.

#     :param file_name: The name of the file to save the formatted data to.
#     :param column_settings: A dictionary of column settings, where keys are column names and values are dictionaries of formatting options.
#     :param buffer: A BytesIO buffer containing the Excel file to format.
#     :param max_row_height: The maximum height of rows in the Excel file.
#     :param kwargs: Additional formatting options.
#     """
#     # (A) Semantic color map for optional header fill
#     COLOR_MAP = {
#         "red":    "FFCC6666",
#         "green":  "FF66A066",
#         "orange": "FFFF9900",
#         "blue":   "FF6699FF",
#         "yellow": "FFE6B800",
#         "purple": "FF9966CC",
#         "gray":   "FFBFBFBF",
#     }

#     def parse_fill_color(color_str):
#         """Convert a semantic color name or a hex string into an ARGB color code."""
#         color_str = color_str.strip().lower()
#         if color_str in COLOR_MAP:
#             return COLOR_MAP[color_str]

#         color_str = color_str.lstrip('#')
#         if len(color_str) == 6:
#             color_str = "FF" + color_str
#         elif len(color_str) == 8:
#             pass
#         else:
#             raise ValueError(f"Invalid color code: '{color_str}'")
#         return color_str.upper()

#     universal_settings_list = ['banding', 'table_style'] # Settings that are associated with the entire table, not just columns, rows, or cells
#     default_settings = {k: v for k, v in kwargs.items() if k not in universal_settings_list}

#     # Load the workbook from the buffer
#     wb = load_workbook(buffer)
#     ws = wb.worksheets[0] # Currently only allowing files with one worksheet

#     columns = [cell.value for cell in ws[ws.min_row]]

#     # Split inputs on comma, but not on escaped commas
#     split_settings = {}
#     for key, value in column_settings.items():
#         # If the key contains an unescaped comma, we want to split it
#         if ',' in key:
#             # Split on unescaped commas
#             parts = _re.split(r'(?<!\\),', key)
#             # Clean up escaped commas
#             parts = [p.replace('\\,', ',').strip() for p in parts]
#             if len(parts) > 1:
#                 for part in parts:
#                     split_settings[part] = value
#             else:
#                 split_settings[parts[0]] = value
#         else:
#             split_settings[key] = value

#     column_settings = split_settings

#     wild_card_columns = [col for col in column_settings.keys() if col.endswith('*')]

#     if wild_card_columns:
#         for col in wild_card_columns:
#             columns_to_expand = _wildcard_expansion(
#                             all_columns=columns,
#                             selected_columns=[col]
#                         )
#             for other_col in columns_to_expand:
#                 column_settings[other_col]= column_settings[col]

#     # Handle columns that are missing from column_settings
#     unspecified_columns = [cell.value for cell in ws[1] if cell.value not in column_settings.keys()]

#     # Build default column settings to be applied to every column not specified
#     column_settings['default'] = default_settings

#     for col in unspecified_columns:
#         if 'default' in column_settings.keys():
#             column_settings[col] = column_settings['default']
#         # else:
#         #     column_settings[col] = {'width': 30, 'header_fill_color': 'blue'} # Currently seems to not be doing anything, leaving commented out for now

#     # Delete the default key from column_settings since it has already been applied to the unspecified columns
#     if 'default' in column_settings.keys(): del column_settings['default']

#     min_row, max_row = ws.min_row, ws.max_row
#     min_col, max_col = ws.min_column, ws.max_column

#     # Set a table name based off sheet name, replace spaces and non alphanumeric characters
#     table_name = f"Table_{ws.title.replace(' ', '_')}"
#     table_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in table_name)
#     if table_name[0].isdigit():
#         table_name = f"_{table_name}"

#     # Build out table reference (the cell range for the table)
#     first_cell = f"{get_column_letter(min_col)}{min_row}"
#     last_cell = f"{get_column_letter(max_col)}{max_row}"
#     table_ref = f"{first_cell}:{last_cell}"

#     tab = Table(displayName=table_name, ref=table_ref) # Named tab to avoid confusion with the table object

#     # Should allow users to set any of these in the future
#     table_style = kwargs.get('table_style', 'TableStyleMedium9') # Default to TableStyleMedium9
#     tab.tableStyleInfo = TableStyleInfo(
#             name= table_style,
#             showFirstColumn=False,
#             showLastColumn=False,
#             showRowStripes=True,
#             showColumnStripes=False
#         )
#     ws.add_table(tab)

#     # Unpack general font data
#     font_name = kwargs.pop('font', 'Calibri')
#     font_size = kwargs.pop('font_size', 11)
#     font_color = kwargs.pop('font_color', 'FF000000')
#     bold = kwargs.pop('bold', False)
#     italicize = kwargs.pop('italic', False)
#     underline = kwargs.pop('underline', None)

#     # Set cell alignment
#     if 'alignment' in column_settings.keys():
#         alignment = column_settings.pop('alignment')
#         alignment = Alignment(horizontal=alignment.get('horizontal', 'left'),
#                               vertical=alignment.get('vertical', 'top'),
#                               wrap_text=alignment.get('wrap_text', True))
#     else:
#         alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)

#     # Styling for all cells
#     for row_cells in ws.iter_rows(min_row=min_row, max_row=max_row,
#                                     min_col=min_col, max_col=max_col):

#         for cell in row_cells:
#             cell.alignment = alignment
#             cell.font = Font(
#                 name=font_name,
#                 size=font_size,
#                 color=font_color,
#                 bold=bold,
#                 italic=italicize,
#                 underline=underline
#             )

#     # Identify header row & build a column map
#     header_row = list(ws.iter_rows(
#         min_row=min_row, max_row=min_row,
#         min_col=min_col, max_col=max_col
#     ))[0]

#     # Build column map to set header specific formatting
#     column_map = {}
#     for idx, header_cell in enumerate(header_row, start=min_col):
#         header_text = header_cell.value if header_cell.value else ""
#         column_map[header_text] = (idx, get_column_letter(idx))

#     # Column-specific settings
#     for col_name, settings in column_settings.items():
#         if col_name in column_map:
#             col_index, col_letter = column_map[col_name]

#             # Column width
#             ws.column_dimensions[col_letter].width = settings.pop("width", 20)

#             for cell_tuple in ws.iter_rows(
#                     min_row=min_row, # Add 1 if not wanting to include header
#                     max_row=max_row,
#                     min_col=col_index,
#                     max_col=col_index
#                 ):
#                 cell_obj = cell_tuple[0]

#                 # Alignment
#                 if 'alignment' in settings.keys():
#                     column_alignment = settings.get('alignment')
#                     curr_align = cell_obj.alignment
#                     cell_obj.alignment = Alignment(
#                         horizontal=column_alignment.get('horizontal', 'left'),
#                         vertical=column_alignment.get('vertical', 'top'),
#                         wrap_text=column_alignment.get('wrap_text', True),
#                         text_rotation=curr_align.text_rotation,
#                         shrink_to_fit=curr_align.shrink_to_fit,
#                         indent=curr_align.indent
#                     )

#                 # Font
#                 curr_font = cell_obj.font
#                 cell_obj.font = Font(
#                     name=settings.get('font', curr_font.name),
#                     size=settings.get('font_size', curr_font.size),
#                     color=settings.get('font_color',curr_font.color),
#                     bold=settings.get('bold', curr_font.bold),
#                     italic=settings.get('italic', curr_font.italic),
#                     underline=settings.get('underline', curr_font.underline),
#                     vertAlign=curr_font.vertAlign, # Possible values: ‘superscript’, ‘baseline’, ‘subscript’
#                     strike=curr_font.strike
#                 )

#                 # Number format (if numeric)
#                 if "number_format" in settings: # cell_obj.number_format allows for General, Text, etc.
#                     if isinstance(cell_obj.value, (int, float)):
#                         cell_obj.number_format = settings["number_format"]

#                 # If 'hyperlink' is True, convert the cell's text into a hyperlink (prepended with 'https://' if needed).
#                 if settings.get("hyperlink", False):
#                     if cell_obj.value:
#                         # Keep the display text the same as the original cell value
#                         display_text = str(cell_obj.value).strip()

#                         # Determine the actual hyperlink target
#                         if display_text.lower().startswith("http://") or display_text.lower().startswith("https://"): # Necessary to avoid a non trusted link pop up
#                             hyperlink_target = display_text
#                         else:
#                             hyperlink_target = "https://" + display_text  # Prepend https:// if missing

#                         # Assign the hyperlink (Excel will display `cell_obj.value`, but will open `hyperlink_target` when clicked)
#                         cell_obj.hyperlink = hyperlink_target

#                         # Optionally apply Excel’s built-in "Hyperlink" style (blue underline).
#                         cell_obj.style = "Hyperlink"

#                         # Ensure wrap_text is enabled by preserving existing alignment and setting wrap_text=True
#                         current_alignment = cell_obj.alignment
#                         cell_obj.alignment = Alignment(
#                             horizontal=current_alignment.horizontal,
#                             vertical=current_alignment.vertical,
#                             wrap_text=True, # otherwise, hyperlink overrides wrap_text
#                             text_rotation=current_alignment.text_rotation,
#                             shrink_to_fit=current_alignment.shrink_to_fit,
#                             indent=current_alignment.indent
#                         )

#     # Style the header row
#     for header_text, (col_idx, col_letter) in column_map.items():
#         # Set header height
#         header_cell = ws.cell(row=min_row, column=col_idx)
#         header_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True) # Hard coded for now

#         # Optional header fill
#         header_fill_color = column_settings.get(header_text, {}).get("header_fill_color")
#         if header_fill_color:
#             try:
#                 argb = parse_fill_color(header_fill_color)
#                 header_cell.fill = PatternFill(fill_type="solid", fgColor=argb) # fill_type values according to Google: 'none, 'solid, 'darkDown, 'darkGray, 'darkTrellis, 'darkGrid, 'darkHorizontal, 'darkUp, 'darkVertical, 'lightGrid, 'gray0625, 'gray125, 'lightDown, 'lightGray, 'lightHorizontal, 'lightTrellis, 'lightUp, 'lightVertical, and 'mediumGray'
#             except ValueError as ve:
#                 print(f"Warning: {ve}. Skipping fill for header '{header_text}'.")

#     # Adjust row heights ######## Should allow a separation of row heights and column header heights ########
#     for row_idx in range(min_row, max_row + 1):
#         max_cell_length = max(
#             len(str(ws.cell(row=row_idx, column=col).value or ''))
#             for col in range(min_col, max_col + 1)
#         )
#         # Dynamically sets row_height based on max_cell_length. Not sure if we will want this
#         # calculated_height = math.ceil(max_cell_length / 10) * 15 # 10 and 15 seem arbitrary
#         # ws.row_dimensions[row_idx].height = min(calculated_height, max_row_height)
#         row_height = kwargs.get("row_height", 15)
#         ws.row_dimensions[row_idx].height = min(row_height, max_row_height)

#     # Set header height if specified
#     if column_settings.get('header_height', None):
#         header_height = column_settings.get('header_height')
#         ws.row_dimensions[min_row].height = header_height

#     # Borders 
#     # Move this to column specific section since it uses the same loop?
#     for col_name, settings in column_settings.items():
#         if col_name in column_map and settings.get("separator_column", False):
#             col_index, col_letter = column_map[col_name]
#             header_fill_color = settings.get("header_fill_color")
#             if header_fill_color:
#                 try:
#                     border_color = parse_fill_color(header_fill_color) # Look up color values based on name in the dictionary
#                 except ValueError:
#                     print(f"Warning: Invalid header_fill_color for '{col_name}'. Using black.")
#                     border_color = "FF000000"
#             else:
#                 border_color = "FF000000"

#             # Style value must be one of {‘mediumDashed’, ‘mediumDashDotDot’, ‘dashDot’, ‘dashed’, ‘slantDashDot’, ‘dashDotDot’, ‘thick’, ‘thin’, ‘dotted’, ‘double’, ‘medium’, ‘hair’, ‘mediumDashDot’}
#             medium_side = Side(style='medium', color=border_color)
#             for row_idx in range(min_row + 1, max_row + 1):
#                 cell = ws.cell(row=row_idx, column=col_index)
#                 cell.border = Border(
#                     left=medium_side,
#                     right=cell.border.right,
#                     top=cell.border.top,
#                     bottom=cell.border.bottom,
#                     diagonal=cell.border.diagonal,
#                     diagonal_direction=cell.border.diagonal_direction,
#                     outline=cell.border.outline,
#                     vertical=cell.border.vertical,
#                     horizontal=cell.border.horizontal
#                 )

#     # Freeze panes
#     freeze_cols = [] # See formatting issue for details on options
#     for c_name, (c_idx, c_letter) in column_map.items():
#         if column_settings.get(c_name, {}).get("freeze_pane", False):
#             freeze_cols.append((c_idx, c_letter))

#     if freeze_cols:
#         freeze_cols.sort(key=lambda x: x[0])  # pick the rightmost
#         rightmost_idx, _ = freeze_cols[-1]
#         freeze_pane_cell = f"{get_column_letter(rightmost_idx + 1)}{min_row + 1}"
#         ws.freeze_panes = freeze_pane_cell

#     # Row banding if group_on=True
#     if kwargs.get('banding', False):
#         fill1 = PatternFill("solid", fgColor="F2F2F2")
#         fill2 = PatternFill("solid", fgColor="d9deea")

#         grouping_columns = [
#             (c_name, column_map[c_name][0])
#             for c_name, cfg in column_settings.items()
#             if c_name in column_map and cfg.get("group_on", True)
#         ]
#         if grouping_columns:
#             grouping_columns.sort(key=lambda x: x[1])

#             def get_group_key(r):
#                 return tuple(ws.cell(row=r, column=col_idx).value for (_, col_idx) in grouping_columns)

#             current_key = None
#             current_fill = fill1
#             for row_idx in range(min_row + 1, max_row + 1):
#                 row_key = get_group_key(row_idx)
#                 if row_key != current_key:
#                     ###### Use this for conditional formatting/banding ########
#                     # col_idx = headers.index(target_col) + 1  # openpyxl uses 1-based indexing

#                     # # 3. Extract all values from that column (excluding the header row)
#                     # column_values = [ws.cell(row=row, column=col_idx).value for row in range(2, ws.max_row + 1)]

#                     # [i for i, val in enumerate(my_list) if val] 
#                     ######## Should be able to use the above to get a list of row indexes, then format/band from there ########
                    
#                     current_fill = fill2 if current_fill == fill1 else fill1 # Fill1 and fill2 are used for banding, currently hardcoded but we can make that a parameter
#                     current_key = row_key

#                 for col_i in range(min_col, max_col + 1):
#                     ws.cell(row=row_idx, column=col_i).fill = current_fill

#     # Finally, save the changes
#     wb.save(file_name)


# ──────────────────────────────────────────────────────────────────────────────
# Module‐level: Default header style (defined exactly once)
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_HEADER_STYLE = {
    'bold'      : True,
    'align'     : 'center',
    'valign'    : 'vcenter',
    'font_color': '#FFFFFF',   # white
    'fg_color'  : '#4F81BD',    # blue fill
    'text_wrap' : True
}


def _is_na(val):
    """
    Return True only if `val` is a scalar and is NaN/None/NaT.
    Arrays, lists, tuples, Series, etc. are never considered NA here.
    """
    return is_scalar(val) and _pd.isna(val)


def file_formatting(
    df,
    file_name,
    sheet_name='Sheet1',
    style_definitions=None,
    column_styles=None,
    group_by=None,
    separator_columns=None,
    conditional_formats=None,
    checkbox_columns=None,
    freeze_panes=None,
    column_widths=None,
    column_formulas=None
   ):
    """
    Export a pandas DataFrame to an Excel file with rich formatting via XlsxWriter.

    Parameters:
      df (pd.DataFrame): DataFrame to write.
      file_name (str): Output Excel file path.
      sheet_name (str): Worksheet name (default 'Sheet1').
      style_definitions (dict): {style_name: format_props_dict} for reusable styles.
      column_styles (dict): Map column → style spec. Each spec can be:
          • a string (named style_name from style_definitions),
          • a dict of direct format props (applies to data cells only),
          • or a dict containing any of {'header', 'data', 'both'}:
            header: style_name or inline dict for header only,
            data:   style_name or inline dict for data only,
            both:   style_name or inline dict for both header & data.
      group_by (str or list): Column name(s) to group rows; draws a bottom border when the key changes.
      separator_columns (str, int, list): Column(s) after which to draw a vertical (medium) border.
      conditional_formats (dict): {column: rule}, where rule can be:
          • 'RYG' (built-in red/yellow/green 3-color scale),
          • '3_color_scale', '2_color_scale', 'data_bar', etc.,
          • or a full XlsxWriter rule dict (with type, colors, thresholds).
      checkbox_columns (str or list): Column(s) whose boolean cells become in-cell checkboxes.
      freeze_panes (bool or str or int): If True or str/int, freeze header row plus columns up to and including named column.
          • If True, no columns frozen (just header).
          • If a column name (string), freeze all columns up to that column.
          • If an integer index, freeze up to that index.
      column_widths (dict): {column_name or index: width} for explicit column widths.

    Returns:
      The original DataFrame (in case chaining is desired).
    """
    
    writer = _pd.ExcelWriter(file_name, engine="xlsxwriter")

    # Write the dataframe data to XlsxWriter, turn off the default index
    df.to_excel(writer, sheet_name, index=False)

    # ──────────────────────────────────────────────────────────────────────────
    # 1) BUILD STYLE DEFINITIONS
    # ──────────────────────────────────────────────────────────────────────────

    # Start by injecting our one default header style, then layer on user styles.
    style_def = {'header_default': DEFAULT_HEADER_STYLE}
    if style_definitions:
        style_def.update(style_definitions)

    # Prepare lookup dicts for each column:
    #   data_style_by_col[col]   → style_name for data cells
    #   header_style_by_col[col] → style_name for header cell
    data_style_by_col   = {}
    header_style_by_col = {}
    auto_counter = 0

    def _next_auto_name():
        nonlocal auto_counter
        name = f"__auto_{auto_counter}"
        auto_counter += 1
        return name

    # 1.1) Resolve column_styles into two maps
    for col in df.columns:
        spec = (column_styles or {}).get(col, 'default')

        # Case A: A dict that explicitly uses any of 'header','data','both'
        if isinstance(spec, dict) and any(k in spec for k in ('header','data','both')):
            if 'both' in spec:
                data_part   = header_part = spec['both']
            else:
                data_part   = spec.get('data',   'default')
                header_part = spec.get('header', 'header_default')
            data_style_by_col[col]   = data_part
            header_style_by_col[col] = header_part

        # Case B: A simple string or inline-dict → data style only, header gets default
        elif isinstance(spec, (str, dict)):
            data_style_by_col[col]   = spec
            header_style_by_col[col] = 'header_default'

        else:
            raise TypeError(
                f"column_styles[{col!r}] must be a str, dict, or a dict with 'header'/'data'/'both'; "
                f"got {type(spec).__name__}"
            )

    # 1.2) Turn any inline-dict into a real named style in style_def
    for mapping in (data_style_by_col, header_style_by_col):
        for col, style_spec in mapping.items():
            if isinstance(style_spec, dict):
                auto_name = _next_auto_name()
                style_def[auto_name] = style_spec
                mapping[col] = auto_name
            elif isinstance(style_spec, str):
                # Ensure the named style exists (even if empty); user may override it in style_definitions.
                style_def.setdefault(style_spec, {})
            else:
                raise TypeError(f"Invalid style spec for column {col!r}: {style_spec!r}")

    # 1.3) Ensure a 'default' style exists for any column not explicitly styled
    style_def.setdefault('default', {})

    # ──────────────────────────────────────────────────────────────────────────
    # 2) CREATE WORKBOOK, WORKSHEET, AND FORMAT OBJECTS
    # ──────────────────────────────────────────────────────────────────────────
    workbook  = writer.book
    formats   = {name: workbook.add_format(props) for name, props in style_def.items()}
    worksheet = writer.sheets[sheet_name]

    # Initialize containers that will be used for borders:
    border_after_indices = set()  # columns that require a vertical (medium) border
    bordered_cache = {}           # cache for Format objects combined with bottom/right border

    # ──────────────────────────────────────────────────────────────────────────
    # 3) FREEZE PANES LOGIC
    # ──────────────────────────────────────────────────────────────────────────
    if freeze_panes:
        # If freeze_panes is a column name:
        if isinstance(freeze_panes, str):
            if freeze_panes not in df.columns:
                raise ValueError(f"freeze_panes: column '{freeze_panes}' not found in DataFrame")
            col_idx = df.columns.get_loc(freeze_panes)
        elif isinstance(freeze_panes, int):
            col_idx = freeze_panes
            if not (0 <= col_idx < len(df.columns)):
                raise IndexError(f"freeze_panes index {col_idx} out of range for {len(df.columns)} columns")
        elif freeze_panes is True:
            # Default: no columns frozen, just header row
            worksheet.freeze_panes(1, 0)
            col_idx = None
        else:
            raise TypeError("freeze_panes must be True, a column name (str), or an integer index")

        # If a column name/index was provided, freeze that many columns to the left
        if isinstance(col_idx, int):
            worksheet.freeze_panes(1, col_idx + 1)

    # ──────────────────────────────────────────────────────────────────────────
    # 4) DETERMINE SEPARATOR COLUMNS (vertical borders)
    # ──────────────────────────────────────────────────────────────────────────
    if separator_columns:
        sep_cols = (
            [separator_columns]
            if not isinstance(separator_columns, (list, tuple))
            else separator_columns
        )
        for col in sep_cols:
            if isinstance(col, str):
                if col not in df.columns:
                    raise ValueError(f"separator_columns: column '{col}' not found")
                idx = df.columns.get_loc(col)
            else:
                idx = col
                if not (0 <= idx < len(df.columns)):
                    raise IndexError(f"separator_columns index {idx} out of range")
            border_after_indices.add(idx)

    # ──────────────────────────────────────────────────────────────────────────
    # 5) DETERMINE ROW GROUP BREAKPOINTS (horizontal bottom borders)
    # ──────────────────────────────────────────────────────────────────────────
    group_break_rows = set()
    if group_by:
        group_cols = [group_by] if isinstance(group_by, str) else list(group_by)
        for gc in group_cols:
            if gc not in df.columns:
                raise ValueError(f"group_by: column '{gc}' not found")

        group_indices = [df.columns.get_loc(c) for c in group_cols]
        for pos in range(len(df) - 1):
            for ci in group_indices:
                curr = df.iat[pos, ci]
                nxt  = df.iat[pos + 1, ci]
                if not _pd.isna(curr) and not _pd.isna(nxt):
                    if curr != nxt:
                        group_break_rows.add(pos + 1)
                        break
                elif _pd.isna(curr) != _pd.isna(nxt):
                    group_break_rows.add(pos + 1)
                    break

    # ──────────────────────────────────────────────────────────────────────────
    # 6) WRITE HEADER ROW (ROW 0)
    # ──────────────────────────────────────────────────────────────────────────
    for col_idx, col_name in enumerate(df.columns):
        fmt = formats[header_style_by_col[col_name]]

        # If this column is marked as a separator, add a medium right border
        if col_idx in border_after_indices:
            key = (header_style_by_col[col_name], 'right')
            if key not in bordered_cache:
                props = style_def[header_style_by_col[col_name]].copy()
                props['right'] = 2  # medium border
                bordered_cache[key] = workbook.add_format(props)
            fmt = bordered_cache[key]

        worksheet.write(0, col_idx, col_name, fmt)

    # ──────────────────────────────────────────────────────────────────────────
    # 7) WRITE DATA ROWS (ROWS 1 .. N)
    # ──────────────────────────────────────────────────────────────────────────
    for row_num, record in enumerate(df.itertuples(index=False, name=None), start=1):
        is_group_break = (row_num in group_break_rows)
        for col_idx, value in enumerate(record):
            col_name   = df.columns[col_idx]
            style_name = data_style_by_col[col_name]
            fmt        = formats[style_name]

            # 7.1) Apply medium bottom border if group boundary
            #      and/or medium right border if separator column
            need_bottom = is_group_break
            need_right  = (col_idx in border_after_indices)
            if need_bottom or need_right:
                key_flags = (style_name, need_bottom, need_right)
                if key_flags not in bordered_cache:
                    props = style_def[style_name].copy()
                    if need_bottom:
                        props['bottom'] = 2
                    if need_right:
                        props['right'] = 2
                    bordered_cache[key_flags] = workbook.add_format(props)
                fmt = bordered_cache[key_flags]

            # 7.2) Value‐type dispatch
            if _is_na(value) or value is None:
                worksheet.write_blank(row_num, col_idx, None, fmt)

            elif isinstance(value, str):
                if value.startswith(('http://', 'https://', 'ftp://', 'mailto:')) or value.startswith('www.'):
                    url = value if value.startswith(('http', 'ftp', 'mailto')) else 'http://' + value
                    worksheet.write_url(row_num, col_idx, url, fmt, string=value)
                else:
                    worksheet.write(row_num, col_idx, value, fmt)

            elif isinstance(value, bool):
                worksheet.write_boolean(row_num, col_idx, value, fmt)

            elif isinstance(value, (int, float, _np.number)) and not _np.isnan(value):
                worksheet.write_number(row_num, col_idx, float(value), fmt)

            elif isinstance(value, dict):
                # Dump dict as JSON string
                worksheet.write(row_num, col_idx, _pd.io.json.dumps(value, ensure_ascii=False), fmt)

            elif isinstance(value, (list, tuple, _np.ndarray, _pd.Series)):
                flat = ', '.join(map(str, _np.asarray(value).ravel()))
                worksheet.write(row_num, col_idx, flat, fmt)

            else:
                # Fallback: cast to string
                worksheet.write(row_num, col_idx, str(value), fmt)

    # ──────────────────────────────────────────────────────────────────────────
    # 8) APPLY CONDITIONAL FORMATTING
    # ──────────────────────────────────────────────────────────────────────────
    if conditional_formats:
        for col, rule in conditional_formats.items():
            if isinstance(col, str):
                if col not in df.columns:
                    raise ValueError(f"conditional_formats: column '{col}' not found")
                col_idx = df.columns.get_loc(col)
            else:
                col_idx = col

            first_data_row = 1
            last_data_row  = len(df)

            # Expand simple string shortcuts
            if isinstance(rule, str):
                rl = rule.lower()
                if rl in ('ryg', 'red-yellow-green', 'red_yellow_green'):
                    options = {
                        'type':      '3_color_scale',
                        'min_color': '#F8696B',
                        'mid_color': '#FFEB84',
                        'max_color': '#63BE7B'
                    }
                elif '3_color' in rl:
                    options = {'type': '3_color_scale'}
                elif '2_color' in rl:
                    options = {'type': '2_color_scale'}
                elif 'data_bar' in rl:
                    options = {'type': 'data_bar'}
                else:
                    continue
            elif isinstance(rule, dict):
                options = rule.copy()
            else:
                continue

            worksheet.conditional_format(first_data_row, col_idx, last_data_row, col_idx, options)

    # ──────────────────────────────────────────────────────────────────────────
    # 9) SET COLUMN WIDTHS OR AUTOFIT (with an upper bound of 50)
    # ──────────────────────────────────────────────────────────────────────────
    if column_widths:
        # 9.1) First, apply any user‐specified widths verbatim
        for col, width in column_widths.items():
            if isinstance(col, str):
                if col not in df.columns:
                    raise ValueError(f"column_widths: column '{col}' not found")
                idx = df.columns.get_loc(col)
            else:
                idx = col
                if not (0 <= idx < len(df.columns)):
                    raise IndexError(f"column_widths index {idx} out of range")
            worksheet.set_column(idx, idx, width)

        # 9.2) Now auto‐fit any columns NOT in column_widths,
        #       capping the final width at 50.
        #       If the user’s explicit width is > 50, we leave it as is;
        #       otherwise, we compute max_len+2 and cap at 50.
        for idx, col in enumerate(df.columns):
            # Skip columns that already have an explicit width
            if ( (isinstance(col, str) and col in column_widths)
              or (isinstance(idx, int) and idx in column_widths) ):
                continue

            # Compute the “ideal” width from data+header
            values = df[col]
            max_len = max([len(str(x)) for x in values] + [len(str(col))])
            ideal_width = max_len + 2

            # Cap at 50
            final_width = ideal_width if ideal_width <= 50 else 50
            worksheet.set_column(idx, idx, final_width)

    else:
        # No explicit widths at all → auto‐fit every column with max = 50
        for idx, col in enumerate(df.columns):
            values = df[col]
            max_len = max([len(str(x)) for x in values] + [len(str(col))])
            ideal_width = max_len + 2
            final_width = ideal_width if ideal_width <= 50 else 50
            worksheet.set_column(idx, idx, final_width)

    # ──────────────────────────────────────────────────────────────────────────
    # 10) ADD AN EXCEL TABLE FOR BANDED ROWS, INJECT ANY USER FORMULAS, AND
    #     ENSURE HEADER WRAP (text_wrap=True)
    # ──────────────────────────────────────────────────────────────────────────
    first_row, first_col = 0, 0
    last_row  = len(df)
    last_col  = len(df.columns) - 1
    table_range = _xlu.xl_range_abs(first_row, first_col, last_row, last_col)

    # 10.1) Build a map from column_name → the header Format object (which has text_wrap=True)
    wrapped_header_cells = {
        col_name: formats[ header_style_by_col[col_name] ]
        for col_name in df.columns
    }

    # 10.2) Build the “columns” list for add_table, using 'header_format' 
    columns_list = []
    for col_name in df.columns:
        hdr_fmt  = wrapped_header_cells[col_name]
        data_fmt = formats[ data_style_by_col[col_name] ]  # whatever data style you chose

        if column_formulas and col_name in column_formulas:
            # Formula + wrapping on header + normal data format on each data cell
            columns_list.append({
                'header'        : col_name,
                'formula'       : column_formulas[col_name],
                'header_format' : hdr_fmt,   # wrap header
                'format'        : data_fmt   # style data cells normally
            })
        else:
            # No formula; still wrap header, and style data cells
            columns_list.append({
                'header'        : col_name,
                'header_format' : hdr_fmt,   # wrap header
                'format'        : data_fmt   # style data cells normally
            })

    # 10.3) Finally, add the table. Now the header row will use hdr_fmt (with text_wrap),
    # and the data cells will use data_fmt (e.g. your checkbox or green‐font format).
    worksheet.add_table(table_range, {
        'name'         : sheet_name.replace(' ', '_'),
        'columns'      : columns_list,
        'style'        : 'Table Style Medium9',
        'banded_rows'  : (group_by is None)
    })

    # ──────────────────────────────────────────────────────────────────────────
    # 11) SAVE AND RETURN
    # ──────────────────────────────────────────────────────────────────────────
    writer.close()
    return df