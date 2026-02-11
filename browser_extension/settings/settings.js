(async() => {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});

    var response = await chrome.runtime.sendMessage({msgType: "getTextTarget", tabid: tab.id});  
    if (!!response.target) {
        document.getElementById("getTextTargetButton").style["background-color"] = "green";
    }

    response = await chrome.runtime.sendMessage({msgType: "getSendTarget", tabid: tab.id});  
    if (!!response.target) {
        document.getElementById("getSendTargetButton").style["background-color"] = "green";
    }
})();

const getSendTarget = document.getElementById("getSendTargetButton");
if (getSendTarget) {
    getSendTarget.onclick = function() {
        (async () => {
            const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
            const response = await chrome.tabs.sendMessage(tab.id, {msgType: "grabSendTarget"});
            
            document.getElementById("getSendTarget").style["background-color"] = "green";
          })();

    };
}

const getTextTarget = document.getElementById("getTextTargetButton");
if (getTextTarget) {
    getTextTarget.onclick = function() {
        (async () => {
            const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
            const response = await chrome.tabs.sendMessage(tab.id, {msgType: "grabTextTarget"});
            
            document.getElementById("getTextTarget").style["background-color"] = "green";
          })();
    };
}

const sendText = document.getElementById("sendTextButton");
if (sendText) {    
    sendText.onclick = function() {
        const selected = document.querySelector('input[name="sendInputMode"]:checked');
        const sendInputMode = selected ? selected.value : null;
        chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
            chrome.tabs.sendMessage(
                tabs[0].id,
                {
                    msgType: "sendText",
                    inputStrategy: sendInputMode,
                    text: "Hello, world!",
                },
                function(response) {
                    window.close();
                }
            );
        });
    };
}

const tabHeader = document.getElementById("tabHeader");
chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
    tabHeader.innerText = "TAB " + tabs[0].id.toString();
});