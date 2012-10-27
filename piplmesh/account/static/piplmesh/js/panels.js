$(document).ready(function () {
    var panels_requiredby = {}
    
    $('#content .panels form input[type="checkbox"][data-display="True"]').on('change', function (event) {
        var display = $(this);
        validateCheckbox(display);
        $('#id_' + display.data('panel')).val(display.prop('checked'));
    }).andSelf().find(':checked').change();
    
    function validateCheckbox(checkbox) {
        var panel = checkbox.data('panel');
        var checked = checkbox.prop('checked');
        
        $.each(panels_with_dependencies[panel] || [], function (index, dependency) {
            if (!(dependency in panels_requiredby)) {
                panels_requiredby[dependency] = {};
            }
            
            if (checked) {
                panels_requiredby[dependency][panel] = true;
            }
            else if (!checked && panel in panels_requiredby[dependency]) {
                delete panels_requiredby[dependency][panel];
            }
            
            lockCheckbox(dependency);
        });
    }

    function lockCheckbox(panel) {
        var panel_checkbox = $('#content .panels form input[data-panel="' + panel + '"]');
        var panel_locktext = $('.locked', panel_checkbox.parents('li'));
        var changed = false;
        
        if (!$.isEmptyObject(panels_requiredby[panel])) {
            panel_locktext.text(gettext("Panel is required by:"));
            var list = $('<ul/>');
            $.each(panels_requiredby[panel], function (panel, depends) {
                $('<li/>').text(panel).appendTo(list);
            })
            list.appendTo(panel_locktext);
            
            panel_checkbox.data('previous_state', panel_checkbox.prop('checked'));
            panel_checkbox.prop('checked', true).prop('disabled', true);
            changed = true;
        }
        else {
            if (panel_checkbox.prop('disabled')) {
                panel_checkbox.prop('disabled', false).prop('checked', panel_checkbox.data('previous_state'));
                panel_locktext.text('');
                changed = true;
            }
        }
        
        // Only if it changed, otherwise there's a chance of an infinite loop with mutually dependent panels.
        if (changed) {
            // Trigger event to recursively check dependencies throughout hierarchy.
            panel_checkbox.change();
        }
    }
});
