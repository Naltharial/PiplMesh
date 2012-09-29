var panels_forcedby = {}
var panels_savestate = {}

$(document).ready(function () {
	var inputs = $('#panel_form input[type="checkbox"]');
	inputs.on('change', function () {
    	validateCheckbox(this);
    });
    
	inputs.each(function (index, element) {
    	var checkbox = $(element);
    	
    	if (checkbox.prop('checked')) {
    		checkbox.change();
    	}
    });
	
	$('#panel_form').on('submit', function () {
		$('#panel_form input[type="checkbox"][disabled]').each(function (index, element) {
			$(element).prop('disabled', false);
        });
    });
});


function validateCheckbox(checkbox) {
    var checkbox = $(checkbox);
    var panel = checkbox.attr('name');
    var checked = checkbox.prop('checked');
    
    if (typeof panels_with_dependencies[panel] != "undefined" && panels_with_dependencies[panel].length) {
	    $.each(panels_with_dependencies[panel], function (key, dependency) {
	    	if (typeof panels_forcedby[dependency] == "undefined") {
	    		panels_forcedby[dependency] = [];
	    	}
	    	
	    	var index = panels_forcedby[dependency].indexOf(panel);
	    	if (checked && index < 0) {
	    		panels_forcedby[dependency].push(panel);
	    	} else if (!checked && index >= 0) {
	    		panels_forcedby[dependency].splice(index, 1);
	    	}
	    	
	    	lockCheckbox(dependency);
	    });
    }
}


function lockCheckbox(panel) {
	var panel_checkbox = $('#panel_form input[name="'+panel+'"]');
	var panel_locktext = $('.locked', panel_checkbox.parents('li'));
	
	if (typeof panels_forcedby[panel] != "undefined" && panels_forcedby[panel].length) {
		var text = gettext('Panel depended on by:');
		panel_locktext.text(text);
		$('<ul><li>' + panels_forcedby[panel].join("\n\t") + '</li></ul>').appendTo(panel_locktext);
		
		panels_savestate[panel] = panel_checkbox.prop('checked');
		panel_checkbox.prop('checked', true);
		panel_checkbox.prop('disabled', true);
		
		// Trigger event to recursively check dependencies throughout hierarchy.
		panel_checkbox.change()
	} else {
		if (panel_checkbox.prop('disabled')) {
			panel_checkbox.prop('disabled', false);
			panel_checkbox.prop('checked', panels_savestate[panel]);
			panel_locktext.text('');
		}
	}
}
