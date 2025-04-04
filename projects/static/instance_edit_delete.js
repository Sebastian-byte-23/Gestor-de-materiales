$(document).ready(function() {
    // Handle edit instance form submission
    $('#saveEditInstance').click(function() {
        const formData = {
            instance_id: $('#editInstanceId').val(),
            instance_type: $('#editItemType').val(),
            name: $('#editInstanceName').val(),
            short_name: $('#editInstanceShortName').val(),
            description: $('#editInstanceDescription').val(),
            short_description: $('#editInstanceShortDescription').val(),
            installation: $('#editInstanceInstallation').val(),
            attributes: {}  // We'll populate this from dynamic fields
        };

        // Collect attribute values
        $('#editAttributesContainer .attribute-field').each(function() {
            const name = $(this).data('attribute-name');
            const value = $(this).val();
            formData.attributes[name] = value;
        });

        $.ajax({
            url: '/projects/instances/update_instance',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function(response) {
                if (response.success) {
                    $('#editInstanceModal').modal('hide');
                    window.location.reload();
                } else {
                    alert('Error updating instance: ' + (response.error || ''));
                }
            }
        });
    });
});

// Handle edit instance click (to be called from other files)


function handleEditInstance(instanceId, instanceType, projectId) {
    // Reset the form
    $('#instanceForm')[0].reset();
    $('#attributesContainer').empty();
    $('#existingInstanceAlert').addClass('d-none');
    $('.instance-detail').show();
    $('.instance-detail input, .instance-detail textarea').prop('disabled', false);
    $('#modalTitle').text('Edit Instance');
    $('#saveInstance').text('Save Changes');
    
    // Set hidden fields
    $('#instanceId').val(instanceId);
    $('#itemType').val(instanceType);
    $('#projectId').val(projectId);
    
    // Set a flag to indicate we're editing an existing instance
    $('#instanceForm').data('edit-mode', true);
    
    // Fetch instance details
    $.ajax({
        url: `/projects/instance/${instanceId}/details`,
        type: 'GET',
        data: { instance_type: instanceType },
        success: function(data) {
            // Populate form with instance data
            $('#instanceName').val(data.name);
            $('#instanceShortName').val(data.short_name);
            $('#instanceDescription').val(data.description);
            $('#instanceShortDescription').val(data.short_description);
            $('#instanceInstallation').val(data.installation);
            $('#itemId').val(instanceType === 'item' ? data.item_id : data.accessory_id);
            
            // Set edit mode flag and ensure it's properly set in the form
            $('#instanceForm').data('edit-mode', true);
            $('#editMode').val('true');
            
            // Fetch and populate attributes
            $.ajax({
                url: `/projects/instance/${instanceId}/attributes`,
                type: 'GET',
                data: { instance_type: instanceType },
                success: function(attrData) {
                    // Group attributes by application or group_id
                    const attributesByGroup = {};
                    
                    attrData.attributes.forEach(attr => {
                        const groupKey = attr.group_id || attr.application || 'General';
                        
                        if (!attributesByGroup[groupKey]) {
                            attributesByGroup[groupKey] = {
                                application: attr.application,
                                application_name: attr.application_name,
                                group_id: attr.group_id,
                                attributes: {}
                            };
                        }
                        
                        attributesByGroup[groupKey].attributes[attr.name] = attr.value;
                    });
                    
                    // Create attribute fields for each group
                    const container = $('#attributesContainer').empty();
                    
                    // Add application field for accessories
                    if (instanceType === 'accessory') {
                        $('#applicationContainer').removeClass('d-none');
                    } else {
                        $('#applicationContainer').addClass('d-none');
                    }
                    
                    // Add attribute fields for each group
                    Object.entries(attributesByGroup).forEach(([groupKey, group]) => {
                        // Create a fieldset for each group
                        const fieldset = $('<fieldset class="attribute-group border p-3 mb-3">').appendTo(container);
                        
                        // Add a legend with the application name if available
                        if (group.application_name && group.application_name !== 'General') {
                            $('<legend class="w-auto px-2">').text(group.application_name).appendTo(fieldset);
                        }
                        
                        // Add attributes to this group
                        Object.entries(group.attributes).forEach(([name, value]) => {
                            const div = $('<div class="form-group">').appendTo(fieldset);
                            $('<label>').text(name + ':').appendTo(div);
                            
                            // Create input field - use a simpler name format for item attributes
                            const inputName = instanceType === 'item' ? 
                                `attribute_${name}` : 
                                `attribute_${groupKey}_${name}`;
                                
                            $('<input type="text" class="form-control">').attr({
                                name: inputName,
                                value: value,
                                'data-group-key': groupKey,
                                'data-name': name
                            }).appendTo(div);
                        });
                        
                        // Add hidden field for group_id if available
                        if (group.group_id) {
                            $('<input type="hidden">').attr({
                                name: `group_id_${groupKey}`,
                                value: group.group_id
                            }).appendTo(fieldset);
                        }
                    });
                    
                    // Show the modal
                    $('#instanceCreationModal').modal('show');
                },
                error: function() {
                    alert('Error loading instance attributes');
                }
            });
        },
        error: function() {
            alert('Error loading instance details');
        }
    });
}

// Handle delete instance confirmation
$(document).on('click', '#confirmDeleteInstance', function() {
    const instanceId = $('#deleteInstanceId').val();
    const instanceType = $('#deleteInstanceType').val();
    const projectId = $('#deleteProjectId').val();
    
    // Send delete request
    $.ajax({
        url: '/projects/instances/delete_instance',
        type: 'DELETE',
        contentType: 'application/json',
        data: JSON.stringify({
            instance_id: instanceId,
            instance_type: instanceType,
            project_id: projectId
        }),
        success: function(response) {
            if (response.success) {
                // Close the modal
                $('#deleteInstanceModal').modal('hide');
                
                // Reload instances for all categories
                $('.category-item').each(function() {
                    const categoryId = $(this).data('category-id');
                    window.tableLogic.loadInstances(categoryId, projectId);
                });
            } else {
                alert('Error deleting instance: ' + (response.error || 'Unknown error'));
            }
        },
        error: function(xhr, status, error) {
            alert('Error deleting instance: ' + error);
        }
    });
});

// Handle delete attribute row confirmation with better validation
$(document).on('click', '#confirmDeleteAttributeRow', function() {
    // Validate required fields
    const instanceId = $('#deleteRowInstanceId').val();
    const instanceType = $('#deleteRowInstanceType').val();
    const groupId = $('#deleteRowGroupId').val();
    const application = $('#deleteRowApplication').val();
        
    if (!instanceId || !instanceType) {
        alert('Missing required instance information');
        return;
    }
    
    // Send delete request
    $.ajax({
        url: '/projects/instances/delete_attribute_row',
        type: 'DELETE',
        contentType: 'application/json',
        data: JSON.stringify({
            instance_id: instanceId,
            instance_type: instanceType,
            group_id: groupId,
            application: application
        }),
        success: function(response) {
            if (response.success) {
                // Show success feedback
                const successMsg = response.deleted_count > 0 
                    ? `Deleted ${response.deleted_count} attributes successfully`
                    : 'No attributes found to delete';
                    
                // Close modal after brief delay
                setTimeout(() => {
                    $('#deleteAttributeRowModal').modal('hide');
                    alert(successMsg);
                }, 500);
                
                // Find and remove the specific row
                const rowSelector = groupId ? 
                    `[data-group-id="${groupId}"]` : 
                    `[data-application="${application}"]`;
                
                $(`.delete-attribute-row${rowSelector}`).closest('tr').fadeOut(300, function() {
                    $(this).remove();
                    
                    // If no rows left, show "No attributes found" message
                    const table = $(this).closest('table');
                    if (table.find('tbody tr').length === 0) {
                        table.replaceWith('<p class="text-muted">No attributes found</p>');
                    }
                });
            } else {
                alert('Error deleting attribute row: ' + (response.error || 'Unknown error'));
            }
        },
        error: function(xhr, status, error) {
            let errorMsg = 'Error deleting attribute row: ';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMsg += xhr.responseJSON.error;
            } else {
                errorMsg += error;
            }
            alert(errorMsg);
            
            // Cerrar el modal solo si fue un error de validación
            if (xhr.status !== 404) {
                $('#deleteAttributeRowModal').modal('hide');
            }
        }
    });
});
