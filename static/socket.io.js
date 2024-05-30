var io = (function () {
    'use strict';

    var socket = {
        connect: function (url) {
            var socket = new WebSocket(url);

            socket.onopen = function () {
                socket.send('connect');
            };

            socket.onmessage = function (event) {
                var data = JSON.parse(event.data);
                if (data.type === 'message') {
                    if (socket.onmessagecallback) {
                        socket.onmessagecallback(data.data);
                    }
                }
            };

            socket.send = function (message) {
                socket.send(JSON.stringify({
                    type: 'message',
                    data: message
                }));
            };

            return socket;
        }
    };

    return {
        connect: socket.connect
    };
})();
var socket = io.connect('http://' + document.domain + ':' + location.port + '/');

socket.on('connect', function() {
    socket.emit('join', {room: 'all'});
});

socket.on('new_message', function(data) {
    var message = data.username + ': ' + data.message;
    
    $('#chatWindow').append('<div class="message">' + message + '</div>');
});