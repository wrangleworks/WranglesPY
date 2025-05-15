import math
import re as _re
from typing import BinaryIO
from ..utils import wildcard_expansion as _wildcard_expansion
from ..utils import wildcard_expansion_dict as _wildcard_expansion_dict
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo


def file_formatting(
    file_name: str,
    buffer: BinaryIO,
    column_settings: dict = None,
    max_row_height: int = 60,
    **kwargs
    ):
    """
    Format a .xlsx file using openpyxl.

    :param file_name: The name of the file to save the formatted data to.
    :param column_settings: A dictionary of column settings, where keys are column names and values are dictionaries of formatting options.
    :param buffer: A BytesIO buffer containing the Excel file to format.
    :param max_row_height: The maximum height of rows in the Excel file.
    :param kwargs: Additional formatting options.
    """
    # (A) Semantic color map for optional header fill
    COLOR_MAP = {
        "red":    "FFCC6666",
        "green":  "FF66A066",
        "orange": "FFFF9900",
        "blue":   "FF6699FF",
        "yellow": "FFE6B800",
        "purple": "FF9966CC",
        "gray":   "FFBFBFBF",
    }

    def parse_fill_color(color_str):
        """Convert a semantic color name or a hex string into an ARGB color code."""
        color_str = color_str.strip().lower()
        if color_str in COLOR_MAP:
            return COLOR_MAP[color_str]

        color_str = color_str.lstrip('#')
        if len(color_str) == 6:
            color_str = "FF" + color_str
        elif len(color_str) == 8:
            pass
        else:
            raise ValueError(f"Invalid color code: '{color_str}'")
        return color_str.upper()

    universal_settings_list = ['banding', 'table_style'] # Settings that are associated with the entire table, not just columns, rows, or cells
    default_settings = {k: v for k, v in kwargs.items() if k not in universal_settings_list}

    # Load the workbook from the buffer
    wb = load_workbook(buffer)
    ws = wb.worksheets[0] # Currently only allowing files with one worksheet

    columns = [cell.value for cell in ws[ws.min_row]]

    # Split inputs on comma, but not on escaped commas
    split_settings = {}
    for key, value in column_settings.items():
        # If the key contains an unescaped comma, we want to split it
        if ',' in key:
            # Split on unescaped commas
            parts = _re.split(r'(?<!\\),', key)
            # Clean up escaped commas
            parts = [p.replace('\\,', ',').strip() for p in parts]
            if len(parts) > 1:
                for part in parts:
                    split_settings[part] = value
            else:
                split_settings[key] = value
        else:
            split_settings[key] = value

    column_settings = split_settings

    wild_card_columns = [col for col in column_settings.keys() if col.endswith('*')]

    if wild_card_columns:
        for col in wild_card_columns:
            columns_to_expand = _wildcard_expansion(
                            all_columns=columns,
                            selected_columns=[col]
                        )
            for other_col in columns_to_expand:
                column_settings[other_col]= column_settings[col]

    # Handle columns that are missing from column_settings
    unspecified_columns = [cell.value for cell in ws[1] if cell.value not in column_settings.keys()]

    # Build default column settings to be applied to every column not specified
    column_settings['default'] = default_settings

    for col in unspecified_columns:
        if 'default' in column_settings.keys():
            column_settings[col] = column_settings['default']
        # else:
        #     column_settings[col] = {'width': 30, 'header_fill_color': 'blue'} # Currently seems to not be doing anything, leaving commented out for now

    # Delete the default key from column_settings since it has already been applied to the unspecified columns
    if 'default' in column_settings.keys(): del column_settings['default']

    min_row, max_row = ws.min_row, ws.max_row
    min_col, max_col = ws.min_column, ws.max_column

    # Set a table name based off sheet name, replace spaces and non alphanumeric characters
    table_name = f"Table_{ws.title.replace(' ', '_')}"
    table_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in table_name)
    if table_name[0].isdigit():
        table_name = f"_{table_name}"

    # Build out table reference (the cell range for the table)
    first_cell = f"{get_column_letter(min_col)}{min_row}"
    last_cell = f"{get_column_letter(max_col)}{max_row}"
    table_ref = f"{first_cell}:{last_cell}"

    tab = Table(displayName=table_name, ref=table_ref) # Named tab to avoid confusion with the table object

    # Should allow users to set any of these in the future
    table_style = kwargs.get('table_style', 'TableStyleMedium9') # Default to TableStyleMedium9
    tab.tableStyleInfo = TableStyleInfo(
            name= table_style,
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False
        )
    ws.add_table(tab)

    # Unpack general font data
    font_name = kwargs.pop('font', 'Calibri')
    font_size = kwargs.pop('font_size', 11)
    font_color = kwargs.pop('font_color', 'FF000000')
    bold = kwargs.pop('bold', False)
    italicize = kwargs.pop('italic', False)
    underline = kwargs.pop('underline', None)

    # Set cell alignment
    if 'alignment' in column_settings.keys():
        alignment = column_settings.pop('alignment')
        alignment = Alignment(horizontal=alignment.get('horizontal', 'left'),
                              vertical=alignment.get('vertical', 'top'),
                              wrap_text=alignment.get('wrap_text', True))
    else:
        alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)

    # Styling for all cells
    for row_cells in ws.iter_rows(min_row=min_row, max_row=max_row,
                                    min_col=min_col, max_col=max_col):

        for cell in row_cells:
            cell.alignment = alignment
            cell.font = Font(
                name=font_name,
                size=font_size,
                color=font_color,
                bold=bold,
                italic=italicize,
                underline=underline
            )

    # Identify header row & build a column map
    header_row = list(ws.iter_rows(
        min_row=min_row, max_row=min_row,
        min_col=min_col, max_col=max_col
    ))[0]

    # Build column map to set header specific formatting
    column_map = {}
    for idx, header_cell in enumerate(header_row, start=min_col):
        header_text = header_cell.value if header_cell.value else ""
        column_map[header_text] = (idx, get_column_letter(idx))

    # Column-specific settings
    for col_name, settings in column_settings.items():
        if col_name in column_map:
            col_index, col_letter = column_map[col_name]

            # Column width
            ws.column_dimensions[col_letter].width = settings.pop("width", 20)

            for cell_tuple in ws.iter_rows(
                    min_row=min_row, # Add 1 if not wanting to include header
                    max_row=max_row,
                    min_col=col_index,
                    max_col=col_index
                ):
                cell_obj = cell_tuple[0]

                # Alignment
                if 'alignment' in settings.keys():
                    column_alignment = settings.get('alignment')
                    curr_align = cell_obj.alignment
                    cell_obj.alignment = Alignment(
                        horizontal=column_alignment.get('horizontal', 'left'),
                        vertical=column_alignment.get('vertical', 'top'),
                        wrap_text=column_alignment.get('wrap_text', True),
                        text_rotation=curr_align.text_rotation,
                        shrink_to_fit=curr_align.shrink_to_fit,
                        indent=curr_align.indent
                    )

                # Font
                curr_font = cell_obj.font
                cell_obj.font = Font(
                    name=settings.get('font', curr_font.name),
                    size=settings.get('font_size', curr_font.size),
                    color=settings.get('font_color',curr_font.color),
                    bold=settings.get('bold', curr_font.bold),
                    italic=settings.get('italic', curr_font.italic),
                    underline=settings.get('underline', curr_font.underline),
                    vertAlign=curr_font.vertAlign, # Possible values: ‘superscript’, ‘baseline’, ‘subscript’
                    strike=curr_font.strike
                )

                # Number format (if numeric)
                if "number_format" in settings: # cell_obj.number_format allows for General, Text, etc.
                    if isinstance(cell_obj.value, (int, float)):
                        cell_obj.number_format = settings["number_format"]

                # If 'hyperlink' is True, convert the cell's text into a hyperlink (prepended with 'https://' if needed).
                if settings.get("hyperlink", False):
                    if cell_obj.value:
                        # Keep the display text the same as the original cell value
                        display_text = str(cell_obj.value).strip()

                        # Determine the actual hyperlink target
                        if display_text.lower().startswith("http://") or display_text.lower().startswith("https://"): # Necessary to avoid a non trusted link pop up
                            hyperlink_target = display_text
                        else:
                            hyperlink_target = "https://" + display_text  # Prepend https:// if missing

                        # Assign the hyperlink (Excel will display `cell_obj.value`, but will open `hyperlink_target` when clicked)
                        cell_obj.hyperlink = hyperlink_target

                        # Optionally apply Excel’s built-in "Hyperlink" style (blue underline).
                        cell_obj.style = "Hyperlink"

                        # Ensure wrap_text is enabled by preserving existing alignment and setting wrap_text=True
                        current_alignment = cell_obj.alignment
                        cell_obj.alignment = Alignment(
                            horizontal=current_alignment.horizontal,
                            vertical=current_alignment.vertical,
                            wrap_text=True, # otherwise, hyperlink overrides wrap_text
                            text_rotation=current_alignment.text_rotation,
                            shrink_to_fit=current_alignment.shrink_to_fit,
                            indent=current_alignment.indent
                        )

    # Style the header row
    for header_text, (col_idx, col_letter) in column_map.items():
        # Set header height
        header_cell = ws.cell(row=min_row, column=col_idx)
        header_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True) # Hard coded for now

        # Optional header fill
        header_fill_color = column_settings.get(header_text, {}).get("header_fill_color")
        if header_fill_color:
            try:
                argb = parse_fill_color(header_fill_color)
                header_cell.fill = PatternFill(fill_type="solid", fgColor=argb) # fill_type values according to Google: 'none, 'solid, 'darkDown, 'darkGray, 'darkTrellis, 'darkGrid, 'darkHorizontal, 'darkUp, 'darkVertical, 'lightGrid, 'gray0625, 'gray125, 'lightDown, 'lightGray, 'lightHorizontal, 'lightTrellis, 'lightUp, 'lightVertical, and 'mediumGray'
            except ValueError as ve:
                print(f"Warning: {ve}. Skipping fill for header '{header_text}'.")

    # Adjust row heights ######## Should allow a seperation of row heights and column header heights ########
    for row_idx in range(min_row, max_row + 1):
        max_cell_length = max(
            len(str(ws.cell(row=row_idx, column=col).value or ''))
            for col in range(min_col, max_col + 1)
        )
        # Dynamically sets row_height based on max_cell_length. Not sure if we will want this
        # calculated_height = math.ceil(max_cell_length / 10) * 15 # 10 and 15 seem arbitrary
        # ws.row_dimensions[row_idx].height = min(calculated_height, max_row_height)
        row_height = kwargs.get("row_height", 15)
        ws.row_dimensions[row_idx].height = min(row_height, max_row_height)

    # Set header height if specified
    if column_settings.get('header_height', None):
        header_height = column_settings.get('header_height')
        ws.row_dimensions[min_row].height = header_height

    # Borders 
    # Move this to column specific section since it uses the same loop?
    for col_name, settings in column_settings.items():
        if col_name in column_map and settings.get("separator_column", False):
            col_index, col_letter = column_map[col_name]
            header_fill_color = settings.get("header_fill_color")
            if header_fill_color:
                try:
                    border_color = parse_fill_color(header_fill_color) # Look up color values based on name in the dictionary
                except ValueError:
                    print(f"Warning: Invalid header_fill_color for '{col_name}'. Using black.")
                    border_color = "FF000000"
            else:
                border_color = "FF000000"

            # Style value must be one of {‘mediumDashed’, ‘mediumDashDotDot’, ‘dashDot’, ‘dashed’, ‘slantDashDot’, ‘dashDotDot’, ‘thick’, ‘thin’, ‘dotted’, ‘double’, ‘medium’, ‘hair’, ‘mediumDashDot’}
            medium_side = Side(style='medium', color=border_color)
            for row_idx in range(min_row + 1, max_row + 1):
                cell = ws.cell(row=row_idx, column=col_index)
                cell.border = Border(
                    left=medium_side,
                    right=cell.border.right,
                    top=cell.border.top,
                    bottom=cell.border.bottom,
                    diagonal=cell.border.diagonal,
                    diagonal_direction=cell.border.diagonal_direction,
                    outline=cell.border.outline,
                    vertical=cell.border.vertical,
                    horizontal=cell.border.horizontal
                )

    # Freeze panes
    freeze_cols = [] # See formatting issue for details on options
    for c_name, (c_idx, c_letter) in column_map.items():
        if column_settings.get(c_name, {}).get("freeze_pane", False):
            freeze_cols.append((c_idx, c_letter))

    if freeze_cols:
        freeze_cols.sort(key=lambda x: x[0])  # pick the rightmost
        rightmost_idx, _ = freeze_cols[-1]
        freeze_pane_cell = f"{get_column_letter(rightmost_idx + 1)}{min_row + 1}"
        ws.freeze_panes = freeze_pane_cell

    # Row banding if group_on=True
    if kwargs.get('banding', False):
        fill1 = PatternFill("solid", fgColor="F2F2F2")
        fill2 = PatternFill("solid", fgColor="d9deea")

        grouping_columns = [
            (c_name, column_map[c_name][0])
            for c_name, cfg in column_settings.items()
            if c_name in column_map and cfg.get("group_on", True)
        ]
        if grouping_columns:
            grouping_columns.sort(key=lambda x: x[1])

            def get_group_key(r):
                return tuple(ws.cell(row=r, column=col_idx).value for (_, col_idx) in grouping_columns)

            current_key = None
            current_fill = fill1
            for row_idx in range(min_row + 1, max_row + 1):
                row_key = get_group_key(row_idx)
                if row_key != current_key:
                    ###### Use this for conditional formatting/banding ########
                    # col_idx = headers.index(target_col) + 1  # openpyxl uses 1-based indexing

                    # # 3. Extract all values from that column (excluding the header row)
                    # column_values = [ws.cell(row=row, column=col_idx).value for row in range(2, ws.max_row + 1)]

                    # [i for i, val in enumerate(my_list) if val] 
                    ######## Should be able to use the above to get a list of row indexes, then format/band from there ########
                    
                    current_fill = fill2 if current_fill == fill1 else fill1 # Fill1 and fill2 are used for banding, currently hardcoded but we can make that a parameter
                    current_key = row_key

                for col_i in range(min_col, max_col + 1):
                    ws.cell(row=row_idx, column=col_i).fill = current_fill

    # Finally, save the changes
    wb.save(file_name)