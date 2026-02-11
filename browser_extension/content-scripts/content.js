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
      console.log("setting text");
      console.log(request.inputStrategy);
      console.log(request.text);
      if (!!textTarget) {
        switch(request.inputStrategy) {
          case "typing-setRangeText":
            inputSetRange(request.text);
            break;
          case "typing-events":
            inputEvents(request.text);
            break;
          case "paste":
            pasteIntoInput(request.text);
            break;
        }

        //$(textTarget).text(request.text).change();
        // $(textTarget).focus();
        // $(textTarget).val(request.text).change();
        // $(textTarget).val(request.text).trigger('input');
        // $(textTarget).trigger({type: 'keypress', which: 13, keycode: 13});
        //$(textTarget).trigger($.Event("keypress", {key: " "}))
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


function setFormControlValue(target, value, opts = {}) {
  const { simulateTyping = false, blur = true } = opts;

  if (!target) return false;

  // If it’s inside shadow DOM, we still dispatch composed events below.
  target.focus?.();

  const tag = (target.tagName || '').toUpperCase();
  const isInput = tag === 'INPUT';
  const isTextarea = tag === 'TEXTAREA';
  const isSelect = tag === 'SELECT';
  const isCE = !isInput && !isTextarea && !isSelect && target.isContentEditable;

  try {
    if (isSelect) {
      setSelectValue(target, String(value));
    } else if (isCE) {
      setContentEditable(target, String(value));
    } else if (simulateTyping && (isInput || isTextarea)) {
      // type-like path for masks/formatters
      typeLike(target, String(value));
    } else if (isInput || isTextarea) {
      setInputValue(target, String(value));
    } else {
      // Fallback: attempt textContent + input
      target.textContent = String(value);
      target.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
      target.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
    }

    if (blur) target.blur?.();
    return true;
  } catch (e) {
    console.warn('setFormControlValue failed', e);
    return false;
  }
}


function inputSetRange(text) {
  const el = $(textTarget)[0];
  el.focus();

  const isTextControl = el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement;
  if (isTextControl) {
    const len = el.value.length;
    if (typeof el.setSelectionRange === 'function') {
      el.setSelectionRange(0, len);
    }
    if (typeof el.setRangeText === 'function') {
      // Preferred path
      el.setRangeText(text, 0, len, "end");
    } else {
      // Fallback for very old browsers / exotic inputs
      el.value = text;
    }
    el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
    el.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
    return;
  }

  if (el.isContentEditable) {
    // Replace all content for contenteditable
    // (Could implement selection if needed)
    const selection = window.getSelection();
    if (selection) {
      selection.removeAllRanges();
      const range = document.createRange();
      range.selectNodeContents(el);
      selection.addRange(range);
    }
    // Use textContent to avoid unintended HTML insertion
    el.textContent = text;
    el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
    return;
  }

  // Generic fallback (non-input, non-contenteditable)
  el.textContent = text;
  el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
}

function inputEvents(text) {
  const el = $(textTarget)[0];
  el.focus();
  const canceled = !el.dispatchEvent(new InputEvent('beforeinput', {
    inputType: 'insertText',
    data: text,
    bubbles: true,
    composed: true,
    cancelable: true
  }));
  if (!canceled) {
    // fall through to native setter + input
    setInputValue(el, el.value + text);
  }
}

function setInputValue(el, value) {
  console.log("setInputValue");
  // Only use the prototype descriptor for real input/textarea elements
  if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
    const proto = Object.getPrototypeOf(el); // HTMLInputElement.prototype or HTMLTextAreaElement.prototype
    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
    if (desc && typeof desc.set === 'function') {
      desc.set.call(el, value);
    } else {
      el.value = value;
    }
    el.dispatchEvent(new Event('input',  { bubbles: true, composed: true }));
    el.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
    return;
  }

  // Contenteditable fallback
  if (el.isContentEditable) {
    el.textContent = value;
    el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
    return;
  }

  // Generic fallback (other element types)
  el.textContent = value;
  el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
}

function pasteIntoInput(text) {
  const el = $(textTarget)[0];
  el.focus();
  const ev = new InputEvent("beforeinput", {
    inputType: "insertFromPaste",
    data: text,
    bubbles: true,
    composed: true,
    cancelable: true
  });

  const canceled = !el.dispatchEvent(ev);

  if (!canceled) {
    el.textContent = text;
    el.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
  }
}


// https://stackoverflow.com/questions/4780822/how-can-i-detect-when-a-new-element-has-been-added-to-the-document-in-jquery
// var myElement = $("<div>hello world</div>")[0];

// var observer = new MutationObserver(function(mutations) {
//    if (document.contains(myElement)) {
//         console.log("It's in the DOM!");
//         observer.disconnect();
//     }
// });

// observer.observe(document, {attributes: false, childList: true, characterData: false, subtree:true});
