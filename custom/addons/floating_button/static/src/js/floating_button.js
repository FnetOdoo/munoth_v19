odoo.define('floating_button.save_button_hover', function (require) {
    "use strict";

    var FormController = require('web.FormController');

    FormController.include({
        renderButtons: function () {
            var self = this;
            this._super.apply(this, arguments);
            var $saveButton = this.$buttons.find('.o_form_button_save');
            var maxLeft = 1000; // Adjust the maximum left position as needed
            var intervalId;

            $saveButton.mouseenter(function () {
                // Initialize interval to move button to the left
                var allFieldsFilled = self._checkRequiredFields();
                console.log(allFieldsFilled, 'Filed?')
                if (allFieldsFilled) {
                    return false
                }
                intervalId = setInterval(function () {
                    var currentLeft = parseInt($saveButton.css('left')) || 0;
                    if (currentLeft >= maxLeft) {
                        // Reset button position when it reaches maximum left position
                        clearInterval(intervalId);
                        $saveButton.css({
                            'left': '0px'
                        });
                    } else {
                        // Move button to the left
                        $saveButton.css({
                            'position': 'relative',
                            'left': (currentLeft + 50) + 'px' // Adjust the movement speed as needed
                        });
                    }
                }, 10); // Adjust the interval time as needed
            });

            $saveButton.mouseleave(function () {
                // Stop the interval when mouse leaves the button
                clearInterval(intervalId);
            });

        },
       _checkRequiredFields: function () {
            // Check if all required fields are filled
            var allFieldsFilled = true;
            var $fields = this.$('.o_field_widget');
            $fields.each(function () {
                var $field = $(this);
                if ($field.is(':visible')) { // Only check visible fields
                    console.log(this, 'thisss')
                    if ($field.hasClass('o_input') || $field.hasClass('o_textarea') || $field.hasClass('o_field_many2one')) {
                        // Check for input, textarea, and many2one fields
                        if ($field.hasClass('o_required_modifier') && !$field.val()) {
                            allFieldsFilled = false;
                            return false; // Break the loop
                        }
                    } else if ($field.hasClass('o_field_many2many_tags')) {
                        // Check for many2many_tags fields
                        if ($field.find('.o_input').length === 0) {
                            allFieldsFilled = false;
                            return false; // Break the loop
                        }
                    } else if ($field.hasClass('o_field_selection')) {
                        // Check for selection fields
                        if (!$field.find('.o_selectivity_input').val()) {
                            allFieldsFilled = false;
                            return false; // Break the loop
                        }
                    }
                }
            });
            return allFieldsFilled;
        },
    });
});