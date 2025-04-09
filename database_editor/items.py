from contextlib import contextmanager
import sqlite3
from categories import get_db

def get_items_by_category(category_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM Items 
            WHERE category_id = ?
        """, (category_id,))
        items = cursor.fetchall()
        
        # Convert rows to dictionaries and get attributes
        items_list = []
        for item in items:
            item_dict = dict(item)
            cursor.execute("""
                SELECT * FROM Item_Attributes 
                WHERE item_id = ?
            """, (item_dict['item_id'],))
            attributes = cursor.fetchall()
            item_dict['attributes'] = []
            for attr in attributes:
                attr_dict = dict(attr)
                # Parse the JSON string into a Python list
                attr_dict['value'] = json.loads(attr_dict['value'])
                item_dict['attributes'].append(attr_dict)
            items_list.append(item_dict)
            
        return items_list

def add_item(name, short_name, description, short_description, installation, category_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Items (name, short_name, description, short_description, 
                             installation, category_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, short_name, description, short_description, installation, category_id))
        item_id = cursor.lastrowid
        conn.commit()
        return item_id

def delete_item(item_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Items WHERE item_id = ?", (item_id,))
        conn.commit()
        return item_id

import json

def add_item_attribute(item_id, name, values):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Item_Attributes (item_id, name, value)
            VALUES (?, ?, ?)
        """, (item_id, name, json.dumps(values)))
        conn.commit()

def edit_item(item_id, name, short_name, description, short_description, installation):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Items 
            SET name = ?, short_name = ?, description = ?, 
                short_description = ?, installation = ?
            WHERE item_id = ?
        """, (name, short_name, description, short_description, installation, item_id))
        conn.commit()

def edit_item(item_id, name, short_name, description, short_description, installation, category_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Items 
            SET name = ?, short_name = ?, description = ?, 
                short_description = ?, installation = ?, category_id = ?
            WHERE item_id = ?
        """, (name, short_name, description, short_description, installation, category_id, item_id))
        conn.commit()

def edit_item_attribute(item_id, attributes):
    with get_db() as conn:
        cursor = conn.cursor()
        # First delete existing attributes
        cursor.execute("DELETE FROM Item_Attributes WHERE item_id = ?", (item_id,))

        # Then insert new attributes
        for attr in attributes:
            cursor.execute("""
                INSERT INTO Item_Attributes (item_id, name, value)
                VALUES (?, ?, ?)
            """, (item_id, attr['name'], json.dumps(attr['value'])))
        conn.commit()
