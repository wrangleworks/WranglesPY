
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
import math


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

    fill1 = PatternFill("solid", fgColor="D9D9D9")
    fill2 = PatternFill("solid", fgColor="BFBFBF")

    medium_black_side = Side(style='medium', color='FF000000')

    default_alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
    default_table_style = TableStyleInfo(
        name="TableStyleMedium9",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=False,
        showColumnStripes=False
    )

    wb = load_workbook(buffer)

    for ws in wb.worksheets:
        # Handle columns that are missing from column_settings (ie Additional_Input)
        column_names = [cell.value for cell in ws[1] if cell.value not in column_settings.keys()]  # Row 1

        for col in column_names:
            column_settings[col] = {'width': 30, 'header_fill_color': 'blue'}

        # Skip if effectively empty
        if ws.max_row == 1 and ws.max_column == 1 and ws['A1'].value is None:
            continue

        # Need at least 2 rows (header + data)
        if (ws.max_row - ws.min_row) < 1:
            print(f"Skipping worksheet '{ws.title}' - not enough data for a table.")
            continue

        min_row, max_row = ws.min_row, ws.max_row
        min_col, max_col = ws.min_column, ws.max_column

        # 1) Define and add the table
        # from string import ascii_letters, digits
        table_name = f"Table_{ws.title.replace(' ', '_')}"
        table_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in table_name)
        if table_name[0].isdigit():
            table_name = f"_{table_name}"

        first_cell = f"{get_column_letter(min_col)}{min_row}"
        last_cell = f"{get_column_letter(max_col)}{max_row}"
        table_ref = f"{first_cell}:{last_cell}"

        tab = Table(displayName=table_name, ref=table_ref)
        tab.tableStyleInfo = default_table_style
        ws.add_table(tab)

        # 2) Default styling for all cells
        for row_cells in ws.iter_rows(min_row=min_row, max_row=max_row,
                                      min_col=min_col, max_col=max_col):
            for cell in row_cells:
                cell.alignment = default_alignment
                cell.font = Font(name='Calibri', size=11, bold=False, color='FF000000')

        # 3) Identify header row & build a column map
        header_row = list(ws.iter_rows(
            min_row=min_row, max_row=min_row,
            min_col=min_col, max_col=max_col
        ))[0]

        column_map = {}
        for idx, header_cell in enumerate(header_row, start=min_col):
            header_text = str(header_cell.value).strip() if header_cell.value else ""
            column_map[header_text] = (idx, get_column_letter(idx))

        # 4) Column-specific settings
        for col_name, settings in column_settings.items():
            if col_name in column_map:
                col_index, col_letter = column_map[col_name]

                # Column width
                ws.column_dimensions[col_letter].width = settings.get("width", 20)

                # Desired alignment, font
                desired_halign = settings.get("horizontal")
                desired_font_size = settings.get("font_size")
                desired_bold = settings.get("bold")

                for cell_tuple in ws.iter_rows(
                    min_row=min_row + 1,
                    max_row=max_row,
                    min_col=col_index,
                    max_col=col_index
                ):
                    cell_obj = cell_tuple[0]

                    # Alignment
                    if desired_halign:
                        curr_align = cell_obj.alignment
                        cell_obj.alignment = Alignment(
                            horizontal=desired_halign,
                            vertical=curr_align.vertical or 'top',
                            wrap_text=curr_align.wrap_text,
                            text_rotation=curr_align.text_rotation,
                            shrink_to_fit=curr_align.shrink_to_fit,
                            indent=curr_align.indent
                        )

                    # Font
                    if desired_font_size or (desired_bold is not None):
                        curr_font = cell_obj.font
                        cell_obj.font = Font(
                            name=curr_font.name,
                            size=desired_font_size if desired_font_size else curr_font.size,
                            bold=desired_bold if desired_bold is not None else curr_font.bold,
                            italic=curr_font.italic,
                            vertAlign=curr_font.vertAlign,
                            underline=curr_font.underline,
                            strike=curr_font.strike,
                            color=curr_font.color
                        )

                    # Number format (if numeric)
                    if "number_format" in settings:
                        if isinstance(cell_obj.value, (int, float)):
                            cell_obj.number_format = settings["number_format"]

                    # If 'hyperlink' is True, convert the cell's text into a hyperlink (prepended with 'https://' if needed).
                    if settings.get("hyperlink", False):
                        if cell_obj.value:
                            # 1) Keep the display text the same as the original cell value
                            display_text = str(cell_obj.value).strip()

                            # 2) Determine the actual hyperlink target
                            if display_text.lower().startswith("http://") or display_text.lower().startswith("https://"):
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
                            cell_obj.alignment = Alignment(
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
            header_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            header_cell.font = Font(name='Calibri', size=12, bold=True, color='FFFFFFFF')

            # Optional header fill
            header_fill_color = column_settings.get(header_text, {}).get("header_fill_color")
            if header_fill_color:
                try:
                    argb = parse_fill_color(header_fill_color)
                    header_cell.fill = PatternFill(fill_type="solid", fgColor=argb)
                except ValueError as ve:
                    print(f"Warning: {ve}. Skipping fill for header '{header_text}'.")

        # 6) Adjust row heights
        for row_idx in range(min_row, max_row + 1):
            max_cell_length = max(
                len(str(ws.cell(row=row_idx, column=col).value or ''))
                for col in range(min_col, max_col + 1)
            )
            calculated_height = math.ceil(max_cell_length / 10) * 15
            ws.row_dimensions[row_idx].height = min(calculated_height, max_row_height)

        # 7) Separator columns
        for col_name, settings in column_settings.items():
            if settings.get("separator_column", False) and col_name in column_map:
                col_index, col_letter = column_map[col_name]
                header_fill_color = settings.get("header_fill_color")
                if header_fill_color:
                    try:
                        border_color = parse_fill_color(header_fill_color)
                    except ValueError:
                        print(f"Warning: Invalid header_fill_color for '{col_name}'. Using black.")
                        border_color = "FF000000"
                else:
                    border_color = "FF000000"

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

        # 8) Freeze panes
        freeze_cols = []
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
                    current_fill = fill2 if current_fill == fill1 else fill1
                    current_key = row_key

                for col_i in range(min_col, max_col + 1):
                    ws.cell(row=row_idx, column=col_i).fill = current_fill

    # Finally, save the changes
    wb.save(file_name)


