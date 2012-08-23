$(document).ready(function () {
    $("#login_item").hover(function(e){
    	if ($("#overlay").length > 0)
    		return;
    	
		$("body").append("<div id='overlay'><div class='li'></div></div>");
		$("#overlay .li").load('/ajax/login/');
		$("#overlay").fadeIn(150);
		
		// Close on the X icon; .live() monitors changes to the DOM
		$("#overlay .close").live('click', function(){
			$("#overlay").remove();
		});
		
		// Close on click elsewhere in the document (i.e. an element which is not a child of the overlay)
		$(document).click(function(event) { 
		    if($(event.target).parents().index($('#overlay')) == -1) {
		        if($('#overlay').length > 0) {
		            $('#overlay').remove()
		        }
		    }        
		})
    });
});
