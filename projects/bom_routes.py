import os
import sqlite3
from flask import  Blueprint, request, jsonify, current_app
bom_bp = Blueprint('bom', __name__)
# Function to register routes with the projects blueprint
def register_bom_routes(projects_bp):
    """Register BOM routes with the projects blueprint"""
    projects_bp.route('/save_material_quantity', methods=['POST'])(save_material_quantity)
    projects_bp.route('/delete_material_quantity', methods=['POST'])(delete_material_quantity)
    projects_bp.route('/get_project_materials/<int:project_id>', methods=['GET'])(get_project_materials)

def get_db():
    """Connect to the projects database"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'projects.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@bom_bp.route('/save_material_quantity', methods=['POST'])
def save_material_quantity():
    """Save or update a material quantity in the Bill_Of_Materials table"""
    data = request.json
    
    if not data or 'project_id' not in data or 'material_id' not in data or 'quantity' not in data:
        return jsonify({'success': False, 'error': 'Missing required data'}), 400
    
    try:
        project_id = int(data['project_id'])
        material_id = int(data['material_id'])
        quantity = float(data['quantity'])
        
        if quantity <= 0:
            return jsonify({'success': False, 'error': 'Quantity must be greater than zero'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if entry already exists
        cursor.execute(
            "SELECT bom_id FROM Bill_Of_Materials WHERE project_id = ? AND material_id = ?", 
            (project_id, material_id)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing entry
            cursor.execute(
                "UPDATE Bill_Of_Materials SET quantity = ? WHERE project_id = ? AND material_id = ?",
                (quantity, project_id, material_id)
            )
        else:
            # Insert new entry
            cursor.execute(
                "INSERT INTO Bill_Of_Materials (project_id, material_id, quantity) VALUES (?, ?, ?)",
                (project_id, material_id, quantity)
            )
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bom_bp.route('/delete_material_quantity', methods=['POST'])
def delete_material_quantity():
    """Delete a material quantity from the Bill_Of_Materials table"""
    data = request.json
    
    if not data or 'project_id' not in data or 'material_id' not in data:
        return jsonify({'success': False, 'error': 'Missing required data'}), 400
    
    try:
        project_id = int(data['project_id'])
        material_id = int(data['material_id'])
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM Bill_Of_Materials WHERE project_id = ? AND material_id = ?", 
            (project_id, material_id)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bom_bp.route('/get_project_materials/<int:project_id>', methods=['GET'])
def get_project_materials(project_id):
    """Get all materials and quantities for a project"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT b.material_id, b.quantity 
            FROM Bill_Of_Materials b
            WHERE b.project_id = ?
            """, 
            (project_id,)
        )
        
        materials = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # When called from a route, return JSON response
        if request and hasattr(request, 'method'):
            return jsonify({'success': True, 'materials': materials})
        # When called directly from Python code, return the data dictionary
        else:
            return {'success': True, 'materials': materials}
    
    except Exception as e:
        error_response = {'success': False, 'error': str(e)}
        # When called from a route, return JSON response with status code
        if request and hasattr(request, 'method'):
            return jsonify(error_response), 500
        # When called directly from Python code, return the error dictionary
        else:
            return error_response

