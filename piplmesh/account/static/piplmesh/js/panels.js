function validatePanels(form) {
	var status = true;
	var selected_panels = {}
	$('[type=checkbox]', $(form)).each(function() {
		if ($(this).prop('checked')) {
			selected_panels[$(this).prop('name')] = panels[$(this).prop('name')];
		}
	});
	
	for (var panel in selected_panels) {
		if (selected_panels.hasOwnProperty(panel)) {
			var dependencies = checkDependencies(panel, selected_panels);
			
			if (dependencies.length > 0)
				status = false;
			selected_panels[panel] = dependencies;
		}
	}
	
	if (!status) {
		var error = gettext('Following dependencies not satisfied:');
		for (var panel in selected_panels) {
			if (selected_panels.hasOwnProperty(panel)) {
				var dependencies = selected_panels[panel];
				if (dependencies.length > 0) {
					error += "\n\t" + panel + ':';
					
					for (var panel in dependencies) {
						if (dependencies.hasOwnProperty(panel)) {
							error += "\n\t\t" + dependencies[panel];
						}
					}
				}
			}
		}
		
		alert(error);
	}
	
	return status;
}

function checkDependencies(panel, selected) {
	var dependencies = []
	
	for (var dependency in selected[panel]) {
		if (selected[panel].hasOwnProperty(dependency)) {
			dependency = selected[panel][dependency];
			if (!selected.hasOwnProperty(dependency) && dependencies.indexOf(dependency) == -1) {
				var inner_dependencies = checkDependencies(dependency, selected);
				dependencies.push(dependency);
				dependencies.concat(inner_dependencies);
			}
		}
	}
	
	return dependencies;
}