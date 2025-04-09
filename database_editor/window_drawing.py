# Window structure dimensions
FRAME = 100          # Outer frame thickness
DIVIDER = 100        # Divider (mullion) thickness between panes

# Stroke widths
FRAME_STROKE = 2.5
GLASS_STROKE_WIDTH = 7
OVERLAY_STROKE = 8
DIMENSION_STROKE = 4
DASHED_STROKE = 15

# Arrow dimensions (absolute units)
ARROW_SIZE = 45  # Controls the visual size of arrowheads

# Colors
FRAME_COLOR = "#f0f0f0"  # Light gray for frame
GLASS_COLOR = "#ffffff"  # White for glass
GLASS_STROKE = "#808080" # Medium gray for glass borders
OVERLAY_COLOR = "#666"   # Gray for overlay indicators
DIMENSION_COLOR = "#333" # Dark gray for dimension lines

# Dimensioning offsets - base values
OUTER_OFFSET_BASE = 50       # Base offset for outer dimension lines
INNER_OFFSET_BASE = 50       # Base offset for inner dimension lines
OUTER_TEXT_OFFSET_BASE = 30  # Base offset for outer dimension text
INNER_TEXT_OFFSET_BASE = 10  # Base offset for inner dimension text
MARGIN_BASE = 200            # Base margin for SVG viewBox

# Arrow and overlay positioning
ARROW_OFFSET = 40       # Offset for sliding arrow positioning
ARROW_MARKER_WIDTH = ARROW_SIZE
ARROW_MARKER_HEIGHT = ARROW_SIZE * 0.7
ARROW_MARKER_REF_X_START = 0
ARROW_MARKER_REF_Y = ARROW_SIZE * 0.35
ARROW_MARKER_REF_X_END = ARROW_SIZE - OVERLAY_STROKE
ARROW_MARKER_POLYGON_POINTS_START = f"{ARROW_SIZE} 0, 0 {ARROW_SIZE * 0.35}, {ARROW_SIZE} {ARROW_SIZE * 0.7}"
ARROW_MARKER_POLYGON_POINTS_END = f"0 0, {ARROW_SIZE} {ARROW_SIZE * 0.35}, 0 {ARROW_SIZE * 0.7}"
ARROW_FILL_COLOR = "#333"

def generate_svg(params):
    """Generates an SVG image of a window based on the given parameters."""

    window_type = params.get('window_type')
    total_height = int(params.get('total_height', 1000))
    total_width = int(params.get('total_width', 1000))
    bottom_outer = int(params.get('bottom_height', 400))
    left_outer = int(params.get('left_width', 500))
    pane_states = params.get('pane_states', {})
    
    # Calculate scaling factor based on window dimensions
    # Use 1000x1000 as the reference size
    size_factor = max(total_width, total_height) / 1000
    size_factor = max(1.0, size_factor)  # Don't scale down for small windows
    
    # Scale offsets based on window size
    OUTER_OFFSET = int(OUTER_OFFSET_BASE * size_factor)
    INNER_OFFSET = int(INNER_OFFSET_BASE * size_factor)
    OUTER_TEXT_OFFSET = int(OUTER_TEXT_OFFSET_BASE * size_factor)
    INNER_TEXT_OFFSET = int(INNER_TEXT_OFFSET_BASE * size_factor)
    MARGIN = int(MARGIN_BASE * size_factor)

    # Compute the glass (inner) dimensions.
    if window_type == 'single-pane' or window_type == 'two-pane':
        glass_height = total_height - 2 * FRAME
    elif window_type == 'two-pane-vertical' or window_type == 'three-pane':
        glass_height = total_height - 2 * FRAME - DIVIDER

    if window_type == 'single-pane' or window_type == 'two-pane-vertical' or window_type == 'three-pane':
        glass_width = total_width - 2 * FRAME
    elif window_type == 'two-pane':
        glass_width = total_width - 2 * FRAME - DIVIDER

    if window_type == 'two-pane-vertical' or window_type == 'three-pane':
        top_glass = (total_height - bottom_outer) - FRAME - (DIVIDER / 2)
        bottom_glass = bottom_outer - FRAME - (DIVIDER / 2)

    if window_type == 'two-pane' or window_type == 'three-pane':
        left_glass = left_outer - FRAME - (DIVIDER / 2)
        right_glass = (total_width - left_outer) - FRAME - (DIVIDER / 2)

    # Set the SVG viewBox (we use a margin so that all dimension lines are visible).
    svg_content = f'<svg viewBox="{-MARGIN} {-MARGIN} {total_width + 2 * MARGIN} {total_height + 2 * MARGIN}" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">'

    # SVG Definitions
    svg_content += f'''
    <defs>
      <marker id="arrowhead-start" markerWidth="{ARROW_MARKER_WIDTH}" markerHeight="{ARROW_MARKER_HEIGHT}" 
              refX="{ARROW_MARKER_REF_X_START}" refY="{ARROW_MARKER_REF_Y}" orient="auto" markerUnits="userSpaceOnUse">
        <polygon points="{ARROW_MARKER_POLYGON_POINTS_START}" fill="{ARROW_FILL_COLOR}"/>
      </marker>
      <marker id="arrowhead-end" markerWidth="{ARROW_MARKER_WIDTH}" markerHeight="{ARROW_MARKER_HEIGHT}" 
              refX="{ARROW_MARKER_REF_X_END}" refY="{ARROW_MARKER_REF_Y}" orient="auto" markerUnits="userSpaceOnUse">
        <polygon points="{ARROW_MARKER_POLYGON_POINTS_END}" fill="{ARROW_FILL_COLOR}"/>
      </marker>
    </defs>
    '''

    # Outer Frame
    svg_content += f'<rect class="frame" x="0" y="0" width="{total_width}" height="{total_height}" />'

    # --- Helper function for opening overlays ---
    def get_overlay_path(state, x, y, width, height):
        if state == 'left':
            return f'<path d="M{x+width-ARROW_OFFSET} {y+height/2} L{x+ARROW_OFFSET} {y+height/2}" stroke="{OVERLAY_COLOR}" stroke-width="{OVERLAY_STROKE}" stroke-dasharray="15,20" fill="none" marker-end="url(#arrowhead-end)" />'
        elif state == 'right':
            return f'<path d="M{x+ARROW_OFFSET} {y+height/2} L{x+width-ARROW_OFFSET} {y+height/2}" stroke="{OVERLAY_COLOR}" stroke-width="{OVERLAY_STROKE}" stroke-dasharray="15,20" fill="none" marker-end="url(#arrowhead-end)" />'
        elif state == 'casement-left':
            return f'<path d="M{x+width} {y} L{x} {y+height/2} L{x+width} {y+height}" stroke="{OVERLAY_COLOR}" stroke-width="{OVERLAY_STROKE}" stroke-dasharray="15,20" fill="none" />'
        elif state == 'casement-right':
            return f'<path d="M{x} {y} L{x+width} {y+height/2} L{x} {y+height}" stroke="{OVERLAY_COLOR}" stroke-width="{OVERLAY_STROKE}" stroke-dasharray=""15,20" fill="none" />'
        elif state == 'awning':
            return f'<path d="M{x} {y+height} L{x+width/2} {y} L{x+width} {y+height}" stroke="{OVERLAY_COLOR}" stroke-width="{OVERLAY_STROKE}" stroke-dasharray="15,20" fill="none" />'
        elif state == 'awning-down':
            return f'<path d="M{x} {y} L{x+width/2} {y+height} L{x+width} {y}" stroke="{OVERLAY_COLOR}" stroke-width="{OVERLAY_STROKE}" stroke-dasharray="15,20" fill="none" />'
        return ''

    # --- Draw the glass areas and overlays ---
    if window_type == 'single-pane':
        x, y, w, h = FRAME, FRAME, total_width - 2 * FRAME, total_height - 2 * FRAME
        svg_content += f'<rect class="glass" x="{x}" y="{y}" width="{w}" height="{h}" fill="{GLASS_COLOR}" stroke="{GLASS_STROKE}" stroke-width="{GLASS_STROKE_WIDTH}"/>'
        svg_content += get_overlay_path(pane_states.get('pane_single', 'none'), x, y, w, h)
    elif window_type == 'two-pane':
        x, y, w, h = FRAME, FRAME, left_glass, total_height - 2 * FRAME
        svg_content += f'<rect class="glass" x="{x}" y="{y}" width="{w}" height="{h}" fill="{GLASS_COLOR}" stroke="{GLASS_STROKE}" stroke-width="{GLASS_STROKE_WIDTH}" />'
        svg_content += get_overlay_path(pane_states.get('pane_left', 'none'), x, y, w, h)
        x = left_outer + (DIVIDER / 2)
        w = right_glass
        svg_content += f'<rect class="glass" x="{x}" y="{FRAME}" width="{w}" height="{total_height - 2 * FRAME}" fill="{GLASS_COLOR}" stroke="{GLASS_STROKE}" stroke-width="{GLASS_STROKE_WIDTH}" />'
        svg_content += get_overlay_path(pane_states.get('pane_right', 'none'), x, FRAME, w, total_height - 2 * FRAME)
    elif window_type == 'two-pane-vertical':
        x, y, w, h = FRAME, FRAME, total_width - 2 * FRAME, top_glass
        svg_content += f'<rect class="glass" x="{x}" y="{y}" width="{w}" height="{h}" fill="{GLASS_COLOR}" stroke="{GLASS_STROKE}" stroke-width="{GLASS_STROKE_WIDTH}" />'
        svg_content += get_overlay_path(pane_states.get('pane_top', 'none'), x, y, w, h)
        y = total_height - bottom_outer + (DIVIDER / 2)
        h = bottom_glass
        svg_content += f'<rect class="glass" x="{FRAME}" y="{y}" width="{w}" height="{h}" fill="{GLASS_COLOR}" stroke="{GLASS_STROKE}" stroke-width="{GLASS_STROKE_WIDTH}" />'
        svg_content += get_overlay_path(pane_states.get('pane_bottom', 'none'), FRAME, y, w, h)
    elif window_type == 'three-pane':
        x, y, w, h = FRAME, FRAME, left_glass, total_height - bottom_outer - FRAME - (DIVIDER / 2)
        svg_content += f'<rect class="glass" x="{x}" y="{y}" width="{w}" height="{h}" fill="{GLASS_COLOR}" stroke="{GLASS_STROKE}" stroke-width="{GLASS_STROKE_WIDTH}" />'
        svg_content += get_overlay_path(pane_states.get('pane_topLeft', 'none'), x, y, w, h)
        x = left_outer + (DIVIDER / 2)
        w = right_glass
        svg_content += f'<rect class="glass" x="{x}" y="{FRAME}" width="{w}" height="{h}" fill="{GLASS_COLOR}" stroke="{GLASS_STROKE}" stroke-width="{GLASS_STROKE_WIDTH}" />'
        svg_content += get_overlay_path(pane_states.get('pane_topRight', 'none'), x, y, w, h)
        x, y, w, h = FRAME, total_height - bottom_outer + (DIVIDER / 2), total_width - 2 * FRAME, bottom_glass
        svg_content += f'<rect class="glass" x="{x}" y="{y}" width="{w}" height="{h}" fill="{GLASS_COLOR}" stroke="{GLASS_STROKE}" stroke-width="{GLASS_STROKE_WIDTH}" />'
        svg_content += get_overlay_path(pane_states.get('pane_bottom', 'none'), x, y, w, h)

    # --- Outer Dimension Lines ---
    # Calculate additional offset for bottom text based on window width
    # Only scale the total width dimension text offset as it can clip into the window
    bottom_text_offset = OUTER_TEXT_OFFSET + int(total_width / 20)  # Increase offset as width grows
    
    svg_content += f'''
    <line class="dim-line" x1="0" y1="{total_height+OUTER_OFFSET}" x2="{total_width}" y2="{total_height+OUTER_OFFSET}"
          marker-start="url(#arrowhead-start)" marker-end="url(#arrowhead-end)" 
          stroke="{DIMENSION_COLOR}" style="stroke-width: {DIMENSION_STROKE}" />
    <text class="dim-text" x="{total_width/2}" y="{total_height+OUTER_OFFSET+bottom_text_offset}" text-anchor="middle" dominant-baseline="auto">{total_width}</text>
    <line class="dim-line" x1="{total_width+OUTER_OFFSET}" y1="0" x2="{total_width+OUTER_OFFSET}" y2="{total_height}"
          marker-start="url(#arrowhead-start)" marker-end="url(#arrowhead-end)" 
          stroke="{DIMENSION_COLOR}" style="stroke-width: {DIMENSION_STROKE};" />
    <text class="dim-text" x="{total_width+OUTER_OFFSET+OUTER_TEXT_OFFSET}" y="{total_height/2}" text-anchor="middle" dominant-baseline="middle" transform="rotate(90 {total_width+OUTER_OFFSET+OUTER_TEXT_OFFSET},{total_height/2})">
      {total_height}</text>
    '''

    # --- Inner Dimension Lines ---
    if window_type == 'two-pane-vertical' or window_type == 'three-pane':
        top_outer = total_height - bottom_outer
        inner_x = -INNER_OFFSET
        
        # Calculate additional offset for left text based on window height
        # Only for top and bottom height dimensions as they can clip into the window
        top_height_offset = OUTER_TEXT_OFFSET + int(top_outer / 10)  # Scale with top height
        bottom_height_offset = OUTER_TEXT_OFFSET + int(bottom_outer / 10)  # Scale with bottom height
        
        svg_content += f'''
        <line class="dim-line" x1="{inner_x}" y1="0" x2="{inner_x}" y2="{top_outer}"
              marker-start="url(#arrowhead-start)" marker-end="url(#arrowhead-end)" 
              stroke="{DIMENSION_COLOR}" style="stroke-width: {DIMENSION_STROKE};" />
        <text class="dim-text" x="{inner_x - top_height_offset}" y="{top_outer/2}" text-anchor="end" dominant-baseline="middle">
          {top_outer}
        </text>
        <line class="dim-line" x1="{inner_x}" y1="{top_outer}" x2="{inner_x}" y2="{total_height}"
              marker-start="url(#arrowhead-start)" marker-end="url(#arrowhead-end)" 
              stroke="{DIMENSION_COLOR}" style="stroke-width: {DIMENSION_STROKE};" />
        <text class="dim-text" x="{inner_x - bottom_height_offset}" y="{top_outer + (bottom_outer/2)}" text-anchor="end" dominant-baseline="middle">
          {bottom_outer}
        </text>
        '''

    if window_type == 'two-pane' or window_type == 'three-pane':
        inner_y = -INNER_OFFSET
        
        # Use standard offset for horizontal dimensions at the top
        # These don't need scaling as they don't clip into the window
        
        svg_content += f'''
        <line class="dim-line" x1="0" y1="{inner_y}" x2="{left_outer}" y2="{inner_y}"
              marker-start="url(#arrowhead-start)" marker-end="url(#arrowhead-end)" 
              stroke="{DIMENSION_COLOR}" style="stroke-width: {DIMENSION_STROKE};" />
        <text class="dim-text" x="{left_outer/2}" y="{inner_y - INNER_TEXT_OFFSET}" dominant-baseline="auto">
          {left_outer}
        </text>
        <line class="dim-line" x1="{left_outer}" y1="{inner_y}" x2="{total_width}" y2="{inner_y}"
              marker-start="url(#arrowhead-start)" marker-end="url(#arrowhead-end)" 
              stroke="{DIMENSION_COLOR}" style="stroke-width: {DIMENSION_STROKE};" />
        <text class="dim-text" x="{left_outer + ((total_width - left_outer)/2)}" y="{inner_y - INNER_TEXT_OFFSET}" dominant-baseline="auto">
          {total_width - left_outer}
        </text>
        '''

    svg_content += '</svg>'
    return svg_content
