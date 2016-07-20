var $notify = $('#notify');
var socket = io('http://localhost:5054');

$(function() {
 $('[data-toggle="tooltip"]').tooltip();
 socket.emit("getWebUser");
});

function notify(status) {
 $notify.notify({
  message:{
   text:status.message
  },
  type: status.status,
  fadeOut: { enabled: true, delay: 5000 }
 }).show()
}

function accountChange() {
 var account = $(this).attr("id");
 $('#activeAccount').text(account);
 socket.emit("changeAccount", account);
}

function setAccount(data) {
 var account = data["name"]
 $('#activeAccount').text(account);
}


function downVote() {
 console.log("downvoting");
 var identifer = $(this).attr("identifier");
 socket.emit("vote", identifer, -100);
}

function upVote() {
 console.log("upvoting");
 var identifer = $(this).attr("identifier");
 socket.emit("vote", identifer, 100);
}

function log (data){
 console.log(data);
 notify(data);
}


// events
socket.on('connect', function(){});
socket.on('event', function(data){});
socket.on('disconnect', function(){});
socket.on('log', log);
socket.on('web.user', setAccount);
$('.accountSelector').on("click", accountChange);
$('.downvoteButton').on("click", downVote);
$('.upvoteButton').on("click", upVote);
