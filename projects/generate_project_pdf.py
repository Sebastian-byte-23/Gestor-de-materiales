from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import os
import sqlite3
import json
import uuid
import re
from reportlab.pdfgen import canvas
from datetime import datetime
import pathlib
from projects.data_retrieval import get_project_windows, get_category_tree, get_instances_by_category
from projects.materials_logic import get_applicable_materials
from projects.bom_routes import get_project_materials
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from reportlab.platypus import Flowable
from io import StringIO
import logging
from database_editor.window_drawing import (
    generate_svg,
    FRAME_COLOR,
    GLASS_COLOR,
    GLASS_STROKE,
    DIMENSION_COLOR,
    FRAME_STROKE,
    GLASS_STROKE_WIDTH,
    OVERLAY_STROKE,
    DIMENSION_STROKE,
    DASHED_STROKE,
    OVERLAY_COLOR,
    ARROW_SIZE
)

class SvgFlowable(Flowable):
    def __init__(self, drawing, width, height):
        super().__init__()
        self.drawing = drawing
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        renderPDF.draw(self.drawing, self.canv, 0, 0)

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        import os # Asegura que 'os' esté disponible en este ámbito local
        self.setFont("Helvetica", 8)
        page_width, page_height = self._pagesize

        # Draw logo header image at the top right
        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'logo.png')
        logo_width, logo_height = 35, 35
        logo_x = page_width - 72 - logo_width + 25 # 72 is the right margin used in the document
        logo_y = page_height - logo_height - 25 
        self.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height,
                   preserveAspectRatio=True, mask='auto')

        # Existing code to draw page number at the bottom right
        self.drawRightString(page_width - 72, 30, f"{self.getPageNumber()} de {page_count}")

# Import database connection functions from data_retrieval
from projects.data_retrieval import get_db, get_main_db

def generate_category_number(idx, parent_number=None):
    """Generate hierarchical category number"""
    if parent_number:
        return f"{parent_number}.{idx + 1}"
    return str(idx + 1)

# Using the get_applicable_materials function from materials_logic.py

def add_window_drawing_to_pdf(window, styles):
    """Generate and return a KeepTogether flowable that embeds a window SVG drawing in a side-by-side layout."""
    # Create a container for the window with attributes on left, drawing on right
    window_name = window.get('name', 'Unnamed Window')
    
    # Create a table for the side-by-side layout
    data = [[]]  # Will be a 1x2 table
    
    # Left column: Window attributes
    left_column = []
    left_column.append(Paragraph(window_name, styles['Heading3']))
    
    total_width = window.get('total_width', 1000)
    total_height = window.get('total_height', 1000)
    dimensions_text = f"Dimensions: {total_width}mm x {total_height}mm"
    left_column.append(Paragraph(dimensions_text, styles['Normal']))
    
    finish = window.get('finish', 'White')
    finish_text = f"Terminación: {finish}"
    left_column.append(Paragraph(finish_text, styles['Normal']))
    
    profile = window.get('profile', 'Standard')
    profile_text = f"Perfil: {profile}"
    left_column.append(Paragraph(profile_text, styles['Normal']))
    
    # Add any additional window attributes
    for key, value in window.items():
        # Skip attributes we've already displayed or that are used for the drawing
        if key in ['name', 'total_width', 'total_height', 'finish', 'profile', 
                  'window_type', 'bottom_height', 'left_width', 'pane_states', 'type', 'window_id', 'category_id']:
            continue
        attr_text = f"{key.replace('_', ' ').title()}: {value}"
        left_column.append(Paragraph(attr_text, styles['Normal']))
    
    # Add notes section
    notes_style = ParagraphStyle(
        name='Notes',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        spaceBefore=0.1*inch
    )
    left_column.append(Paragraph("* vista desde afuera hacia adentro", notes_style))
    
    # Create a container for the left column
    left_container = []
    for item in left_column:
        left_container.append(item)
        left_container.append(Spacer(1, 0.05 * inch))
    
    # Right column: Window drawing
    # Prepare parameters for the SVG drawing
    svg_params = {
        'window_type': window.get('window_type', 'single-pane'),
        'total_width': total_width,
        'total_height': total_height,
        'bottom_height': window.get('bottom_height', 400),
        'left_width': window.get('left_width', 500),
        'pane_states': window.get('pane_states', {})
    }
    svg_content = generate_svg(svg_params)
    
    # Calculate element scaling factor based on window width
    # Use 800 as the reference size that looks best
    total_width = float(svg_params.get('total_width', 800))
    total_height = float(svg_params.get('total_height', 800))
    element_scale = max(1.0, max(total_width, total_height) / 1200)
    
    # Scale stroke widths and font sizes based on window size
    scaled_glass_stroke_width = GLASS_STROKE_WIDTH * element_scale
    scaled_frame_stroke = FRAME_STROKE * element_scale
    scaled_dimension_stroke = DIMENSION_STROKE * element_scale
    scaled_overlay_stroke = OVERLAY_STROKE * element_scale
    scaled_font_size = int(64 * element_scale)
    scaled_dash_array_sliding = f"{int(10 * element_scale)},{int(10 * element_scale)}"
    scaled_dash_array_casement = f"{int(4 * element_scale)},{int(8 * element_scale)}"
    
    # Enhance SVG for better PDF rendering using imported styles with scaled values
    svg_content = svg_content.replace('class="glass"', f'class="glass" fill="{GLASS_COLOR}" stroke="{GLASS_STROKE}" stroke-width="{scaled_glass_stroke_width}"')
    svg_content = svg_content.replace('class="frame"', f'class="frame" fill="{FRAME_COLOR}" stroke="{DIMENSION_COLOR}" stroke-width="{scaled_frame_stroke}"')
    svg_content = svg_content.replace('class="dim-line"', f'class="dim-line" stroke="{DIMENSION_COLOR}" stroke-width="{scaled_dimension_stroke}" stroke-dasharray="none"')
    svg_content = svg_content.replace('class="dim-text"', f'class="dim-text" fill="{DIMENSION_COLOR}" font-size="{scaled_font_size}" text-anchor="middle"')
    svg_content = svg_content.replace('class="sliding-arrow"', f'class="sliding-arrow" stroke="{OVERLAY_COLOR}" stroke-width="{scaled_overlay_stroke}" stroke-dasharray="{scaled_dash_array_sliding}" fill="none"')
    svg_content = svg_content.replace('class="casement-line"', f'class="casement-line" stroke="{OVERLAY_COLOR}" stroke-width="{scaled_overlay_stroke}" stroke-dasharray="{scaled_dash_array_casement}" fill="none"')
    
    # Replace marker references with direct arrow paths for better PDF rendering
    svg_content = replace_markers_with_arrows(svg_content, svg_params)
    
    # Add explicit width and height to rect elements
    svg_content = re.sub(r'<rect([^>]*)>', lambda m: ensure_dimensions(m.group(0)), svg_content)
    
    right_container = None
    try:
        # svg2rlg requires a file-like object
        drawing = svg2rlg(StringIO(svg_content))
        
        # Scale drawing to fit within half the page width
        max_width = (A4[0] - 144) / 2  # Half of available width (accounting for margins)
        scale = max_width / drawing.width if drawing.width > max_width else 1.0
    
        # Calculate element scaling factor based on window width
        # Use 800 as the reference size that looks best
        total_width = float(svg_params.get('total_width', 800))
        element_scale = max(1.0, total_width / 800)
    
        # Apply scaling to the drawing
        drawing.width *= scale
        drawing.height *= scale
        drawing.scale(scale, scale)
        right_container = SvgFlowable(drawing, drawing.width, drawing.height)
    except Exception as e:
        logging.error(f"SVG-to-PDF conversion failed for window '{window.get('name', 'Unnamed')}': {e}")
        right_container = Paragraph("Error rendering window drawing.", styles['Normal'])
    
    # Create the table with left and right columns
    data[0] = [left_container, right_container]
    
    # Create the table with appropriate styling
    col_widths = [(A4[0] - 144) * 0.4, (A4[0] - 144) * 0.6]  # 40% for text, 60% for drawing
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
    ]))
    
    # Return the table wrapped in KeepTogether
    return KeepTogether(table)

def replace_markers_with_arrows(svg_content, svg_params=None):
    """Replace marker references with direct arrow paths for better PDF rendering"""
    # Find all dimension lines with markers
    pattern = r'<line([^>]*?)marker-start="url\(#arrowhead-start\)"([^>]*?)marker-end="url\(#arrowhead-end\)"([^>]*?)\/>'
    
    # Also find sliding arrow paths with markers
    path_pattern = r'<path([^>]*?)class="sliding-arrow"([^>]*?)marker-end="url\(#arrowhead-end\)"([^>]*?)\/>'
    
    def add_arrows(match):
        line_attrs = match.group(1) + match.group(2) + match.group(3)
        
        # Extract coordinates
        x1 = re.search(r'x1="([^"]+)"', line_attrs)
        y1 = re.search(r'y1="([^"]+)"', line_attrs)
        x2 = re.search(r'x2="([^"]+)"', line_attrs)
        y2 = re.search(r'y2="([^"]+)"', line_attrs)
        
        if not all([x1, y1, x2, y2]):
            return match.group(0)  # Return original if we can't extract coordinates
            
        x1, y1, x2, y2 = float(x1.group(1)), float(y1.group(1)), float(x2.group(1)), float(y2.group(1))
        
        # Determine if the line is horizontal or vertical
        is_horizontal = abs(y2 - y1) < abs(x2 - x1)
        
        # Extract stroke width if present, otherwise use DIMENSION_STROKE
        stroke_width_match = re.search(r'stroke-width="([^"]+)"', line_attrs)
        stroke_width = float(stroke_width_match.group(1)) if stroke_width_match else DIMENSION_STROKE
        
        # Calculate scaled arrow dimensions based on window size
        total_width = float(svg_params.get('total_width', 800))
        element_scale = max(1.0, total_width / 800)
        
        # Use ARROW_SIZE from window_drawing.py for consistent arrow sizing
        arrow_width = ARROW_SIZE * 0.5 * element_scale  # Reduce arrow size by half
        arrow_height = ARROW_SIZE * 0.25 * element_scale  # Reduce arrow height proportionally
        
        # Create a group with the line and explicit arrow paths
        result = f'<g>\n'
        
        # Original line without markers but preserving all other attributes
        clean_attrs = line_attrs.replace("marker-start=\"url(#arrowhead-start)\"", "").replace("marker-end=\"url(#arrowhead-end)\"", "")
        # Store original coordinates before shortening
        original_x1, original_y1 = x1, y1
        original_x2, original_y2 = x2, y2
        
        # Shorten the line by 10 units on both ends
        if is_horizontal:
            x1 += 10
            x2 -= 10
        else:
            y1 += 10
            y2 -= 10
        result += f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {clean_attrs} />\n'
        
        if is_horizontal:
            # Horizontal line - arrows point left/right using original coordinates
            # Start arrow (triangle pointing right)
            result += f'  <polygon points="{original_x1},{original_y1} {original_x1+arrow_width},{original_y1-arrow_height} {original_x1+arrow_width},{original_y1+arrow_height}" fill="{DIMENSION_COLOR}" stroke="none"/>\n'
            # End arrow (triangle pointing left)
            result += f'  <polygon points="{original_x2},{original_y2} {original_x2-arrow_width},{original_y2-arrow_height} {original_x2-arrow_width},{original_y2+arrow_height}" fill="{DIMENSION_COLOR}" stroke="none"/>\n'
        else:
            # Vertical line - arrows point up/down using original coordinates
            # Start arrow (triangle pointing down)
            result += f'  <polygon points="{original_x1},{original_y1} {original_x1-arrow_height},{original_y1+arrow_width} {original_x1+arrow_height},{original_y1+arrow_width}" fill="{DIMENSION_COLOR}" stroke="none"/>\n'
            # End arrow (triangle pointing up)
            result += f'  <polygon points="{original_x2},{original_y2} {original_x2-arrow_height},{original_y2-arrow_width} {original_x2+arrow_height},{original_y2-arrow_width}" fill="{DIMENSION_COLOR}" stroke="none"/>\n'
        
        result += '</g>'
        return result
    
    # Function to add arrows to sliding paths
    def add_path_arrows(match):
        path_attrs = match.group(1) + match.group(2) + match.group(3)
        
        # Extract path data
        d_match = re.search(r'd="([^"]+)"', path_attrs)
        if not d_match:
            return match.group(0)  # Return original if we can't extract path data
            
        path_data = d_match.group(1)
        
        # Parse the path data to extract start and end points
        # Format is typically "M{start_x} {start_y} L{end_x} {end_y}"
        parts = path_data.split(' ')
        if len(parts) < 4 or not parts[0].startswith('M') or not parts[2].startswith('L'):
            return match.group(0)  # Return original if path format is unexpected
            
        start_x = float(parts[0][1:])  # Remove 'M' prefix
        start_y = float(parts[1])
        end_x = float(parts[2][1:])    # Remove 'L' prefix
        end_y = float(parts[3])
        
        # Determine direction (left-to-right or right-to-left)
        is_left_to_right = start_x < end_x
        
        # Extract stroke properties
        stroke_color = OVERLAY_COLOR
        stroke_match = re.search(r'stroke="([^"]+)"', path_attrs)
        if stroke_match:
            stroke_color = stroke_match.group(1)
            
        # Create a group with the path and explicit arrow paths
        result = f'<g>\n'
        
        # Original path without markers but preserving all other attributes
        clean_attrs = path_attrs.replace('marker-end="url(#arrowhead-end)"', '')
        result += f'  <path {clean_attrs} />\n'
        
        # Calculate scaled arrow dimensions based on window size
        total_width = float(svg_params.get('total_width', 800))
        element_scale = max(1.0, total_width / 800)
        
        # Arrow dimensions scaled by element_scale
        arrow_width = ARROW_SIZE * 0.5 * element_scale
        arrow_height = ARROW_SIZE * 0.25 * element_scale
        
        # Add only the end arrow
        if is_left_to_right:
            # End arrow (triangle pointing right)
            result += f'  <polygon points="{end_x},{end_y} {end_x-arrow_width},{end_y-arrow_height} {end_x-arrow_width},{end_y+arrow_height}" fill="{stroke_color}" stroke="none"/>\n'
        else:
            # End arrow (triangle pointing left)
            result += f'  <polygon points="{end_x},{end_y} {end_x+arrow_width},{end_y-arrow_height} {end_x+arrow_width},{end_y+arrow_height}" fill="{stroke_color}" stroke="none"/>\n'
        
        result += '</g>'
        return result
    
    # If svg_params is None, use default values
    if svg_params is None:
        svg_params = {'total_width': 800}
    
    # Replace all dimension lines with explicit arrow paths
    modified_svg = re.sub(pattern, add_arrows, svg_content)
    
    # Replace all sliding arrow paths with explicit arrow paths
    modified_svg = re.sub(path_pattern, add_path_arrows, modified_svg)
    
    # Remove the marker definitions since we're not using them anymore
    modified_svg = re.sub(r'<marker id="arrowhead-start".*?</marker>', '', modified_svg, flags=re.DOTALL)
    modified_svg = re.sub(r'<marker id="arrowhead-end".*?</marker>', '', modified_svg, flags=re.DOTALL)
    
    return modified_svg

def ensure_dimensions(rect_tag):
    """Ensure rect elements have explicit width and height attributes"""
    if 'width=' not in rect_tag:
        rect_tag = rect_tag.replace('>', ' width="100">')
    if 'height=' not in rect_tag:
        rect_tag = rect_tag.replace('>', ' height="100">')
    
    # Ensure fill and stroke are explicitly set
    if 'fill=' not in rect_tag:
        if 'class="glass"' in rect_tag:
            rect_tag = rect_tag.replace('>', f' fill="{GLASS_COLOR}">')
        elif 'class="frame"' in rect_tag:
            rect_tag = rect_tag.replace('>', f' fill="{FRAME_COLOR}">')
        else:
            rect_tag = rect_tag.replace('>', ' fill="none">')
    
    if 'stroke=' not in rect_tag:
        if 'class="glass"' in rect_tag:
            rect_tag = rect_tag.replace('>', f' stroke="{GLASS_STROKE}">')
        elif 'class="frame"' in rect_tag:
            rect_tag = rect_tag.replace('>', f' stroke="{DIMENSION_COLOR}">')
        else:
            rect_tag = rect_tag.replace('>', f' stroke="{DIMENSION_COLOR}">')
    
    # Ensure stroke-width is set
    if 'stroke-width=' not in rect_tag:
        if 'class="glass"' in rect_tag:
            rect_tag = rect_tag.replace('>', f' stroke-width="{GLASS_STROKE_WIDTH}">')
        elif 'class="frame"' in rect_tag:
            rect_tag = rect_tag.replace('>', f' stroke-width="{FRAME_STROKE}">')
        else:
            rect_tag = rect_tag.replace('>', f' stroke-width="{DIMENSION_STROKE}">')
    
    return rect_tag

def create_pdf(project_id, output_path=None, report_type='full'):
    """Create a PDF document for a project overview with specified report type"""
    db = get_db()
    main_db = get_main_db()
    
    # Get all material quantities for this project
    material_quantities = {}
    try:
        # Connect directly to the database instead of using the route function
        conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'projects.db'))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT material_id, quantity 
            FROM Bill_Of_Materials
            WHERE project_id = ?
            """, 
            (project_id,)
        )
        
        for row in cursor.fetchall():
            material_quantities[row['material_id']] = row['quantity']
        
        conn.close()
    except Exception as e:
        print(f"Error fetching BOM data: {e}")

    # Get project details
    project = db.execute('SELECT * FROM Projects WHERE project_id = ?', (project_id,)).fetchone()
    if not project:
        raise ValueError(f"Project with ID {project_id} not found")
    
    # Format the date as YYYY.MM.DD
    current_date = datetime.now().strftime("%Y.%m.%d")
    
    # Create filename with format based on report type
    if output_path is None:
        # Get the Downloads folder path
        downloads_path = os.path.join(pathlib.Path.home(), "Downloads")
        if report_type == 'commercial':
            filename = f"[{current_date}] EETT {project['name']}.pdf"
        else:  # full report
            filename = f"[{current_date}] EETT Full {project['name']}.pdf"
        output_path = os.path.join(downloads_path, filename)
    
    # Create the PDF document with title metadata
    if report_type == 'commercial':
        pdf_title = f"[{current_date}] EETT {project['name']}"
    else:  # full report
        pdf_title = f"[{current_date}] EETT Full {project['name']}"
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=A4,
        rightMargin=72, 
        leftMargin=72,
        topMargin=60, 
        bottomMargin=50,
        title=pdf_title  # Set PDF title for both file metadata and browser display
    )

    # Get styles
    styles = getSampleStyleSheet()

    # Define custom styles if they don't exist
    custom_styles = {
        'Heading1': ParagraphStyle(name='Heading1', fontSize=25, spaceAfter=4, fontName='Courier'),
        'Heading2': ParagraphStyle(name='Heading2', fontSize=10, spaceAfter=4),
        'Normal': ParagraphStyle(name='Normal', fontSize=8, spaceAfter=0, spaceBefore=0),
        'TableHeader': ParagraphStyle(name='TableHeader', fontSize=8, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceBefore=0, spaceAfter=0)
    }

    # Add styles that don't already exist
    for style_name, style in custom_styles.items():
        if style_name not in styles:
            styles.add(style)
        else:
            # Override existing style with our custom properties
            for attr, value in style.__dict__.items():
                if attr != 'name' and not attr.startswith('_'):
                    setattr(styles[style_name], attr, value)

    # Initialize document content
    story = []

    # Define a style for the project name (bold and different font)
    project_name_style = ParagraphStyle(
        name='ProjectName',
        fontSize=25,
        fontName='Courier-Bold',  # Using Helvetica-Bold
        spaceAfter=6,
    )

    # Cover page: display title, project name, and date
    cover_title = Paragraph("Especificaciones Técnicas", styles['Heading1'])
    project_name = Paragraph(project['name'], project_name_style)  # Apply the new style
    current_date = Paragraph(datetime.now().strftime("%Y/%m/%d"), styles['Heading1'])

    story.append(Spacer(1, 1*inch))  # Adjust vertical spacing as needed
    story.append(cover_title)
    story.append(Spacer(1, 0.5*inch))
    story.append(project_name)
    story.append(Spacer(1, 0.5*inch))
    story.append(current_date)
    story.append(PageBreak())

    # Process categories with instances
    def process_category_tree(category_list, parent_number=None):
        result = []
        category_index = 0  # Use a separate counter for category numbering
        
        for category in category_list:
            # Generate category number
            current_number = generate_category_number(category_index, parent_number)

            # Get instances for this category
            instances_data = get_instances_by_category(project_id, category['id'])

            # Combine item and accessory instances
            all_instances = []

            # Process item instances
            for item_instance in instances_data['item_instances']:
                # Get attributes for this instance
                attrs = db.execute('''
                    SELECT name, value FROM Item_Instance_Attributes
                    WHERE instance_id = ?
                ''', (item_instance['instance_id'],)).fetchall()

                # Get full instance details
                instance = db.execute('''
                    SELECT * FROM Item_Instances WHERE instance_id = ?
                ''', (item_instance['instance_id'],)).fetchone()

                if instance:
                    # Get linked accessories for this item instance
                    linked_accessories = []
                    accessory_instances = db.execute('''
                        SELECT DISTINCT a.accessory_instance_id, a.name, a.installation,
                               a.description, a.short_description, a.accessory_id
                        FROM Accessory_Instance a
                        JOIN Accessory_Instance_Attributes attr ON a.accessory_instance_id = attr.accessory_instance_id
                        WHERE attr.application = ?
                    ''', (str(instance['instance_id']),)).fetchall()

                    for acc in accessory_instances:
                        # Get accessory attributes specific to this item instance
                        acc_attrs = db.execute('''
                            SELECT name, value, group_id
                            FROM Accessory_Instance_Attributes
                            WHERE accessory_instance_id = ? AND application = ?
                        ''', (acc['accessory_instance_id'], str(instance['instance_id']))).fetchall()

                        # Get category name from main database
                        category_info = main_db.execute('''
                            SELECT c.name
                            FROM Accesory_Item ai
                            JOIN Categories c ON ai.category_id = c.category_id
                            WHERE ai.accesory_id = ?
                        ''', (acc['accessory_id'],)).fetchone()

                        # Group attributes by group_id
                        acc_attribute_groups = {}
                        for attr in acc_attrs:
                            group_id = attr['group_id'] if attr['group_id'] is not None else 'default'
                            if group_id not in acc_attribute_groups:
                                acc_attribute_groups[group_id] = {
                                    'group_id': group_id,
                                    'application': str(instance['instance_id']),
                                    'application_name': instance['name'],
                                    'attributes': []
                                }
                            acc_attribute_groups[group_id]['attributes'].append({
                                'name': attr['name'],
                                'value': json.loads(attr['value'])[0]
                            })

                        linked_accessories.append({
                            'accessory_id': acc['accessory_id'],
                            'name': acc['name'],
                            'category_name': category_info['name'] if category_info else 'Uncategorized',
                            'instance_id': acc['accessory_instance_id'],
                            'attribute_groups': list(acc_attribute_groups.values())
                        })

                    # Build attribute dict for material evaluation
                    item_attr_dict = { attr['name']: json.loads(attr['value'])[0] for attr in attrs }
                    material_list = get_applicable_materials('item', instance['item_id'], item_attr_dict, main_db)

                    all_instances.append({
                        'name': instance['name'],
                        'short_name': instance['short_name'],
                        'description': instance['description'],
                        'short_description': instance['short_description'],
                        'installation': instance['installation'],
                        'type': 'Item',
                        'attributes': [{'name': attr['name'], 'value': json.loads(attr['value'])[0]} for attr in attrs],
                        'materials': material_list,
                        'linked_accessories': linked_accessories
                    })

            # Process accessory instances
            for acc_instance in instances_data['accessory_instances']:
                # Get full instance details
                instance = db.execute('''
                    SELECT * FROM Accessory_Instance WHERE accessory_instance_id = ?
                ''', (acc_instance['instance_id'],)).fetchone()

                if instance:
                    # Get all attributes with group_id for this accessory
                    attrs = db.execute('''
                        SELECT name, value, application, group_id
                        FROM Accessory_Instance_Attributes
                        WHERE accessory_instance_id = ?
                        ORDER BY group_id
                    ''', (acc_instance['instance_id'],)).fetchall()

                    # Group attributes by group_id while maintaining order
                    attribute_groups = []
                    current_group = None
                    for attr in attrs:
                        group_id = attr['group_id'] if attr['group_id'] is not None else str(uuid.uuid4())
                        if group_id != current_group:
                            # Get application name for display
                            application = attr['application'] if attr['application'] is not None else ''
                            application_name = application

                            # If application is a numeric string (item ID), look up the item name
                            if application and application.isdigit():
                                item_instance = db.execute('''
                                    SELECT name
                                    FROM Item_Instances
                                    WHERE instance_id = ?
                                ''', (application,)).fetchone()

                                if item_instance:
                                    application_name = item_instance['name']
                            # For standalone accessory with no application, use installation
                            elif not application or application == '':
                                application_name = instance['installation'] if instance['installation'] else 'General'

                            attribute_groups.append({
                                'group_id': group_id,
                                'application': attr['application'],
                                'application_name': application_name,
                                'attributes': []
                            })
                            current_group = group_id
                        attribute_groups[-1]['attributes'].append({
                            'name': attr['name'],
                            'value': json.loads(attr['value'])[0],
                            'application': attr['application']
                        })

                    material_dict = {}
                    for group in attribute_groups:
                        # Build a dict from this group's attributes
                        group_attrs = { attr['name']: attr['value'] for attr in group['attributes'] }
                        group_materials = get_applicable_materials('accessory', instance['accessory_id'], group_attrs, main_db)
                        for material in group_materials:
                            material_id = material['material_id']
                            if material_id not in material_dict:
                                material_dict[material_id] = material
                    material_list = list(material_dict.values())

                    all_instances.append({
                        'name': instance['name'],
                        'short_name': instance['short_name'],
                        'description': instance['description'],
                        'short_description': instance['short_description'],
                        'installation': instance['installation'],
                        'type': 'Accessory',
                        'attribute_groups': attribute_groups,
                        'materials': material_list
                    })

            # Sort instances by name
            all_instances.sort(key=lambda x: x['name'])

            # Process subcategories recursively
            subcategories = []
            if 'children' in category:
                subcategories = process_category_tree(category['children'], parent_number=current_number)

            # Create category object with instances and subcategories
            cat_obj = {
                'id': category['id'],
                'name': category['name'],
                'instances': all_instances,
                'subcategories': subcategories,
                'number': current_number
            }

            # Only add categories that have instances or subcategories with instances
            has_instances = bool(all_instances)
            has_subcategories_with_instances = any(subcategories)

            if has_instances or has_subcategories_with_instances:
                result.append(cat_obj)
                category_index += 1  # Only increment the counter when we add a category

        return result

    # Get the category tree and process it
    category_tree = get_category_tree()
    categories = process_category_tree(category_tree)

    # Add Windows category if project windows exist
    windows_list = get_project_windows(project_id)
    if windows_list:
        # Mark each window with a type for later processing
        for win in windows_list:
            win['type'] = 'Window'
        # Generate a sequential category number for the Windows category
        new_category_number = generate_category_number(len(categories))
        window_category = {
             'id': 'windows',       # A dummy id
             'name': 'Ventanas',
             'instances': windows_list,
             'subcategories': [],
             'number': new_category_number,  # Sequential category number
             'path': ['Windows']
        }
        categories.append(window_category)
        
    # Add categories and instances to the PDF
    def add_category_to_pdf(category, level=0):
        # Create a new style for category headings based on Heading2
        category_heading_style = ParagraphStyle(
            name=f'CategoryHeading{level}',
            parent=styles['Heading2'],
            spaceBefore=0.05*inch,  # Reduced space before
            spaceAfter=0.025*inch   # Reduced space after
        )
        # Add category header
        category_heading = Paragraph(
            f"{category['number']} {category['name']}",
            styles['Heading3']  # Use Heading3 for categories
        )
        story.append(category_heading)

        # Add instances
        # For windows, we'll create a special layout with two windows per row
        if category['id'] == 'windows':
            # Process windows in pairs
            windows = category['instances']
            for i in range(0, len(windows), 2):
                row_flowables = []
                
                # First window in the pair
                first_window = windows[i]
                first_window_flowable = add_window_drawing_to_pdf(first_window, styles)
                row_flowables.append(first_window_flowable)
                
                # Add a page break after each pair (or single window if odd number)
                if i + 1 < len(windows):
                    # Second window in the pair
                    second_window = windows[i + 1]
                    second_window_flowable = add_window_drawing_to_pdf(second_window, styles)
                    row_flowables.append(second_window_flowable)
                
                # Add the windows to the story
                for flowable in row_flowables:
                    story.append(flowable)
                
                # Add page break after each pair (or single window if odd number)
                story.append(PageBreak())
        else:
            # Regular instances (non-windows)
            for idx, instance in enumerate(category['instances']):
                instance_flowables = []  # Initialize container for this instance
                instance_number = f"{category['number']}.{idx+1}"
                # Get instance name based on report type for items/accessories
                if report_type == 'commercial' and instance.get('short_name'):
                    display_name = instance['short_name']
                else:
                    display_name = instance['name']
                instance_flowables.append(Paragraph(
                    f"{instance_number} {display_name}",
                    category_heading_style
                ))

                # Add description based on report type
                if report_type == 'commercial':
                    if instance.get('short_description'):
                        short_description_text = instance['short_description'].replace('\n', '<br />')
                        instance_flowables.append(Paragraph(short_description_text, styles['Normal']))
                        instance_flowables.append(Spacer(1, 0.02*inch))
                    elif instance.get('description'):
                        description_text = instance['description'].replace('\n', '<br />')
                        instance_flowables.append(Paragraph(description_text, styles['Normal']))
                        instance_flowables.append(Spacer(1, 0.02*inch))
                else:  # Full report
                    if instance.get('description'):
                        description_text = instance['description'].replace('\n', '<br />')
                        instance_flowables.append(Paragraph(description_text, styles['Normal']))
                        instance_flowables.append(Spacer(1, 0.02*inch))

                # Add installation instructions only in full report
                if report_type != 'commercial' and instance.get('installation'):
                    instance_flowables.append(Paragraph(instance['installation'].replace('\n', '<br />'), styles['Normal']))
                    instance_flowables.append(Spacer(1, 0.02*inch))

                # Add attributes based on instance type
                if instance['type'] == 'Item':
                    # Create attributes table
                    if instance['attributes']:
                        # Create table data
                        data = [[Paragraph(attr['name'], styles['TableHeader']) for attr in instance['attributes']]]
                        data.append([Paragraph(str(attr['value']), styles['Normal']) for attr in instance['attributes']])

                        # Create the table
                        table = Table(data)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('SPACEAFTER', (0, 0), (-1, -1), 0.1*inch),
                        ]))
                        instance_flowables.append(table)
                        instance_flowables.append(Spacer(1, 0.1*inch))

                    # Add materials if present - only in full report
                    if report_type != 'commercial' and instance.get('materials'):
                        # Check if any materials have quantities
                        has_quantities = any(material_quantities.get(material['material_id'], '') for material in instance['materials'])
                        
                        # Define headers based on whether quantities exist
                        if has_quantities:
                            mat_data = [['Material', 'Código', 'Cantidades', 'Unidad']]
                        else:
                            mat_data = [['Material', 'Código']]
                        
                        for material in instance['materials']:
                            material_id = material['material_id']
                            quantity = material_quantities.get(material_id, '')
                            units = material.get('units', material.get('Units', ''))
                            
                            if has_quantities:
                                mat_data.append([
                                    material['material_name'], 
                                    material['SKU'],
                                    str(quantity) if quantity else '',
                                    units
                                ])
                            else:
                                mat_data.append([
                                    material['material_name'], 
                                    material['SKU']
                                ])

                        mat_table = Table(mat_data)
                        mat_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 8),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('SPACEAFTER', (0, 0), (-1, -1), 0.1*inch),
                        ]))
                        instance_flowables.append(mat_table)
                        instance_flowables.append(Spacer(1, 0.1*inch))

                    # Add linked accessories if present
                    if instance.get('linked_accessories'):
                        # Consolidate linked accessories for this item instance by grouping on (accessory_id, instance_id)
                        accessory_groups = {}
                        for accessory in instance['linked_accessories']:
                            key = (accessory['accessory_id'], accessory['instance_id'])
                            accessory_groups.setdefault(key, []).append(accessory)
                            
                        for (acc_id, inst_id), accessories in accessory_groups.items():
                            # Use the first accessory from the group to create the header
                            first_accessory = accessories[0]
                            acc_heading_text = f"{first_accessory['category_name']}: {first_accessory['name']}"
                            instance_flowables.append(Paragraph(acc_heading_text, styles['Normal']))

                            # Consolidate all attribute groups (by group_id) from accessories of the same instance
                            consolidated_groups = {}
                            for accessory in accessories:
                                for group in accessory.get('attribute_groups', []):
                                    group_key = group['group_id']
                                    consolidated_groups[group_key] = group  # Keep one occurrence per unique group_id
                                
                            # Derive table header from the first consolidated group if available
                            first_group = next(iter(consolidated_groups.values()), None)
                            if first_group and first_group.get('attributes'):
                                headers = [attr['name'] for attr in first_group['attributes']]
                            else:
                                headers = []
                                
                            if headers:
                                table_data = []
                                # Header row
                                table_data.append([Paragraph(header, styles['TableHeader']) for header in headers])
                                # One row for each unique group (sorted by group_id for consistency)
                                for group_id, group in sorted(consolidated_groups.items()):
                                    row = [Paragraph(str(attr['value']), styles['Normal']) for attr in group['attributes']]
                                    table_data.append(row)
                                    
                                table = Table(table_data)
                                table.setStyle(TableStyle([
                                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                    ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
                                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                    ('SPACEAFTER', (0, 0), (-1, -1), 0.1*inch),
                                ]))
                                instance_flowables.append(table)
                                instance_flowables.append(Spacer(1, 0.1*inch))
                else:
                    if report_type != 'commercial':
                        # Accessory instance with attribute groups
                        all_attr_names = []
                        if instance.get('attribute_groups'):
                            # Get all unique attribute names across all groups
                            all_attr_names_set = set()
                            for group in instance.get('attribute_groups', []):
                                for attr in group['attributes']:
                                    all_attr_names_set.add(attr['name'])

                            # Sort attribute names for consistent column order
                            all_attr_names = sorted(list(all_attr_names_set))

                        # Create header row with "Application" and all attribute names
                        table_data = [[
                            Paragraph("Aplicación", styles['TableHeader']),
                            *[Paragraph(name, styles['TableHeader']) for name in all_attr_names]
                        ]]

                        # Add a row for each application group
                        for group in instance.get('attribute_groups', []):
                            if group['attributes']:
                                row = [Paragraph(group['application_name'], styles['Normal'])]

                                # For each attribute name, find corresponding value or empty
                                for attr_name in all_attr_names:
                                    value = next((str(attr['value']) for attr in group['attributes']
                                                 if attr['name'] == attr_name), '')
                                    row.append(Paragraph(value, styles['Normal']))

                                table_data.append(row)

                        # Create the table with column widths that fit the page
                        if len(table_data) > 1:  # Only create table if we have data rows
                            # Calculate column widths - first column wider, others equal
                            col_widths = [1.5*inch]  # Wider first column for "Aplicación"
                            remaining_width = doc.width - 1.5*inch - 72  # Subtract margins
                            if all_attr_names:
                                col_widths.extend([remaining_width/len(all_attr_names)] * len(all_attr_names))
                            
                            consolidated_table = Table(table_data, colWidths=col_widths)
                            consolidated_table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, -1), 7),  # Smaller font size
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('SPACEAFTER', (0, 0), (-1, -1), 0.1*inch),
                                ('WORDWRAP', (0, 0), (-1, -1), True),  # Enable word wrap
                            ]))
                            
                            # Split table if too tall
                            if len(table_data) > 15:  # If more than 15 rows
                                split_tables = []
                                for i in range(0, len(table_data), 15):
                                    chunk = table_data[i:i+15]
                                    if i > 0:  # Add header to subsequent chunks
                                        chunk.insert(0, table_data[0])
                                    split_tables.append(Table(chunk, colWidths=col_widths))
                                
                                for table in split_tables:
                                    table.setStyle(consolidated_table.getStyle())
                                    instance_flowables.append(table)
                                    instance_flowables.append(Spacer(1, 0.1*inch))
                            else:
                                instance_flowables.append(consolidated_table)
                                instance_flowables.append(Spacer(1, 0.1*inch))

                    # Add materials if present (skipped in commercial report)
                    if report_type != 'commercial' and instance.get('materials'):
                        # Check if any materials have quantities
                        has_quantities = any(material_quantities.get(material['material_id'], '') for material in instance['materials'])
                        
                        # Define headers based on whether quantities exist
                        if has_quantities:
                            mat_data = [['Material', 'SKU', 'Quantity', 'Units']]
                        else:
                            mat_data = [['Material', 'SKU']]
                        
                        for material in instance['materials']:
                            material_id = material['material_id']
                            quantity = material_quantities.get(material_id, '')
                            units = material.get('units', material.get('Units', ''))
                            
                            if has_quantities:
                                mat_data.append([
                                    material['material_name'], 
                                    material['SKU'],
                                    str(quantity) if quantity else '',
                                    units
                                ])
                            else:
                                mat_data.append([
                                    material['material_name'], 
                                    material['SKU']
                                ])

                        mat_table = Table(mat_data)
                        mat_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 8),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('SPACEAFTER', (0, 0), (-1, -1), 0.05*inch),
                        ]))
                        instance_flowables.append(mat_table)
                        instance_flowables.append(Spacer(1, 0.05*inch))

                story.append(KeepTogether(instance_flowables))
                story.append(Spacer(1, 0.05*inch))

        # Process subcategories
        for subcategory in category['subcategories']:
            add_category_to_pdf(subcategory, level=level+1)

    # Add each category
    for category in categories:
        add_category_to_pdf(category)

    # Build and save the PDF
    doc.build(story, canvasmaker=NumberedCanvas)

    main_db.close()
    db.close()

    return output_path

# The create_pdf function is now the main entry point
def generate_project_pdf(project_id, output_path=None, report_type='full'):
    """Wrapper function to maintain compatibility with existing code"""
    return create_pdf(project_id, output_path, report_type)


