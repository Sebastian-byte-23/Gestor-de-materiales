from contextlib import contextmanager
import sqlite3
from categories import get_db

def get_accessories_by_category(category_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM Accesory_Item 
            WHERE category_id = ?
        """, (category_id,))
        accessories = cursor.fetchall()
        
        # Convert rows to dictionaries and get attributes
        accessories_list = []
        for accessory in accessories:
            accessory_dict = dict(accessory)
            cursor.execute("""
                SELECT * FROM Accesory_Attributes 
                WHERE accesory_id = ?
            """, (accessory_dict['accesory_id'],))
            attributes = cursor.fetchall()
            accessory_dict['attributes'] = []
            for attr in attributes:
                attr_dict = dict(attr)
                # Parse the JSON string into a Python list
                attr_dict['value'] = json.loads(attr_dict['value'])
                accessory_dict['attributes'].append(attr_dict)
            accessories_list.append(accessory_dict)
            
        return accessories_list

def add_accessory(name, short_name, description, short_description, installation, category_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Accesory_Item (name, short_name, description, short_description, 
                                     installation, category_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, short_name, description, short_description, installation, category_id))
        accessory_id = cursor.lastrowid
        conn.commit()
        return accessory_id

def delete_accessory(accessory_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Materials WHERE accesory_id = ?", (accessory_id,))
        cursor.execute("DELETE FROM Accesory_Item WHERE accesory_id = ?", (accessory_id,))
        conn.commit()
        return accessory_id

import json

def add_accessory_attribute(accessory_id, name, values):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Accesory_Attributes (accesory_id, name, value)
            VALUES (?, ?, ?)
        """, (accessory_id, name, json.dumps(values)))
        conn.commit()

def edit_accessory(accessory_id, name, short_name, description, short_description, installation, category_id=None):
    with get_db() as conn:
        cursor = conn.cursor()
        if category_id is not None:
            cursor.execute("""
                UPDATE Accesory_Item 
                SET name = ?, short_name = ?, description = ?, short_description = ?, installation = ?, category_id = ?
                WHERE accesory_id = ?
            """, (name, short_name, description, short_description, installation, category_id, accessory_id))
        else:
            cursor.execute("""
                UPDATE Accesory_Item 
                SET name = ?, short_name = ?, description = ?, short_description = ?, installation = ?
                WHERE accesory_id = ?
            """, (name, short_name, description, short_description, installation, accessory_id))
        conn.commit()

def edit_accessory_attribute(accessory_id, attributes):
    with get_db() as conn:
        cursor = conn.cursor()
        # First delete existing attributes
        cursor.execute("DELETE FROM Accesory_Attributes WHERE accesory_id = ?", (accessory_id,))
        
        # Then insert new attributes
        for attr in attributes:
            cursor.execute("""
                INSERT INTO Accesory_Attributes (accesory_id, name, value)
                VALUES (?, ?, ?)
            """, (accessory_id, attr['name'], json.dumps(attr['value'])))
        conn.commit()
