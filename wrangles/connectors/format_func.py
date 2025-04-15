
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
import math





########## Notes ##########

# Need to think about how to be able to just pass values through that then do available formatting in Excel. Borders or something niche for example.

# Speaking of borders, drop names like separator_column for what it is in Excel (borders)


# Separating out header formatting from body formatting like so:
"""
file:
name: tests/temp/write_data.xlsx
format:
    Find:
        width: 10
        header:
            fill_color: blue
            font_size: 14
        fill_color: yellow
        font_size: 18
    Replace:
        width: 20
        header_fill_color: red # old, ignore the name compared to the above
        font_size: 11
    """

# What about conditional formatting?

# What about the ability to freeze panes?

# What about striping or whatever Chris called it?

# Add font, but cell based, row based, column based, sheet based, or all of it?









def convert_worksheets_to_tables(
    file_name,
    column_settings,
    buffer,
    max_row_height=60
):
    """
    Convert each worksheet in the given workbook into a formatted table, **without** any filtering logic.
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
    ######### I don't think we are going to allow this. Just pass default values through as their own key #########
    # if 'Default' in column_settings.keys():
    #     column_settings['default'] = column_settings.pop('Default')

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







    ########## Come back to these ##########

    fill1 = PatternFill("solid", fgColor="6efdfd")
    # fill1 = PatternFill("solid", fgColor="D9D9D9")
    fill2 = PatternFill("solid", fgColor="f231f2")
    # fill2 = PatternFill("solid", fgColor="BFBFBF")

    default_table_style = TableStyleInfo(
        name="TableStyleMedium9",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=False,
        showColumnStripes=False
    )









    wb = load_workbook(buffer)

    ws = wb.worksheets[0]

    columns = [cell.value for cell in ws[ws.min_row]]

    # Handle columns that are missing from column_settings
    unspecified_columns = [cell.value for cell in ws[1] if cell.value not in column_settings.keys()]

    column_settings['default'] = {key: value for key, value in zip(list(column_settings.keys()), list(column_settings.values())) if key not in columns}

    for col in unspecified_columns:
        if 'default' in column_settings.keys():
            column_settings[col] = column_settings['default']
        else:
            column_settings[col] = {'width': 30, 'header_fill_color': 'blue'}

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
    tab.tableStyleInfo = default_table_style
    ws.add_table(tab)

    # Unpack font data
    font_name = column_settings.pop('font', 'Calibri')
    font_size = column_settings.pop('font_size', 11)
    font_color = column_settings.pop('font_color', 'FF000000')

    # Set cell alignment
    default_alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
    if 'alignment' in column_settings.keys():
        alignment = column_settings.pop('alignment')
        alignment = Alignment(horizontal=alignment.get('horizontal', 'left'),
                              vertical=alignment.get('vertical', 'top'),
                              wrap_text=alignment.get('wrap_text', True))
    else:
        alignment = default_alignment

    # Styling for all cells
    for row_cells in ws.iter_rows(min_row=min_row, max_row=max_row,
                                    min_col=min_col, max_col=max_col):

        for cell in row_cells:
            cell.alignment = alignment
            cell.font = Font(name=font_name, size=font_size, bold=False, color=font_color)

    # 3) Identify header row & build a column map ######### What is this doing? #########
    header_row = list(ws.iter_rows(
        min_row=min_row, max_row=min_row,
        min_col=min_col, max_col=max_col
    ))[0]

    column_map = {}
    for idx, header_cell in enumerate(header_row, start=min_col):
        header_text = header_cell.value if header_cell.value else ""
        column_map[header_text] = (idx, get_column_letter(idx))

    # 4) Column-specific settings
    for col_name, settings in column_settings.items():
        if col_name in column_map:
            col_index, col_letter = column_map[col_name]

            # Column width
            ws.column_dimensions[col_letter].width = settings.pop("width", 20)

            # Desired alignment, font
            desired_halign = settings.get("horizontal") ####### No default for these. No vertical alignment? This shows that horizontal can be passed through in settings ########
            desired_font_size = settings.get("font_size")
            desired_bold = settings.get("bold") ######### Add italic, underline, etc. #########

            for cell_tuple in ws.iter_rows(
                min_row=min_row + 1,
                max_row=max_row,
                min_col=col_index,
                max_col=col_index
            ):
                cell_obj = cell_tuple[0]

                # Alignment
                if desired_halign: ####### Why all of this just based off of horizontal alignment? ########
                    curr_align = cell_obj.alignment
                    cell_obj.alignment = Alignment(
                        horizontal=desired_halign,
                        vertical=curr_align.vertical or 'top', ######## Vertical alignment is preserved or set to top here ########
                        wrap_text=curr_align.wrap_text,
                        text_rotation=curr_align.text_rotation, ######## All of these are possible fields to allow users to set ########
                        shrink_to_fit=curr_align.shrink_to_fit,
                        indent=curr_align.indent
                    )

                # Font
                if desired_font_size or (desired_bold is not None):
                    curr_font = cell_obj.font ####### Same ideas as above, but for font ########
                    cell_obj.font = Font(
                        name=curr_font.name,
                        size=desired_font_size if desired_font_size else curr_font.size,
                        bold=desired_bold if desired_bold is not None else curr_font.bold, ######## Instead of current, can just set defaults ########
                        italic=curr_font.italic,
                        vertAlign=curr_font.vertAlign,
                        underline=curr_font.underline,
                        strike=curr_font.strike,
                        color=curr_font.color
                    )

                # Number format (if numeric)
                if "number_format" in settings: ######### cell_obj.number_format allows for General, Text, etc. #########
                    if isinstance(cell_obj.value, (int, float)):
                        cell_obj.number_format = settings["number_format"]

                # If 'hyperlink' is True, convert the cell's text into a hyperlink (prepended with 'https://' if needed).
                if settings.get("hyperlink", False):
                    if cell_obj.value:
                        # 1) Keep the display text the same as the original cell value
                        display_text = str(cell_obj.value).strip()

                        # 2) Determine the actual hyperlink target
                        if display_text.lower().startswith("http://") or display_text.lower().startswith("https://"): ####### Surprisingly necessary to avoid a non trusted link pop up ########
                            hyperlink_target = display_text
                        else:
                            hyperlink_target = "https://" + display_text  # Prepend https:// if missing

                        # 3) Assign the hyperlink (Excel will display `cell_obj.value`, 
                        #    but will open `hyperlink_target` when clicked)
                        cell_obj.hyperlink = hyperlink_target

                        # 4) Optionally apply Excel’s built-in "Hyperlink" style (blue underline).
                        cell_obj.style = "Hyperlink"

                        # 5) Ensure wrap_text is enabled by preserving existing alignment and setting wrap_text=True
                        current_alignment = cell_obj.alignment
                        cell_obj.alignment = Alignment( ####### Why does this seem to be repeating what was done above? ########
                            horizontal=current_alignment.horizontal,
                            vertical=current_alignment.vertical,
                            wrap_text=True, # otherwise, hyperlink overrides wrap_text
                            text_rotation=current_alignment.text_rotation,
                            shrink_to_fit=current_alignment.shrink_to_fit,
                            indent=current_alignment.indent
                        )

    # 5) Style the header row
    for header_text, (col_idx, col_letter) in column_map.items():
        header_cell = ws.cell(row=min_row, column=col_idx)
        header_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True) ######## Hard coded header alignment ########
        header_cell.font = Font(name='Calibri', size=12, bold=True, color='FFFFFFFF') ######## Hard coded header font ########

        # Optional header fill
        header_fill_color = column_settings.get(header_text, {}).get("header_fill_color") ####### header_fill_color versus what other fill color? ########
        if header_fill_color:
            try:
                argb = parse_fill_color(header_fill_color) ########## Looks up color values based on name in the dictionary, and formats the color code properly for color codes that are passed through ##########
                header_cell.fill = PatternFill(fill_type="solid", fgColor=argb) ####### What other fill_types are there? Something to allow to be set or is it useless? ########
            except ValueError as ve:
                print(f"Warning: {ve}. Skipping fill for header '{header_text}'.") ######### Does this mean that there is not a default fill color? #########

    # 6) Adjust row heights
    for row_idx in range(min_row, max_row + 1):
        max_cell_length = max(
            len(str(ws.cell(row=row_idx, column=col).value or ''))
            for col in range(min_col, max_col + 1)
        )
        calculated_height = math.ceil(max_cell_length / 10) * 15 ####### 10 and 15 seem arbitrary, but what is the actual math doing and why? ########
        # ws.row_dimensions[row_idx].height = min(calculated_height, max_row_height) ######### Dynamically attempts to set row_height, but users can set max #########
        row_height = column_settings.pop("row_height", 15)
        ws.row_dimensions[row_idx].height = min(row_height, max_row_height) ######### Dynamically attempts to set row_height, but users can set max #########

    # 7) Separator columns
    for col_name, settings in column_settings.items():
        if col_name in column_map and settings.get("separator_column", False):
            col_index, col_letter = column_map[col_name]
            header_fill_color = settings.get("header_fill_color")
            if header_fill_color:
                try:
                    border_color = parse_fill_color(header_fill_color) ########## Looks up color values based on name in the dictionary, and formats the color code properly for color codes that are passed through ##########
                except ValueError:
                    print(f"Warning: Invalid header_fill_color for '{col_name}'. Using black.")
                    border_color = "FF000000"
            else:
                border_color = "FF000000"

            medium_side = Side(style='medium', color=border_color)
            for row_idx in range(min_row + 1, max_row + 1):
                cell = ws.cell(row=row_idx, column=col_index)
                cell.border = Border( ######### All of these setting type things seem very redundant #########
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

    # 8) Freeze panes
    freeze_cols = [] ######### Going to need to try to use what we have currently. See formatting issue for details on options #########
    for c_name, (c_idx, c_letter) in column_map.items():
        if column_settings.get(c_name, {}).get("freeze_pane", False):
            freeze_cols.append((c_idx, c_letter))

    if freeze_cols:
        freeze_cols.sort(key=lambda x: x[0])  # pick the rightmost
        rightmost_idx, _ = freeze_cols[-1]
        freeze_pane_cell = f"{get_column_letter(rightmost_idx + 1)}{min_row + 1}"
        ws.freeze_panes = freeze_pane_cell

    # 9) Row banding if group_on=True
    grouping_columns = [
        (c_name, column_map[c_name][0])
        for c_name, cfg in column_settings.items()
        if c_name in column_map and cfg.get("group_on", False)
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
                current_fill = fill2 if current_fill == fill1 else fill1 ######## Fill1 and fill2 are used for banding, currently hardcoded but we can make that a parameter ########
                current_key = row_key

            for col_i in range(min_col, max_col + 1):
                ws.cell(row=row_idx, column=col_i).fill = current_fill

    # Finally, save the changes
    wb.save(file_name)


