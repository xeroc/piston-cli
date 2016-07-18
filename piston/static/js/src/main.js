$(function() {
 $.fn.bootstrapSwitch.defaults.onText = 'Yes';
 $.fn.bootstrapSwitch.defaults.offText = 'No';

 $("input[type=\"checkbox\"], input[type=\"radio\"]").not("[data-switch-no-init]").bootstrapSwitch();

});
