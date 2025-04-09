from contextlib import contextmanager
import sqlite3
import os
from flask import render_template, request, redirect, url_for, jsonify, flash
from database_editor.categories import get_db, get_category_by_id
from database_editor.window_drawing import generate_svg  # Import the SVG generation function


def get_windows_by_category(category_id):
    """Get all windows for a specific category, organized by window_group"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM Windows 
            WHERE category_id = ?
            ORDER BY window_group NULLS LAST, name
        """, (category_id,))
        windows = cursor.fetchall()

        # For each window record, generate its SVG using stored dimension and pane state parameters.
        windows_by_group = {}
        ungrouped_windows = []
        
        for window in windows:
            window_dict = dict(window)
            # Parse pane_states JSON if it exists
            if 'pane_states' in window_dict and window_dict['pane_states']:
                import json
                try:
                    window_dict['pane_states'] = json.loads(window_dict['pane_states'])
                except json.JSONDecodeError:
                    window_dict['pane_states'] = {}
            else:
                window_dict['pane_states'] = {}

            params = {
                'window_type': window_dict['window_type'],
                'total_height': window_dict['total_height'],
                'total_width': window_dict['total_width'],
                'bottom_height': window_dict['bottom_height'],
                'left_width': window_dict['left_width'],
                'pane_states': window_dict.get('pane_states') or {}
            }
            window_dict['svg'] = generate_svg(params)
            
            # Organize windows by group
            group = window_dict.get('window_group')
            if group and group.strip():
                if group not in windows_by_group:
                    windows_by_group[group] = []
                windows_by_group[group].append(window_dict)
            else:
                ungrouped_windows.append(window_dict)
        
        # Create a structured result with groups and ungrouped windows
        result = {
            'grouped': windows_by_group,
            'ungrouped': ungrouped_windows
        }
        
        return result

def get_window_by_id(window_id):
    """Get a specific window by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Windows WHERE window_id = ?", (window_id,))
        window = cursor.fetchone()
        if window:
            window_dict = dict(window)
            # Parse pane_states JSON if it exists
            if 'pane_states' in window_dict and window_dict['pane_states']:
                import json
                try:
                    window_dict['pane_states'] = json.loads(window_dict['pane_states'])
                except json.JSONDecodeError:
                    window_dict['pane_states'] = {}
            else:
                window_dict['pane_states'] = {}
            return window_dict
        return None

def get_window_groups():
    """Get all unique window groups"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT window_group FROM Windows WHERE window_group IS NOT NULL AND window_group != ''")
        groups = cursor.fetchall()
        return [group['window_group'] for group in groups]

def save_window(data):
    """Save a new window or update an existing one"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Convert string values to integers where needed
            for key in ['total_height', 'total_width', 'bottom_height', 'left_width', 'category_id']:
                if key in data and data[key] and isinstance(data[key], str):
                    try:
                        data[key] = int(data[key])
                    except ValueError:
                        return False, None, f"Invalid value for {key}: {data[key]}"

            # Extract pane states from the data
            pane_states = {}
            for key in data:
                if key.startswith('pane_'):
                    pane_states[key] = data[key]

            # Convert pane states to JSON string
            import json
            pane_states_json = json.dumps(pane_states)
            
            # Debug output
            print(f"Saving pane states: {pane_states_json}")
            
            # Handle window_group - if it's "new" and new_group_name is provided, use that instead
            window_group = data.get('window_group', '')
            if window_group == 'new' and data.get('new_group_name'):
                window_group = data['new_group_name']
            
            # Handle empty window_id
            if 'window_id' in data and data['window_id'] and data['window_id'] != 'None':
                # Update existing window
                cursor.execute('''
                    UPDATE Windows 
                    SET name = ?, total_height = ?, total_width = ?, 
                        bottom_height = ?, left_width = ?, window_type = ?,
                        pane_states = ?, window_group = ?
                    WHERE window_id = ?
                ''', (
                    data['name'], data['total_height'], data['total_width'],
                    data['bottom_height'], data['left_width'], data['window_type'],
                    pane_states_json, window_group, data['window_id']
                ))
                window_id = data['window_id']
            else:
                # Insert new window
                cursor.execute('''
                    INSERT INTO Windows 
                    (name, total_height, total_width, bottom_height, left_width, window_type, category_id, pane_states, window_group)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['name'], data['total_height'], data['total_width'],
                    data['bottom_height'], data['left_width'], data['window_type'],
                    data['category_id'], pane_states_json, window_group
                ))
                window_id = cursor.lastrowid

            conn.commit()
            return True, window_id, None
        except Exception as e:
            conn.rollback()
            return False, None, str(e)

def delete_window(window_id):
    """Delete a window by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Get category_id before deleting
            cursor.execute('SELECT category_id FROM Windows WHERE window_id = ?', (window_id,))
            result = cursor.fetchone()
            if not result:
                return False, None, "Window not found"
            
            category_id = result['category_id']
            
            # Delete the window
            cursor.execute('DELETE FROM Windows WHERE window_id = ?', (window_id,))
            conn.commit()
            
            return True, category_id, None
        except Exception as e:
            conn.rollback()
            return False, None, str(e)

def generate_window_svg_route(window_id=None):
    """Generates the SVG for a window based on its parameters or ID."""
    if request.method == 'POST':
        # Get parameters from the POST request (for a new or unsaved window)
        params = request.get_json()
    elif window_id:
        # Get parameters from the database (for an existing window)
        window = get_window_by_id(window_id)
        if not window:
            return jsonify({'error': 'Window not found'}), 404
        params = {
            'window_type': window['window_type'],
            'total_height': window['total_height'],
            'total_width': window['total_width'],
            'bottom_height': window['bottom_height'],
            'left_width': window['left_width'],
            'pane_states': window['pane_states']
        }
    else:
        return jsonify({'error': 'Invalid request'}), 400

    svg_data = generate_svg(params)
    return jsonify({'svg': svg_data})

def get_window_specs(spec_name):
    """Return spec options for a given spec name from the Window_Specs table."""
    import json
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT spec_values FROM Window_Specs WHERE name = ?", (spec_name,))
        row = cursor.fetchone()
        if row:
            return json.loads(row['spec_values'])
        return []

def save_window_spec(spec_name, spec_values):
    """Save or update a window spec in the Window_Specs table."""
    import json
    with get_db() as conn:
        cursor = conn.cursor()
        # Check if spec already exists
        cursor.execute("SELECT spec_id FROM Window_Specs WHERE name = ?", (spec_name,))
        row = cursor.fetchone()
        try:
            if row:
                # Update existing spec
                cursor.execute(
                    "UPDATE Window_Specs SET spec_values = ? WHERE name = ?", 
                    (json.dumps(spec_values), spec_name)
                )
            else:
                # Insert new spec
                cursor.execute(
                    "INSERT INTO Window_Specs (name, spec_values) VALUES (?, ?)",
                    (spec_name, json.dumps(spec_values))
                )
            conn.commit()
            return True, None
        except Exception as e:
            conn.rollback()
            return False, str(e)
