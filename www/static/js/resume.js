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

  /* Custom JS */
  $("#registerBtn").on("click",function(){
    var formData = $(this).parent().serializeArray();
    console.log($("#deviceName").val().match("/\s/"));
    if ($("#deviceName").val().match(/\s/) != null) {
      // Whitespace Found
      alert("Your Device Name Contains white spaces. Please Remove")
    } else {
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
    }
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

  $("#sendFPBtn").on("click",function(){
    var formData = $(this).parent().serializeArray();
    $.post("/send_fp", formData, function(res){
      if (res != '200') {
        alert("Flight Plan Failed to send");
      } else {
        alert("Flight Plan was Send to Drone");
      }
    });
  });

  $("#updateNetwork").on("click",function(){
    $.post("/update_network", function(res){
      if (res != '200') {
        alert("Global Ping Failed to send");
      } else {
        //alert("Global Ping was Send to Drone");
        window.location.reload(true);
      }
    });
  });

  // Leaflet Stuff

  // viewCoor = [lat, lng]
  // bases = [{base: %s, lat: %d, lng: %d}]
  function createMap(id, viewCoor, bases) {
    var mymap = L.map(id).setView(viewCoor, 13);

    L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoiY3RhbmdlbDE0IiwiYSI6ImNqZnR5aHB4MzNuOGUyeG1rYWZtOHB4YXoifQ.zI08FZUwF9cczjG1P4wCMQ', {
      attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="http://mapbox.com">Mapbox</a>',
      maxZoom: 18,
      id: 'mapbox.streets',
      accessToken: 'pk.eyJ1IjoiY3RhbmdlbDE0IiwiYSI6ImNqZnR5aHB4MzNuOGUyeG1rYWZtOHB4YXoifQ.zI08FZUwF9cczjG1P4wCMQ'
    }).addTo(mymap);
    for (var i = 0; i < bases.length; i++) {
      var marker = L.marker([bases[i]['lat'], bases[i]['lng']]);//.addTo(mymap);
      marker.bindTooltip(bases[i]['base'], {permanent:true}).openTooltip().addTo(mymap);
    }
  }

  // Example Dummy Data
  var viewCoor = [40.34573916136237, -74.65477966767571];
  createMap('mapid', viewCoor, bases);
  createMap('mapid2', viewCoor, bases);

})(jQuery); // End of use strict
