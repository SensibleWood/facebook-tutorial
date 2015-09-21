var map;
var markers = [];

/* Initialize the Google Maps display, zoomed out above the UK */
function initMap() {
    map = new google.maps.Map(document.getElementById('map-display'), {
        center: {lat: 54.445103, lng: -3.318324},
        zoom: 6
    });

    /* Only add listeners when authorized (as button does not exist) */
    if ($('#login').length == 0) {
        /* Add left click listener that removes context menu */
        google.maps.event.addListener(map, "click", function(event) {
            $(".contextmenu").remove();
        });

        /* Custom context menu to offer POST of Hello World message */
        google.maps.event.addListener(map, "rightclick", function(event) {
            showContextMenu(event);
        });
    }
}

function showContextMenu(event) {
    var projection;
    var contextMenuDiv;

    projection = map.getProjection() ;
    $('.contextmenu').remove();

    contextMenuDiv = document.createElement("div");
    contextMenuDiv.className  = 'contextmenu';
    contextMenuDiv.innerHTML =
      '<h5>Pick and share menu</h5>' +
      '<a id="menu1" href="javascript:void(0)" onclick="postHelloWorld(' + event.latLng.H + ',' + event.latLng.L + ')">Pick random coffee place<\/a><br/><br/>';

    $(map.getDiv()).append(contextMenuDiv);
    setMenuXY(event);
    contextMenuDiv.style.visibility = "visible";
}


function setMenuXY(event) {
    $('.contextmenu').css('left', event.pixel.x);
    $('.contextmenu').css('top', event.pixel.y);
}

function postHelloWorld(lat, lng) {
    $.ajax({
        'type': 'POST',
        'url': '/helloworld?lat=' + lat + '&lng=' + lng,
        'success': function(data) {
            /* bootbox.alert("Message posted successfully!"); */
            $('.contextmenu').remove();

            if (data.lat !== undefined) {
                var infowindow = new google.maps.InfoWindow({
                    content: '<div id="content"><p>' + data.name + '</p></div>'
                });

                marker = new google.maps.Marker({
                    map: map,
                    draggable: false,
                    animation: google.maps.Animation.DROP,
                    position: {lat: data.lat, lng: data.lng},
                });

                marker.addListener('click', function() {
                    infowindow.open(map, marker);
                });

                infowindow.open(map, marker);
                markers.push(marker);
            } else {
                bootbox.alert("Coffee picker failed to find place!");
            }
        },
        'error': function() {
            bootbox.alert("Failed to post hello world message!");
            $('.contextmenu').remove();
        }
    });
}