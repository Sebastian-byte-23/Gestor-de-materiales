import json
from categories import get_db

def get_materials_for_item(item_id, item_type):
    with get_db() as conn:
        cursor = conn.cursor()
        if item_type == 'item':
            cursor.execute("SELECT * FROM Materials WHERE item_id = ?", (item_id,))
        else:
            cursor.execute("SELECT * FROM Materials WHERE accesory_id = ?", (item_id,))
        materials = cursor.fetchall()
        materials_list = []
        for material in materials:
            m_dict = dict(material)
            cursor.execute("SELECT * FROM Material_Conditions WHERE material_id = ?", (m_dict['material_id'],))
            conditions = cursor.fetchall()
            m_dict['conditions'] = [dict(cond) for cond in conditions]
            materials_list.append(m_dict)
        return materials_list

def add_material(item_id, item_type, material_name, SKU):
    with get_db() as conn:
        cursor = conn.cursor()
        if item_type == 'item':
            cursor.execute("INSERT INTO Materials (item_id, material_name, SKU) VALUES (?, ?, ?)",
                           (item_id, material_name, SKU))
        else:
            cursor.execute("INSERT INTO Materials (accesory_id, material_name, SKU) VALUES (?, ?, ?)",
                           (item_id, material_name, SKU))
        material_id = cursor.lastrowid
        conn.commit()
        return material_id

def edit_material(material_id, material_name, SKU):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Materials SET material_name = ?, SKU = ? WHERE material_id = ?",
                       (material_name, SKU, material_id))
        conn.commit()

def delete_material(material_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Materials WHERE material_id = ?", (material_id,))
        conn.commit()

def add_material_condition(material_id, group_id, attribute_name, operator, value):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Material_Conditions (material_id, group_id, attribute_name, operator, value) VALUES (?, ?, ?, ?, ?)",
            (material_id, group_id, attribute_name, operator, value)
        )
        condition_id = cursor.lastrowid
        conn.commit()
        return condition_id

def edit_material_condition(condition_id, group_id, attribute_name, operator, value):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Material_Conditions SET group_id = ?, attribute_name = ?, operator = ?, value = ? WHERE condition_id = ?",
            (group_id, attribute_name, operator, value, condition_id)
        )
        conn.commit()

def delete_material_condition(condition_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Material_Conditions WHERE condition_id = ?", (condition_id,))
        conn.commit()

def edit_material_units(material_id, units):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Materials SET units = ? WHERE material_id = ?", (units, material_id))
        conn.commit()
