odoo.define('purchase_comparison_chart.purchase_comparison', function (require) {
'use strict';
	var Model = require('web.Model');
    var core = require('web.core');
    var QWeb = core.qweb;
	console.log("Loaded")
	$(document).on('click', $('#b3'), function() {
//	    $("b3").onclick(function() {
        console.log('Test')
        var values = $(this).val();
        var res = values.split(",");
        var value=res[2];
        var value1=res[1];
        return new Model("purchase.requisition").call('show_terms_condition',[parseInt(value), value1, parseInt(value)])
           .then(function(action){
           if (action){
                document.getElementById('my_vals').innerHTML = action;
                var modal = document.getElementById('myModal');
                modal.style.display = "block";
           }
           else{
            document.getElementById('my_vals').innerHTML = 'Notes Unavailable';
            var modal = document.getElementById('myModal');
            modal.style.display = "block";
           }
           });
//	    });
	    var span = document.getElementsByClassName("close")[0];
	    var modal = document.getElementById('myModal');
		span.onclick = function() {
   			modal.style.display = "none";
		}
		window.onclick = function(event) {
		    if (event.target == modal) {
		        modal.style.display = "none";
		    }
		}
	});
});