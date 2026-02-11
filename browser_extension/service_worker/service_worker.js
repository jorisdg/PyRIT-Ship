var tabTargets = [];

chrome.runtime.onMessage.addListener((request, sender, reply) => {
    // console.log(
    //   sender.tab
    //     ? "from a content script:" + sender.tab.url
    //     : "from the extension"
    // );
    // if (request.greeting == "hello") reply({ farewell: "goodbye" });
  
    var tabid = sender.tab ? sender.tab.id : request.tabid;

    switch(request.msgType) {
        case "setTextTarget":
            var targets;
            console.log("setTextTarget");
            if (!!tabTargets[tabid]) {
                targets = tabTargets[tabid];
                targets.textTarget = request.target;
            }
            else {
                targets = { textTarget: request.target, sendTarget: null };
            }
            tabTargets[tabid] = targets;
            break;
        case "getTextTarget":
            var targets;
            if (!!tabTargets[tabid]) {
                targets = tabTargets[tabid];
                reply({target: targets.textTarget});
            }
            else {
                reply({target: null});
            }
            break;
        case "setSendTarget":
            var targets;
            console.log("setSendTarget");
            if (!!tabTargets[tabid]) {
                targets = tabTargets[tabid];
                targets.sendTarget = request.target;
            }
            else {
                targets = { textTarget: null, sendTarget: request.target };
            }
            tabTargets[tabid] = targets;
            break;
        case "getSendTarget":
            var targets;
            if (!!tabTargets[tabid]) {
                targets = tabTargets[tabid];
                reply({target: targets.sendTarget});
            }
            else {
                reply({target: null});
            }
            break;
    }

    return true;
  });