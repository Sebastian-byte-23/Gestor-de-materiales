-- this is the schema for database.db, which serves as the main database of information the app


-- Categories Table (Adjacency List)
CREATE TABLE Categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(100) NOT NULL,
    parent_id   INTEGER, 
    linked_categories VARCHAR(50) DEFAULT NULL,
    item_type   VARCHAR(20) DEFAULT 'item',
    FOREIGN KEY (parent_id) REFERENCES Categories(category_id) ON DELETE CASCADE,
    UNIQUE (name, parent_id)  -- unique within the same parent
);

-- Items Table
CREATE TABLE IF NOT EXISTS Items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL,
    short_name VARCHAR(50),       
    description TEXT,
    short_description TEXT,
    installation TEXT,
    category_id INTEGER, -- can reference either a top-level or nested category
    hidden TEXT DEFAULT '[]',
    item_type TEXT,
    FOREIGN KEY (category_id) REFERENCES Categories(category_id) ON DELETE CASCADE
);

-- Item Attributes Table
CREATE TABLE Item_Attributes (
    attribute_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL,
    value TEXT DEFAULT '[]', -- Stores JSON array of values
    FOREIGN KEY (item_id) REFERENCES Items(item_id) ON DELETE CASCADE
);

-- Accessory Item Table
CREATE TABLE Accesory_Item (
    accesory_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    name VARCHAR(50) NOT NULL,
    short_name VARCHAR(50),
    description VARCHAR(50),
    short_description VARCHAR(50),
    installation TEXT,
    hidden TEXT DEFAULT '[]',
    category_id INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES Categories(category_id) ON DELETE CASCADE
);

-- Accesory Attributes Table
CREATE TABLE Accesory_Attributes (
    attribute_id INTEGER PRIMARY KEY AUTOINCREMENT,
    accesory_id INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL,
    value TEXT DEFAULT '[]', -- Stores JSON array of values
    FOREIGN KEY (accesory_id) REFERENCES Accesory_Item(accesory_id) ON DELETE CASCADE
);    

CREATE TABLE Materials (
    material_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER, -- FK to Items (if applicable)
    accesory_id INTEGER, -- FK to Accesory_Item (if applicable)
    material_name TEXT NOT NULL,
    SKU TEXT NOT NULL,
    Units VARCHAR(50),
    FOREIGN KEY (item_id) REFERENCES Items(item_id) ON DELETE CASCADE,
    FOREIGN KEY (accesory_id) REFERENCES Accesory_Item(accesory_id) ON DELETE CASCADE
);

CREATE TABLE Material_Conditions (
    condition_id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,   -- Groups conditions for AND logic
    attribute_name TEXT NOT NULL,
    operator TEXT DEFAULT '=',   -- '=', 'IN', etc.
    value TEXT NOT NULL,         -- JSON array or single value
    FOREIGN KEY (material_id) REFERENCES Materials(material_id) ON DELETE CASCADE
);


-- Windows Table
CREATE TABLE Windows (
    window_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    total_height INTEGER NOT NULL,
    total_width INTEGER NOT NULL,
    bottom_height INTEGER,
    left_width INTEGER,
    window_type VARCHAR(20) NOT NULL, -- 'single-pane', 'two-pane', 'two-pane-vertical', 'three-pane'
    category_id INTEGER NOT NULL,
    pane_states TEXT,
    window_group TEXT,
    FOREIGN KEY (category_id) REFERENCES Categories(category_id) ON DELETE CASCADE
)

--Window Specs Table
CREATE TABLE Window_specs (
    spec_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    value TEXT DEFAULT '[]', -- Stores JSON array of values
)

-- Indexes for Performance
CREATE INDEX idx_item_attributes ON Item_Attributes (attribute_id);
