$(document).ready(function () {
    var panels_forcedby = {}
    var panels_savestate = {}
    
    $('#content .panels form').on('submit', function (event) {
        $('input[type="checkbox"][disabled]', this).prop('disabled', false);
    })
    	.find('input[type="checkbox"]').on('change', function (event) {
        validateCheckbox(this);
    })
    	.andSelf().find(':checked').change();
    
    function validateCheckbox(checkbox) {
        var checkbox = $(checkbox);
        var panel = checkbox.attr('name');
        var checked = checkbox.prop('checked');
        
        if (panel in panels_with_dependencies && panels_with_dependencies[panel].length) {
            $.each(panels_with_dependencies[panel], function (index, dependency) {
                if (!(dependency in panels_forcedby)) {
                    panels_forcedby[dependency] = {};
                }
                
                if (checked) {
                    panels_forcedby[dependency][panel] = true;
                }
                else if (!checked && panel in panels_forcedby[dependency]) {
                    delete panels_forcedby[dependency][panel];
                }
                
                lockCheckbox(dependency);
            });
        }
    }

    function lockCheckbox(panel) {
        var panel_checkbox = $('#content .panels form input[name="' + panel + '"]');
        var panel_locktext = $('.locked', panel_checkbox.parents('li'));
        
        if (!$.isEmptyObject(panels_forcedby[panel])) {
            panel_locktext.text(gettext('Panel depended on by:'));
            var list = $('<ul></ul>');
            $.each(panels_forcedby[panel], function (panel, depends) {
            	$('<li></li>').text(panel).appendTo(list);
            })
            list.appendTo(panel_locktext);
            
            panels_savestate[panel] = panel_checkbox.prop('checked');
            panel_checkbox.prop('checked', true).prop('disabled', true);
        }
        else {
            if (panel_checkbox.prop('disabled')) {
                panel_checkbox.prop('disabled', false).prop('checked', panels_savestate[panel]);
                panel_locktext.text('');
            }
        }
        
        // Trigger event to recursively check dependencies throughout hierarchy.
        panel_checkbox.change()
    }
});
