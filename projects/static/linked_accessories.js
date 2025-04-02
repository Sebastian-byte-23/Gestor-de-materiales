// This file contains functions for handling linked accessories

// Function to show the linked accessory modal
function showLinkedAccessoryModal(categoryId, categoryName, itemInstanceId) {
    // Update modal title and store instance ID
    $('#linkedCategoryName').text(categoryName);
    $('#linkedItemInstanceId').val(itemInstanceId);
    $('#linkedCategoryId').val(categoryId);
    
    // Fetch accessories for this category
    $.get(`/projects/category/${categoryId}/items`, function(data) {
        const accessoriesList = $('#linkedAccessoriesList').empty();
        
        // Sort accessories by name
        const accessories = data.accessories.sort((a, b) => a.name.localeCompare(b.name));
        
        // Populate the list
        accessories.forEach(accessory => {
            const listItem = $(`<li class="list-group-item d-flex justify-content-between align-items-center">
                ${accessory.name}
                <span class="badge badge-secondary">Accessory</span>
            </li>`);
            
            listItem.on('click', function() {
                // When clicked, get accessory details and show creation modal
                $.get(`/projects/get_item_details/accessory/${accessory.name}`, function(data) {
                    // Close the linked accessory modal
                    $('#linkedAccessoryModal').modal('hide');
                    
                    // Reset the form
                    $('#instanceForm')[0].reset();
                    $('#attributesContainer').empty();
                    $('#existingInstanceAlert').addClass('d-none');
                    $('.instance-detail').show();
                    $('.instance-detail input, .instance-detail textarea').prop('disabled', false);
                    $('#modalTitle').text('Create Instance');
                    $('#saveInstance').text('Create Instance');
                    
                    // Set hidden fields
                    $('#itemId').val(data.id);
                    $('#itemType').val('accessory');
                    // Ensure we get the current project ID from the URL if not already set
                    const projectId = $('#deleteProjectId').val() || $('#projectId').val() || window.location.pathname.split('/')[2];
                    $('#projectId').val(projectId);
                    $('#instanceId').val('');
                    
                    // Store the application (item instance ID) in the form
                    if (!$('#instanceApplication').length) {
                        $('<input>').attr({
                            type: 'hidden',
                            id: 'instanceApplication',
                            value: $('#linkedItemInstanceId').val()
                        }).appendTo('#instanceForm');
                    } else {
                        $('#instanceApplication').val($('#linkedItemInstanceId').val());
                    }
                    
                    // Always populate form with fresh accessory data
                    $('#instanceName').val(data.name);
                    $('#instanceShortName').val(data.short_name);
                    $('#instanceDescription').val(data.description);
                    $('#instanceShortDescription').val(data.short_description);
                    $('#instanceInstallation').val(data.installation);
                    
                    // Populate attribute fields
                    populateLinkedAccessoryAttributes(data.attributes);
                    
                    // Show the instance creation modal
                    $('#instanceCreationModal').modal('show');
                });
            });
            
            accessoriesList.append(listItem);
        });
        
        // Show the modal
        $('#linkedAccessoryModal').modal('show');
    });
}

// Function to populate attribute fields for linked accessories
function populateLinkedAccessoryAttributes(attributes) {
    const container = $('#attributesContainer').empty();
    
    // Generate a group ID for this set of attributes
    const groupId = 'new_group_' + Date.now().toString();
    
    // Add hidden group ID field
    $('<input type="hidden">').attr({
        id: 'attributeGroupId',
        name: 'group_id',
        value: groupId
    }).appendTo(container);
    
    attributes.forEach(attr => {
        const div = $('<div class="form-group">').appendTo(container);
        $('<label>').text(attr.name + ':').appendTo(div);
        
        // Parse the values array
        const values = JSON.parse(attr.value);
        
        // If values array is empty or has only one empty value, use text input
        if (values.length === 0 || (values.length === 1 && values[0] === '')) {
            $('<input type="text" class="form-control">').attr({
                name: `attribute_${attr.name}`,
                required: true,
                'data-group-id': groupId
            }).appendTo(div);
        } else {
            // Otherwise use select dropdown
            const select = $('<select class="form-control">').attr({
                name: `attribute_${attr.name}`,
                required: true,
                'data-group-id': groupId
            }).appendTo(div);
            
            // Add options from the values array
            values.forEach(val => {
                $('<option>').val(val).text(val).appendTo(select);
            });
        }
    });
}

// Function to update linked categories indicators
function updateLinkedCategoryIndicators() {
    // For each category with linked categories, show the indicator
    Object.keys(window.linkedCategoriesData || {}).forEach(categoryId => {
        if (window.linkedCategoriesData[categoryId] && window.linkedCategoriesData[categoryId].length > 0) {
            $(`.category-item[data-category-id="${categoryId}"] .linked-indicator`).show();
        }
    });
}
