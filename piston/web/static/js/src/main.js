var $notify = $('#notify');
var socket = io('http://localhost:5054');
var stopSpinners = [];

$(function() {
 /* Tooltips
  ************************************************/
 $('[data-toggle="tooltip"]').tooltip();

 /* Tokenfield
  ************************************************/
 $('#tokenfield').tokenfield({
  "delimiter": [",", " ", "\t"],
  "createTokensOnBlur": true,
 });

 /* Retreive web:user
  ************************************************/
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
 setAccount({"name": account});
 socket.emit("changeAccount", account);
}

function setAccount(data) {
 var account = data["name"]
 $('#activeAccount').text(account);
 $('#activeAccount').attr("href", "/@" + account);
}

function voteSpinnerStart(icon) {
 if (icon.hasClass("fa-thumbs-up")) {
  icon.removeClass("fa-thumbs-up");
  icon.addClass("fa-thumbs-up-spinner");
 }
 if (icon.hasClass("fa-thumbs-down")) {
  icon.removeClass("fa-thumbs-down");
  icon.addClass("fa-thumbs-down-spinner");
 }
 icon.addClass("fa-spinner fa-pulse fa-fw");
 stopSpinners.push(icon);
}

function voteSpinnerStop(icon) {
 if (icon.hasClass("fa-thumbs-up-spinner")) {
  icon.removeClass("fa-thumbs-up-spinner");
  icon.addClass("fa-thumbs-up");
 }
 if (icon.hasClass("fa-thumbs-down-spinner")) {
  icon.removeClass("fa-thumbs-down-spinner");
  icon.addClass("fa-thumbs-down");
 }
 icon.removeClass("fa-spinner fa-pulse fa-fw");
 stopSpinners.pop(icon);
}

function stopAllSpinners() {
 for (var i=0; i<stopSpinners.length; ++i) {
   voteSpinnerStop(stopSpinners[i]);
 }
}

function upVote() {
 var identifer = $(this).attr("identifier");
 socket.emit("vote", identifer, 100);
 voteSpinnerStart($(this).children("i"));
}

function downVote() {
 var identifer = $(this).attr("identifier");
 socket.emit("vote", identifer, -100);
 voteSpinnerStart($(this).children("i"));
}

function voted(data) {
 var identifier = data["identifier"];
 var weight = data["weight"];
 var upvote = $("button[identifier='" + identifier + "'][class*='upvoteButton']");
 var downvote = $("button[identifier='" + identifier + "'][class*='downvoteButton']");
 if (weight > 0) {
  upvote.addClass("btn-success");
  upvote.prop('disabled', true);
  voteSpinnerStop(upvote.children("i"));
 } else {
  downvote.addClass("btn-danger");
  downvote.prop('disabled', true);
  voteSpinnerStop(downvote.children("i"));
 }
}

function log (data){
 console.log(data);
 notify(data);
}

function locked(){
 stopAllSpinners();
}

function unlockWallet() {
 var password = $("#unlockpassword");
 socket.emit("unlock", password.val());
}

function unlocked() {
 $('#unlockModal').modal('hide');
 $(".walletLock").removeClass("fa-lock");
 $(".walletLock").addClass("fa-unlock");
}

function notunlocked() {
 $(".walletLock").removeClass("fa-unlock")
 $(".walletLock").addClass("fa-lock")
}

/* SocketIO events
 ******************************************/
socket.on('connect', function(){});
socket.on('event', function(data){});
socket.on('disconnect', function(){});
socket.on('log', log);

/* SocketIO messaging
 ******************************************/
socket.on('success.web:user', setAccount);
socket.on('success.unlocked', unlocked);
socket.on('success.vote', voted);
socket.on('error.notunlocked', notunlocked);
socket.on('error.locked', locked);

/* jQuery interactions
 ******************************************/
$('.accountSelector').on("click", accountChange);
$('.downvoteButton').on("click", downVote);
$('.upvoteButton').on("click", upVote);
$('#unlockWallet').on("click", unlockWallet);
