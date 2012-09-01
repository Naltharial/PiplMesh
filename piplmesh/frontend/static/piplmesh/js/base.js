$(document).ready(function () {
    $("#login_item").hover(function(e){
    	$("#overlay .login").show();
		$("#overlay").fadeIn(150);
		
		// Close on the X icon; .live() monitors changes to the DOM
		$("#overlay .close").live('click', function(){
			$("#overlay").remove();
		});
		
		// Close on click elsewhere in the document (i.e. an element which is not a child of the overlay)
		$(document).click(function(event) { 
		    if($(event.target).parents().index($('#overlay')) == -1) {
	            $('#overlay').fadeOut(150);
	            $("#overlay .login").hide();
		    }        
		})
    });
});
