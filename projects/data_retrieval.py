from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, send_from_directory, g

# Create the Blueprint object
data_retrieval_bp = Blueprint('data_retrieval', __name__, url_prefix='/data')
import sqlite3
import os
import json
import uuid

# Define database paths as constants
PROJECTS_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'projects.db')
MAIN_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.db')

def get_db():
    """Connect to the projects database"""
    db = sqlite3.connect(PROJECTS_DB)
    db.row_factory = sqlite3.Row
    return db

def get_main_db():
    """Connect to the main database"""
    db = sqlite3.connect(MAIN_DB)
    db.row_factory = sqlite3.Row
    return db

def get_instances_by_category(project_id, category_id):
    main_db = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.db'))
    main_db.row_factory = sqlite3.Row
    db = get_db()
    
    # Get items in this category
    items = main_db.execute('''
        SELECT item_id, name FROM Items WHERE category_id = ?
    ''', (category_id,)).fetchall()
    
    # Get instances for these items
    item_instances = []
    for item in items:
        instances = db.execute('''
            SELECT instance_id, name, short_name 
            FROM Item_Instances 
            WHERE project_id = ? AND item_id = ?
        ''', (project_id, item['item_id'])).fetchall()
        item_instances.extend([dict(inst) for inst in instances])
    
    # Get accessories in this category
    accessories = main_db.execute('''
        SELECT accesory_id, name FROM Accesory_Item WHERE category_id = ?
    ''', (category_id,)).fetchall()
    
    # Get instances for these accessories
    accessory_instances = []
    for acc in accessories:
        instances = db.execute('''
            SELECT accessory_instance_id as instance_id, name, short_name 
            FROM Accessory_Instance 
            WHERE project_id = ? AND accessory_id = ?
        ''', (project_id, acc['accesory_id'])).fetchall()
        accessory_instances.extend([dict(inst) for inst in instances])
    
    main_db.close()
    return {
        'item_instances': item_instances,
        'accessory_instances': accessory_instances
    }

def generate_category_number(index, parent_number=None):
    """Generate a category number based on index and parent number"""
    if parent_number:
        return f"{parent_number}.{index + 1}"
    else:
        return f"{index + 1}"

def get_category_tree():
    main_db = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.db'))
    main_db.row_factory = sqlite3.Row
    
    def build_tree(parent_id=None):
        categories = main_db.execute(
            'SELECT category_id, name, parent_id, item_type FROM Categories WHERE parent_id IS ? ORDER BY name',
            (parent_id,)
        ).fetchall()
        
        return [{
            'id': cat['category_id'],
            'name': cat['name'],
            'item_type': cat['item_type'],
            'children': build_tree(cat['category_id'])
        } for cat in categories]
    
    tree = build_tree()
    main_db.close()
    return tree

def get_project_windows(project_id):
    """Get all windows for a project"""
    db = get_db()
    try:
        # Add window_type, bottom_height, left_width, and pane_states to the query
        windows = db.execute('''
            SELECT window_id, name, total_height, total_width, profile, finish, category_id,
                   window_type, bottom_height, left_width, pane_states
            FROM Windows
            WHERE project_id = ?
            ORDER BY name
        ''', (project_id,)).fetchall()
        
        # Convert to list of dicts and ensure proper data types
        result = []
        for window in windows:
            window_dict = dict(window)
            
            # Ensure category_id is an integer for proper comparison
            if 'category_id' in window_dict and window_dict['category_id'] is not None:
                window_dict['category_id'] = int(window_dict['category_id'])
            
            # Ensure window_type has a default value if missing
            if 'window_type' not in window_dict or not window_dict['window_type']:
                window_dict['window_type'] = 'single-pane'
                
            # Parse pane_states from JSON string if it exists
            if 'pane_states' in window_dict and window_dict['pane_states']:
                try:
                    if isinstance(window_dict['pane_states'], str):
                        window_dict['pane_states'] = json.loads(window_dict['pane_states'])
                except json.JSONDecodeError:
                    window_dict['pane_states'] = {}
            else:
                window_dict['pane_states'] = {}
                
            # Ensure numeric fields are integers
            for field in ['total_height', 'total_width', 'bottom_height', 'left_width']:
                if field in window_dict and window_dict[field] is not None:
                    window_dict[field] = int(window_dict[field])
                    
            result.append(window_dict)
        
        return result
    except Exception as e:
        print(f"Error getting project windows: {e}")
        return []

def delete_project_window(window_id):
    """Delete a window from a project (only from projects.db, not main.db)"""
    db = get_db()
    try:
        db.execute('DELETE FROM Windows WHERE window_id = ?', (window_id,))
        db.commit()
        return True, "Window deleted successfully"
    except Exception as e:
        db.rollback()
        return False, f"Error deleting window: {e}"

# Route handlers for data retrieval
def register_routes(projects_bp):
    @projects_bp.route('/category/<int:category_id>/items')
    def get_category_items(category_id):
        # Connect to main.db to get items
        main_db = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.db'))
        main_db.row_factory = sqlite3.Row
        
        # Get category info to check for linked categories
        category = main_db.execute('''
            SELECT category_id, name, linked_categories
            FROM Categories
            WHERE category_id = ?
        ''', (category_id,)).fetchone()
        
        linked_categories = []
        if category and category['linked_categories']:
            # Parse linked categories (comma-separated list of IDs)
            linked_ids = [int(id.strip()) for id in category['linked_categories'].split(',') if id.strip()]
            if linked_ids:
                linked_categories = main_db.execute('''
                    SELECT category_id, name
                    FROM Categories
                    WHERE category_id IN ({})
                '''.format(','.join('?' * len(linked_ids))), linked_ids).fetchall()
        
        # Get items
        items = main_db.execute('''
            SELECT item_id, name, short_name 
            FROM Items 
            WHERE category_id = ?
        ''', (category_id,)).fetchall()
        
        # Get accessories
        accessories = main_db.execute('''
            SELECT accesory_id as accessory_id, name, short_name 
            FROM Accesory_Item 
            WHERE category_id = ?
        ''', (category_id,)).fetchall()
        
        main_db.close()
        
        return jsonify({
            'items': [dict(item) for item in items],
            'accessories': [dict(acc) for acc in accessories],
            'linked_categories': [dict(cat) for cat in linked_categories]
        })

    @projects_bp.route('/category/<int:category_id>/instances')
    def get_category_instances(category_id):
        project_id = request.args.get('project_id', type=int)
        if not project_id:
            return jsonify({'error': 'Project ID is required'}), 400
            
        instances = get_instances_by_category(project_id, category_id)
        return jsonify(instances)

    @projects_bp.route('/get_item_details/<item_type>/<name>')
    def get_item_details(item_type, name):
        main_db = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.db'))
        main_db.row_factory = sqlite3.Row
        
        try:
            # Clean the name by removing extra spaces
            clean_name = ' '.join(name.split())
            
            if item_type == 'item':
                item = main_db.execute('''
                    SELECT item_id as id, name, short_name, description, short_description, installation
                    FROM Items WHERE name = ?
                ''', (clean_name,)).fetchone()
                
                if item is None:
                    return jsonify({'error': 'Item not found'}), 404
                    
                attributes = main_db.execute('''
                    SELECT name, value
                    FROM Item_Attributes
                    WHERE item_id = ?
                ''', (item['id'],)).fetchall()
            else:
                item = main_db.execute('''
                    SELECT accesory_id as id, name, short_name, description, short_description, installation
                    FROM Accesory_Item WHERE name = ?
                ''', (clean_name,)).fetchone()
                
                if item is None:
                    return jsonify({'error': 'Accessory not found'}), 404
                    
                attributes = main_db.execute('''
                    SELECT name, value
                    FROM Accesory_Attributes
                    WHERE accesory_id = ?
                ''', (item['id'],)).fetchall()
            
            return jsonify({
                **dict(item),
                'attributes': [dict(attr) for attr in attributes]
            })
        finally:
            main_db.close()

    @projects_bp.route('/instance/<int:instance_id>/details', methods=['GET'])
    def get_instance_details(instance_id):
        """Get details for an instance"""
        instance_type = request.args.get('instance_type', 'item')
        db = get_db()
        main_db = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.db'))
        main_db.row_factory = sqlite3.Row
        
        try:
            if instance_type == 'item':
                # Get instance details
                instance = db.execute('''
                    SELECT instance_id, name, short_name, description, short_description, installation, item_id
                    FROM Item_Instances
                    WHERE instance_id = ?
                ''', (instance_id,)).fetchone()
                
                if instance:
                    instance_dict = dict(instance)
                    
                    # Get original item attributes from main.db
                    original_attrs = main_db.execute('''
                        SELECT name, value
                        FROM Item_Attributes
                        WHERE item_id = ?
                    ''', (instance['item_id'],)).fetchall()
                    
                    instance_dict['original_attributes'] = [dict(attr) for attr in original_attrs]
                    return jsonify(instance_dict)
            else:
                # Get accessory instance details
                instance = db.execute('''
                    SELECT accessory_instance_id as instance_id, name, short_name, description, 
                           short_description, installation, accessory_id
                    FROM Accessory_Instance
                    WHERE accessory_instance_id = ?
                ''', (instance_id,)).fetchone()
                
                if instance:
                    instance_dict = dict(instance)
                    
                    # Get original accessory attributes from main.db
                    original_attrs = main_db.execute('''
                        SELECT name, value
                        FROM Accesory_Attributes
                        WHERE accesory_id = ?
                    ''', (instance['accessory_id'],)).fetchall()
                    
                    instance_dict['original_attributes'] = [dict(attr) for attr in original_attrs]
                    return jsonify(instance_dict)
            
            return jsonify({'error': 'Instance not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            if 'main_db' in locals():
                main_db.close()

    @projects_bp.route('/instance/<int:instance_id>/attributes', methods=['GET'])
    def get_instance_attributes(instance_id):
        """Get attributes for an instance with application names resolved"""
        instance_type = request.args.get('instance_type', 'item')
        parent_item_id = request.args.get('parent_item_id')
        db = get_db()
        
        try:
            attributes = []
            
            if instance_type == 'item':
                # Get attributes for item instance
                attrs = db.execute('''
                    SELECT name, value
                    FROM Item_Instance_Attributes
                    WHERE instance_id = ?
                ''', (instance_id,)).fetchall()
                
                # Convert to list of dicts with parsed values
                for attr in attrs:
                    values = json.loads(attr['value'])
                    attributes.append({
                        'name': attr['name'],
                        'value': values[0] if values else ''
                        # No application info for items
                    })
                    
            else:
                # Get accessory instance info
                accessory_info = db.execute('''
                    SELECT name, installation
                    FROM Accessory_Instance
                    WHERE accessory_instance_id = ?
                ''', (instance_id,)).fetchone()
                
                accessory_name = accessory_info['name'] if accessory_info else 'Accessory'
                installation = accessory_info['installation'] if accessory_info else ''
                
                # Get attributes for accessory instance with ordering by group_id
                attrs = db.execute('''
                    SELECT name, value, application, group_id
                    FROM Accessory_Instance_Attributes
                    WHERE accessory_instance_id = ?
                    ORDER BY group_id
                ''', (instance_id,)).fetchall()
                
                # Group attributes by group_id first
                grouped_attrs = {}
                for attr in attrs:
                    group_id = attr['group_id'] or str(uuid.uuid4())
                    if group_id not in grouped_attrs:
                        grouped_attrs[group_id] = {
                            'application': attr['application'],
                            'attributes': [],
                            'group_id': group_id
                        }
                    grouped_attrs[group_id]['attributes'].append(attr)
                
                # Process each group
                for group_id, group in grouped_attrs.items():
                    application = group['application']
                    
                    # Default application name is the raw application value
                    application_name = application if application else 'General'
                    
                    # If this is a linked accessory under an item, use the accessory name for the first row
                    if parent_item_id and str(parent_item_id) == str(application):
                        # For the first row of an accessory table inside an item, show the accessory name
                        if not attributes:  # This is the first attribute we're processing
                            application_name = accessory_name
                        else:
                            # Get the parent item's name for subsequent rows
                            parent_item = db.execute('''
                                SELECT name
                                FROM Item_Instances
                                WHERE instance_id = ?
                            ''', (parent_item_id,)).fetchone()
                            
                            if parent_item:
                                application_name = parent_item['name']
                    # For standalone accessory view with no application, use the installation value
                    elif not parent_item_id and (not application or application == ''):
                        application_name = installation if installation else 'General'
                    # If application is a numeric string (item ID), look up the item name
                    elif application and application.isdigit():
                        item_instance = db.execute('''
                            SELECT name
                            FROM Item_Instances
                            WHERE instance_id = ?
                        ''', (application,)).fetchone()
                        
                        if item_instance:
                            application_name = item_instance['name']
                    
                    # Add all attributes from this group with the same group_id and occurrence
                    for attr in group['attributes']:
                        values = json.loads(attr['value'])
                        attributes.append({
                            'name': attr['name'],
                            'value': values[0] if values else '',
                            'application': application,
                            'application_name': application_name,
                            'group_id': group_id,
                            'occurrence': 1  # Default occurrence
                        })
            
            return jsonify({
                'attributes': attributes
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @projects_bp.route('/item_instance/<int:instance_id>/accessories', methods=['GET'])
    def get_item_instance_accessories(instance_id):
        """Get accessories linked to an item instance"""
        db = get_db()
        main_db = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.db'))
        main_db.row_factory = sqlite3.Row
        
        try:
            # Find accessories that have this item instance as their application
            accessories = db.execute('''
                SELECT DISTINCT a.accessory_instance_id as instance_id, a.name, a.short_name, a.accessory_id
                FROM Accessory_Instance a
                JOIN Accessory_Instance_Attributes attr ON a.accessory_instance_id = attr.accessory_instance_id
                WHERE attr.application = ?
            ''', (str(instance_id),)).fetchall()
            
            # Get category information for each accessory
            result_accessories = []
            for acc in accessories:
                acc_dict = dict(acc)
                
                # Get category info for this accessory
                category = main_db.execute('''
                    SELECT c.category_id, c.name as category_name
                    FROM Accesory_Item ai
                    JOIN Categories c ON ai.category_id = c.category_id
                    WHERE ai.accesory_id = ?
                ''', (acc['accessory_id'],)).fetchone()
                
                if category:
                    acc_dict['category_id'] = category['category_id']
                    acc_dict['category_name'] = category['category_name']
                else:
                    acc_dict['category_id'] = None
                    acc_dict['category_name'] = 'Unknown'
                    
                result_accessories.append(acc_dict)
            
            main_db.close()
            return jsonify({
                'accessories': result_accessories
            })
        except Exception as e:
            if 'main_db' in locals():
                main_db.close()
            return jsonify({'error': str(e)}), 500

    @projects_bp.route('/static/<path:filename>')
    def static_files(filename):
        """Serve static files from the static directory"""
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)

    @projects_bp.route('/table_logic.js')
    def serve_table_logic():
        """Serve the table_logic.js file directly from the projects directory"""
        return send_from_directory(os.path.dirname(__file__), 'table_logic.js')
    
    @projects_bp.route('/windows/<int:project_id>')
    def get_project_windows_route(project_id):
        windows = get_project_windows(project_id)
        return jsonify({'windows': windows})
        
    @projects_bp.route('/delete_project_window/<int:window_id>', methods=['POST'])
    def delete_project_window_route(window_id):
        success, message = delete_project_window(window_id)
        return jsonify({'success': success, 'message': message})

@data_retrieval_bp.route('/instance/<int:instance_id>/materials', methods=['GET'])
def get_instance_materials(instance_id):
    instance_type = request.args.get('instance_type', 'item')
    project_id = request.args.get('project_id')
    import json
    from projects.materials_logic import get_applicable_materials
    db = get_db()
    main_db = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.db'))
    main_db.row_factory = sqlite3.Row
    if instance_type == 'item':
        instance = db.execute('SELECT instance_id, item_id, project_id FROM Item_Instances WHERE instance_id = ?', (instance_id,)).fetchone()
        if not instance:
            return jsonify({'error': 'Instance not found'}), 404
        ref_id = instance['item_id']
        project_id = project_id or instance['project_id']
        attrs = db.execute('SELECT name, value FROM Item_Instance_Attributes WHERE instance_id = ?', (instance_id,)).fetchall()
        instance_attributes = {}
        for attr in attrs:
            try:
                values = json.loads(attr['value'])
                instance_attributes[attr['name']] = values[0] if values else ''
            except Exception:
                instance_attributes[attr['name']] = attr['value']
        materials = get_applicable_materials('item', ref_id, instance_attributes, main_db)
    else:
        instance = db.execute('SELECT accessory_instance_id as instance_id, accessory_id, project_id FROM Accessory_Instance WHERE accessory_instance_id = ?', (instance_id,)).fetchone()
        if not instance:
            return jsonify({'error': 'Instance not found'}), 404
        ref_id = instance['accessory_id']
        project_id = project_id or instance['project_id']
        attrs = db.execute('SELECT name, value, group_id FROM Accessory_Instance_Attributes WHERE accessory_instance_id = ?', (instance_id,)).fetchall()
        groups = {}
        for attr in attrs:
            group = attr['group_id']
            if group not in groups:
                groups[group] = {}
            try:
                values = json.loads(attr['value'])
                groups[group][attr['name']] = values[0] if values else ''
            except Exception:
                groups[group][attr['name']] = attr['value']
        materials = []
        for group_attrs in groups.values():
            group_materials = get_applicable_materials('accessory', ref_id, group_attrs, main_db)
            materials.extend(group_materials)
    
    # Deduplicate materials by material_id
    unique_materials = []
    seen_ids = set()
    for m in materials:
        if m.get('material_id') not in seen_ids:
            unique_materials.append(m)
            seen_ids.add(m.get('material_id'))
    
    # Get quantities from Bill_Of_Materials if project_id is available
    if project_id:
        try:
            # Get quantities for all materials in this project
            quantities = db.execute(
                "SELECT material_id, quantity FROM Bill_Of_Materials WHERE project_id = ?", 
                (project_id,)
            ).fetchall()
            
            # Create a lookup dictionary
            quantity_lookup = {row['material_id']: row['quantity'] for row in quantities}
            
            # Add quantities to materials
            for material in unique_materials:
                material_id = material.get('material_id')
                if material_id in quantity_lookup:
                    material['quantity'] = quantity_lookup[material_id]
        except Exception as e:
            print(f"Error fetching material quantities: {e}")
    
    main_db.close()
    return jsonify({'materials': unique_materials})
