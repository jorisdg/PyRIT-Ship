var textTarget;
var sendTarget;
var selectedFunction;

function mouseenter(event) {
  var trgt = $(event.currentTarget);
  
  $("#pyritshipselectordiv").remove();

  var newDiv = $(`<div id="pyritshipselectordiv" style="position: absolute; 
        top: ${trgt.offset().top}px; left: ${trgt.offset().left}px; width: ${trgt.width()}px; height: ${trgt.height()}px;
        z-index: 1000; background-color: #00FF0044;">
      
    </div>`);
  newDiv.prependTo("body");

  newDiv.on("mouseleave", mouseleave);
  newDiv.data("target", event.currentTarget);
  newDiv.on("click", targetSelect);
}

function mouseleave(event) {
  console.log("remove due to leave")
  $(event.currentTarget).remove();
}

function targetSelect(event) {
  var trgt = $(event.currentTarget).data("target");

  if (!$(trgt).attr('id')) {
    const uniqueId = 'ext-' + Date.now() + '-' + Math.floor(Math.random()*1e6);
    $(trgt).attr('id', uniqueId);
  }

  selectedFunction(trgt);

  $(event.currentTarget).remove();
}

function setTargetBorder(target) {
  $(target).css("border", "2px solid red");
}

function grabTextTarget(sendResponse) {
  selectedFunction = function(target) {
    $('input[type="text"], input[type="search"], textarea, div[contenteditable="true"], span[contenteditable="true"]').off('mouseenter', mouseenter);
    textTarget = target;
    setTargetBorder(target);
    sendResponse({ found: true, id: $(target).attr('id') });
    console.log("capturing text target END");

    chrome.runtime.sendMessage({msgType: "setTextTarget", target: $(target).attr('id')});
  }

  console.log("capturing text target BEGIN");

  $('input[type="text"], input[type="search"], textarea, div[contenteditable="true"], span[contenteditable="true"]').on('mouseenter', mouseenter);
}

function grabSendTarget(sendResponse) {
  selectedFunction = function(target) {
    $('input[type="button"], input[type="submit"], button').off('mouseenter', mouseenter);
    sendTarget = target;
    setTargetBorder(target);
    sendResponse({ found: true, id: $(target).attr('id') });
    console.log("capturing send target END");

    chrome.runtime.sendMessage({msgType: "setSendTarget", target: $(target).attr('id')});
  }

  console.log("capturing send target BEGIN");

  $('input[type="button"], input[type="submit"], button').on('mouseenter', mouseenter);
}

window.addEventListener('load', setKnownTargets, false);

async function setKnownTargets() {
  const sendTargetId = await chrome.runtime.sendMessage({msgType: "getSendTarget"});
  if (!!sendTargetId.target) {
    sendTarget = $("#" + sendTargetId.target);
    setTargetBorder(sendTarget);
  }

  const textTargetId = await chrome.runtime.sendMessage({msgType: "getTextTarget"});
  if (!!textTargetId.target) {
    textTarget = $("#" + textTargetId.target);
    setTargetBorder(textTarget);
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  switch (request.msgType) {
    case "grabTextTarget":
      // TODO remove previous target if one is selected
      $("#pyritshipselectordiv").remove();
      grabTextTarget(sendResponse);
      //return true;
      break;
      
    case "grabSendTarget":
      // TODO remove previous target if one is selected
      $("#pyritshipselectordiv").remove();
      grabSendTarget(sendResponse);
      //return true;
      break;
      
    case "sendText":
      // if (!sendTarget) {
      //   (async () => {
      //     const sendTargetId = await chrome.runtime.sendMessage({msgType: "getSendTarget"});
      //     console.log("sendTargetID: " + sendTargetId);
      //     sendTarget = $("#" + sendTargetId.target);
      //   })();
      // }
      // if (!textTarget) {
      //   (async () => {
      //     const textTargetId = await chrome.runtime.sendMessage({msgType: "getTextTarget"});
      //     textTarget = $("#" + textTargetId.target);
      //     console.log("textTargetID: " + textTargetId);
      //   })();
      // }
      if (!!textTarget) {
        console.log("setting text");
        //$(textTarget).text(request.text).change();
        $(textTarget).focus();
        $(textTarget).val(request.text).change();
        // $(textTarget).val(request.text).trigger('input');
        // $(textTarget).trigger({type: 'keypress', which: 13, keycode: 13});
        $(textTarget).trigger($.Event("keypress", {key: " "}))
        //$(textTarget).trigger($.Event('keypress', { which: 13, keyCode: 13 }));
        // for (let i = 0; i < request.text.length; i++) {
        //   $(textTarget).trigger({type: 'keypress', which: request.text[i]});
        // }
      }
      if (!!sendTarget) {
        console.log("clicking send");
        $(sendTarget).click();
        //sendResponse({ sent: true });
      }
      break;
  }

});


// https://stackoverflow.com/questions/4780822/how-can-i-detect-when-a-new-element-has-been-added-to-the-document-in-jquery
// var myElement = $("<div>hello world</div>")[0];

// var observer = new MutationObserver(function(mutations) {
//    if (document.contains(myElement)) {
//         console.log("It's in the DOM!");
//         observer.disconnect();
//     }
// });

// observer.observe(document, {attributes: false, childList: true, characterData: false, subtree:true});
