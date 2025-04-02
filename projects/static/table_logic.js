window.tableLogic = (function() {
    // Store linked categories data
    const linkedCategoriesData = {};
    
    // Function to load instances for a category
    function loadInstances(categoryId, projectId) {
        const instancesContainer = $(`#instances-${categoryId}`);
        
        $.get(`/projects/category/${categoryId}/instances?project_id=${projectId}`, function(data) {
            instancesContainer.empty();
            
            // Combine and sort instances
            const allInstances = [
                ...data.item_instances.map(inst => ({...inst, type: 'Item'})),
                ...data.accessory_instances.map(inst => ({...inst, type: 'Accessory'}))
            ].sort((a, b) => a.name.localeCompare(b.name));
            
            // Populate instances
            allInstances.forEach(instance => {
                // Create instance element
                const instanceElement = $(`<div class="instance-item d-flex justify-content-between align-items-center">
                    <div class="instance-name-container">
                        <span>${instance.name}</span>
                        <div class="instance-actions">
                            <i class="fa fa-edit edit-instance-btn" 
                               data-instance-id="${instance.instance_id}" 
                               data-instance-type="${instance.type.toLowerCase()}"
                               title="Edit instance"></i>
                            <i class="fa fa-times delete-instance-btn" 
                               data-instance-id="${instance.instance_id}" 
                               data-instance-type="${instance.type.toLowerCase()}"
                               title="Delete instance"></i>
                        </div>
                    </div>
                    <div>
                        <span class="badge badge-info">${instance.type}</span>
                        <button class="show-attributes-btn btn btn-sm btn-outline-info ml-2" 
                                data-instance-id="${instance.instance_id}" 
                                data-instance-type="${instance.type.toLowerCase()}">
                            <i class="fa fa-table"></i> Hide
                        </button>
                    </div>
                </div>`);
                
                // Add linked accessory buttons if needed
                if (typeof addLinkedAccessoryButtons === 'function') {
                    addLinkedAccessoryButtons(instanceElement, instance, categoryId);
                }
                
                // Create a container for the attributes table
                const attributesTableContainer = $('<div class="attributes-table-container"></div>');
                
                // Add the instance element and attributes container to the container
                instancesContainer.append(instanceElement);
                instancesContainer.append(attributesTableContainer);
                
                // Fetch and populate attributes for this instance
                fetchInstanceAttributes(instance.instance_id, instance.type.toLowerCase(), attributesTableContainer);
            });
        });
    }

    // Function to fetch and display instance attributes
    function fetchInstanceAttributes(instanceId, instanceType, container, parentItemId) {
        $.ajax({
            url: `/projects/instance/${instanceId}/attributes`,
            type: 'GET',
            data: { 
                instance_type: instanceType,
                parent_item_id: parentItemId 
            },
            success: function(data) {
                // Filter attributes based on context
                if (instanceType === 'accessory' && parentItemId) {
                    data.attributes = data.attributes.filter(attr => 
                        attr.application === parentItemId.toString());
                }
                
                // Create attributes table
                if (data.attributes && data.attributes.length > 0) {
                    // Get unique attribute names
                    const attributeNames = [...new Set(data.attributes.map(attr => attr.name))];
                    
                    // Create table
                    const table = $('<table class="attributes-table"></table>');
                    
                    // Create header row
                    const headerRow = $('<tr></tr>');
                    // Only show application column for standalone accessories
                    if (instanceType === 'accessory' && !parentItemId) {
                        headerRow.append('<th>Aplicación</th>');
                    }
                    attributeNames.forEach(name => {
                        headerRow.append(`<th>${name}</th>`);
                    });
                    table.append($('<thead></thead>').append(headerRow));
                    
                    // Group attributes by group_id
                    const attributesByGroup = {};
                    data.attributes.forEach(attr => {
                        // Handle items as single group
                        if (instanceType === 'item') {
                            const groupKey = 'item_group'; // Force single group for items
                            if (!attributesByGroup[groupKey]) {
                                attributesByGroup[groupKey] = {
                                    attributes: {},
                                    isItemGroup: true // Flag for item groups
                                };
                            }
                            attributesByGroup[groupKey].attributes[attr.name] = attr.value;
                        } else {
                            // Existing accessory grouping logic
                            const groupKey = attr.group_id || `no_group_${Math.random().toString(36).substr(2, 9)}`;
                            if (!attributesByGroup[groupKey]) {
                                attributesByGroup[groupKey] = {
                                    group_id: attr.group_id,
                                    application: attr.application || 'General',
                                    occurrence: attr.occurrence || 1,
                                    application_name: attr.application_name || attr.application || 'General',
                                    attributes: {}
                                };
                            }
                            attributesByGroup[groupKey].attributes[attr.name] = attr.value;
                        }
                    });
                    
                    // Create table body
                    const tbody = $('<tbody></tbody>');
                    
                    Object.values(attributesByGroup).forEach(group => {
                        const row = $('<tr></tr>');
                        
                        // Only show application cell for standalone accessories
                        if (instanceType === 'accessory' && !parentItemId && !group.isItemGroup) {
                            const appDisplay = group.application_name;
                            const occurrenceSuffix = group.occurrence > 1 ? ` (${group.occurrence})` : '';
                            const appCell = $(`<td class="application-cell">
                                ${appDisplay}${occurrenceSuffix}
                                <i class="fas fa-trash delete-attribute-row" 
                                    data-instance-id="${instanceId}" 
                                    data-instance-type="${instanceType}"
                                    data-group-id="${group.group_id || ''}"
                                    data-application="${group.application || ''}"
                                    data-occurrence="${group.occurrence || '1'}"
                                    title="Delete this row"></i>
                            </td>`);
                            row.append(appCell);
                        }
                        
                        // Attribute value columns
                        attributeNames.forEach(name => {
                            const value = group.attributes[name] || '';
                            row.append(`<td>${value}</td>`);
                        });
                        
                        tbody.append(row);
                    });
                    
                    table.append(tbody);
                    container.html(table);
                } else {
                    container.html('<p class="text-muted">No attributes found</p>');
                }
                
                // If this is an item instance, also fetch linked accessories
                if (instanceType === 'item') {
                    fetchLinkedAccessories(instanceId, container);
                }
                if (!(instanceType === 'accessory' && parentItemId)) {
                    const projectId = window.projectId || $('h1').data('project-id');
                    $.get(`/data/instance/${instanceId}/materials`, { 
                        instance_type: instanceType,
                        project_id: projectId
                    }, function(materialData) {
                        if (materialData.materials && materialData.materials.length > 0) {
                            let materialsHtml = `<div class="materials-section mt-2 execution-only">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Material</th>
                                            <th>SKU</th>
                                            <th>Cantidad</th>
                                            <th>Unidad</th>
                                        </tr>
                                    </thead>
                                    <tbody>`;
                            
                            materialData.materials.forEach(material => {
                                materialsHtml += `
                                    <tr>
                                        <td>${material.material_name}</td>
                                        <td>${material.SKU}</td>
                                        <td>
                                            <input type="number" 
                                                class="form-control form-control-sm material-quantity" 
                                                data-material-id="${material.material_id}" 
                                                data-instance-id="${instanceId}"
                                                data-project-id="${projectId}"
                                                value="${material.quantity || ''}" 
                                                min="0" 
                                                step="0.01"
                                                placeholder="Enter quantity">
                                        </td>
                                        <td>${material.Units || material.units || ''}</td>
                                    </tr>`;
                            });
                            
                            materialsHtml += `</tbody></table></div>`;
                            container.append(materialsHtml);
                            
                            // Add event handler for quantity changes
                            container.find('.material-quantity').on('change', function() {
                                const $input = $(this);
                                const materialId = $input.data('material-id');
                                const projectId = $input.data('project-id');
                                const quantity = $input.val();
                                
                                if (quantity && quantity > 0) {
                                    // Save quantity
                                    $.ajax({
                                        url: '/projects/save_material_quantity',
                                        type: 'POST',
                                        contentType: 'application/json',
                                        data: JSON.stringify({
                                            project_id: projectId,
                                            material_id: materialId,
                                            quantity: quantity
                                        }),
                                        success: function(response) {
                                            if (response.success) {
                                                // Visual feedback
                                                $input.addClass('is-valid');
                                                setTimeout(() => $input.removeClass('is-valid'), 2000);
                                            } else {
                                                alert('Error saving quantity: ' + response.error);
                                                $input.addClass('is-invalid');
                                                setTimeout(() => $input.removeClass('is-invalid'), 2000);
                                            }
                                        },
                                        error: function() {
                                            alert('Error saving material quantity');
                                            $input.addClass('is-invalid');
                                            setTimeout(() => $input.removeClass('is-invalid'), 2000);
                                        }
                                    });
                                } else {
                                    // Delete quantity if empty
                                    $.ajax({
                                        url: '/projects/delete_material_quantity',
                                        type: 'POST',
                                        contentType: 'application/json',
                                        data: JSON.stringify({
                                            project_id: projectId,
                                            material_id: materialId
                                        }),
                                        success: function(response) {
                                            if (response.success) {
                                                // Visual feedback
                                                $input.addClass('is-valid');
                                                setTimeout(() => $input.removeClass('is-valid'), 2000);
                                            } else {
                                                alert('Error removing quantity: ' + response.error);
                                            }
                                        },
                                        error: function() {
                                            alert('Error removing material quantity');
                                        }
                                    });
                                }
                            });
                        }
                    });
                }
            },
            error: function() {
                container.html('<p class="text-danger">Error loading attributes</p>');
            }
        });
    }
    
    // Function to fetch and display linked accessories for an item instance
    function fetchLinkedAccessories(itemInstanceId, container) {
        $.ajax({
            url: `/projects/item_instance/${itemInstanceId}/accessories`,
            type: 'GET',
            success: function(data) {
                if (data.accessories && data.accessories.length > 0) {
                    // Create a section for linked accessories
                    const accessoriesSection = $('<div class="linked-accessories-section mt-3"></div>');
                    
                    // Process each accessory
                    data.accessories.forEach(accessory => {
                        // Create accessory element
                        const accessoryDiv = $(`<div class="linked-accessory mb-3">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <span class="accessory-name">${accessory.name}</span>
                                    <span class="badge badge-secondary ml-2">${accessory.category_name || 'Unknown'}</span>
                                </div>
                                <button class="btn btn-sm btn-outline-info show-accessory-attributes-btn" 
                                        data-instance-id="${accessory.instance_id}"
                                        data-parent-item-id="${itemInstanceId}">
                                    <i class="fa fa-table"></i> Hide
                                </button>
                            </div>
                            <div class="accessory-attributes-container mt-2"></div>
                        </div>`);
                        
                        accessoriesSection.append(accessoryDiv);
                    });
                    
                    container.append(accessoriesSection);
                    
                    // Add click handler for showing/hiding accessory attributes
                    $('.show-accessory-attributes-btn').off('click').on('click', function() {
                        const btn = $(this);
                        const accessoryId = btn.data('instance-id');
                        const itemInstanceId = btn.data('parent-item-id');
                        const attributesContainer = btn.closest('.linked-accessory').find('.accessory-attributes-container');
                        
                        if (attributesContainer.is(':empty')) {
                            // Fetch and display attributes, passing the parent item ID
                            fetchInstanceAttributes(accessoryId, 'accessory', attributesContainer, itemInstanceId);
                            btn.html('<i class="fa fa-table"></i> Hide');
                        } else if (attributesContainer.is(':visible')) {
                            attributesContainer.slideUp();
                            btn.html('<i class="fa fa-table"></i> Attributes');
                        } else {
                            attributesContainer.slideDown();
                            btn.html('<i class="fa fa-table"></i> Hide');
                        }
                    });
                    
                    // Automatically load all accessory attributes
                    $('.show-accessory-attributes-btn').each(function() {
                        const btn = $(this);
                        const accessoryId = btn.data('instance-id');
                        const itemInstanceId = btn.data('parent-item-id');
                        const attributesContainer = btn.closest('.linked-accessory').find('.accessory-attributes-container');
                        
                        // Fetch and display attributes
                        fetchInstanceAttributes(accessoryId, 'accessory', attributesContainer, itemInstanceId);
                    });
                }
            },
            error: function() {
                console.error('Error loading linked accessories');
            }
        });
    }
    
    // Toggle attributes visibility
    function toggleAttributes(button) {
        const instanceElement = button.closest('.instance-item');
        const attributesContainer = instanceElement.next('.attributes-table-container');
        
        if (attributesContainer.is(':visible')) {
            attributesContainer.slideUp();
            button.html('<i class="fa fa-table"></i> Attributes');
        } else {
            attributesContainer.slideDown();
            button.html('<i class="fa fa-table"></i> Hide');
        }
        
        // Update the global toggle button based on visibility state
        updateGlobalToggleButton();
    }
    
    // Function to update the global toggle button text
    function updateGlobalToggleButton() {
        const allContainers = $('.attributes-table-container, .accessory-attributes-container');
        const visibleContainers = allContainers.filter(':visible');
        
        if (visibleContainers.length === 0) {
            $('#toggleAllAttributes').html('<i class="fas fa-table"></i> Mostrar Atributos');
        } else if (visibleContainers.length === allContainers.length) {
            $('#toggleAllAttributes').html('<i class="fas fa-table"></i> Esconder Atributos');
        } else {
            $('#toggleAllAttributes').html('<i class="fas fa-table"></i> Mostrar Atributos');
        }
    }
    
    // Toggle all attributes visibility
    function toggleAllAttributes() {
        const allContainers = $('.attributes-table-container, .accessory-attributes-container');
        const visibleContainers = allContainers.filter(':visible');
        const isAnyVisible = visibleContainers.length > 0;
        
        // Prevent multiple rapid toggles by using a flag
        if (window.isTogglingAll) return;
        window.isTogglingAll = true;
        
        if (isAnyVisible) {
            // Hide all
            allContainers.slideUp(400, function() {
                // Only update UI after animation completes, and only once
                if ($(this).is(allContainers.last())) {
                    $('#toggleAllAttributes').html('<i class="fas fa-table"></i> Mostrar Atributos');
                    $('.show-attributes-btn').html('<i class="fa fa-table"></i> Atributos');
                    $('.show-accessory-attributes-btn').html('<i class="fa fa-table"></i> Atributos');
                    window.isTogglingAll = false;
                }
            });
        } else {
            // Show all
            allContainers.slideDown(400, function() {
                // Only update UI after animation completes, and only once
                if ($(this).is(allContainers.last())) {
                    $('#toggleAllAttributes').html('<i class="fas fa-table"></i> Escondr Atributos');
                    $('.show-attributes-btn').html('<i class="fa fa-table"></i> Esconder');
                    $('.show-accessory-attributes-btn').html('<i class="fa fa-table"></i> Esconder');
                    window.isTogglingAll = false;
                }
            });
        }
    }
    
    // Event handlers
    $(document).on('click', '.show-attributes-btn', function(e) {
        e.stopPropagation();
        toggleAttributes($(this));
    });
    
    $(document).on('click', '#toggleAllAttributes', function() {
        toggleAllAttributes();
    });

    // Return public API
    return {
        loadInstances: loadInstances,
        fetchInstanceAttributes: fetchInstanceAttributes,
        fetchLinkedAccessories: fetchLinkedAccessories,
        toggleAttributes: toggleAttributes,
        toggleAllAttributes: toggleAllAttributes,
        updateGlobalToggleButton: updateGlobalToggleButton
    };
})();
