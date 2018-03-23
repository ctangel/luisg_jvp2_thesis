(function($) {
  "use strict"; // Start of use strict

  // Smooth scrolling using jQuery easing
  $('a.js-scroll-trigger[href*="#"]:not([href="#"])').click(function() {
    if (location.pathname.replace(/^\//, '') == this.pathname.replace(/^\//, '') && location.hostname == this.hostname) {
      var target = $(this.hash);
      target = target.length ? target : $('[name=' + this.hash.slice(1) + ']');
      if (target.length) {
        $('html, body').animate({
          scrollTop: (target.offset().top)
        }, 1000, "easeInOutExpo");
        return false;
      }
    }
  });

  // Closes responsive menu when a scroll trigger link is clicked
  $('.js-scroll-trigger').click(function() {
    $('.navbar-collapse').collapse('hide');
  });

  // Activate scrollspy to add active class to navbar items on scroll
  $('body').scrollspy({
    target: '#sideNav'
  });

  $("#registerBtn").on("click",function(){
    var formData = $(this).parent().serializeArray();
    $.post("/register", formData, function(res){
      if (res != '200') {
        if (res == '400') {
          alert("Failed: Device has already been registered")
        } else {
          alert("Registration Failed");
        }
      } else {
        alert("Device has been Registered");
        window.location.reload(true);
      }
    });
  });

  $("#resetBtn").on("click",function(){
    $.post("/master_reset", function(res){
      if (res != '200') {
        alert("Reset Failed");
      } else {
        alert("Systems has been Reset");
      }
    });
  });

})(jQuery); // End of use strict
