(async() => {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});

    var response = await chrome.runtime.sendMessage({msgType: "getTextTarget", tabid: tab.id});  
    if (!!response.target) {
        document.getElementById("getTextTarget").style["background-color"] = "green";
    }

    response = await chrome.runtime.sendMessage({msgType: "getSendTarget", tabid: tab.id});  
    if (!!response.target) {
        document.getElementById("getSendTarget").style["background-color"] = "green";
    }
})();

const getSendTarget = document.getElementById("getSendTarget");
if (getSendTarget) {
    getSendTarget.onclick = function() {
        (async () => {
            const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
            const response = await chrome.tabs.sendMessage(tab.id, {msgType: "grabSendTarget"});
            
            document.getElementById("getSendTarget").style["background-color"] = "green";
          })();

    };
}

const getTextTarget = document.getElementById("getTextTarget");
if (getTextTarget) {
    getTextTarget.onclick = function() {
        (async () => {
            const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
            const response = await chrome.tabs.sendMessage(tab.id, {msgType: "grabTextTarget"});
            
            document.getElementById("getTextTarget").style["background-color"] = "green";
          })();
    };
}

const sendText = document.getElementById("sendText");
if (sendText) {
    sendText.onclick = function() {
        chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
            chrome.tabs.sendMessage(
                tabs[0].id,
                {
                    msgType: "sendText",
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